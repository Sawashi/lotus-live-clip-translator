"""Speech recognition worker thread.

Processes audio chunks from the audio queue using faster-whisper.
Feeds transcribed text into a queue for the translation worker.
Detects silence/gaps to reset state cleanly between clips.
"""

import queue
import sys
import time
import logging
import threading
import numpy as np
from speech.whisper_engine import WhisperEngine

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.005  # RMS energy below this = silence
SILENCE_RESET_SECONDS = 1.0  # Continuous silence triggers state reset

# main.py redirects stdout to suppress argostranslate spam; grab real stdout for user-facing output
_original_stdout = sys.__stdout__


class RecognitionWorker(threading.Thread):
    """Worker thread for speech recognition."""

    def __init__(
        self,
        audio_queue: queue.Queue,
        text_queue: queue.Queue,
        model_size: str = "small",
        chunk_duration: float = 2.0
    ):
        super().__init__(daemon=True)
        self._audio_queue = audio_queue
        self._text_queue = text_queue
        self._engine = WhisperEngine(model_size)
        self._running = False
        self._language = "auto"
        self._buffer = np.array([], dtype=np.float32)
        self._model_loaded = threading.Event()
        self._chunk_duration = chunk_duration
        # Silence detection for graceful reset between clips
        self._silence_start = None  # time.time() when silence began
        self._reset_sent = False  # prevent sending multiple resets

    def run(self):
        """Run the recognition loop."""
        self._running = True
        logger.info("Recognition worker started")

        # Load model on startup
        self._engine.load_model()
        if self._engine.is_loaded:
            self._model_loaded.set()
        else:
            logger.error("Model failed to load, recognition disabled")

        self._process_loop()

    def stop(self):
        """Stop the recognition worker."""
        self._running = False

    def set_language(self, language: str):
        """Set the recognition language."""
        self._language = language
        logger.info("Recognition language set to: %s", language)

    def set_model(self, model_size: str):
        """Change the Whisper model (requires reload)."""
        logger.info("Loading model: %s", model_size)
        self._engine.load_model(model_size)
        if self._engine.is_loaded:
            self._model_loaded.set()

    @property
    def is_model_loaded(self) -> bool:
        return self._engine.is_loaded

    @property
    def model_size(self) -> str:
        return self._engine.model_size

    @property
    def device(self) -> str:
        return self._engine.device

    def set_buffer_duration(self, seconds: float):
        """Set chunk duration for audio processing."""
        self._chunk_duration = max(0.5, min(10.0, seconds))

    def _is_silent(self, audio_chunk: np.ndarray) -> bool:
        """Check if audio chunk is silence (low RMS energy)."""
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        return rms < SILENCE_THRESHOLD

    def _handle_silence(self, audio_chunk: np.ndarray):
        """Track silence duration and reset state if silence persists."""
        if self._is_silent(audio_chunk):
            if self._silence_start is None:
                self._silence_start = time.time()
            elif not self._reset_sent and (time.time() - self._silence_start) >= SILENCE_RESET_SECONDS:
                logger.debug("Silence detected for %.1f sec → resetting state", SILENCE_RESET_SECONDS)
                # Clear internal state
                self._buffer = np.array([], dtype=np.float32)
                # Signal downstream workers to reset
                self._text_queue.put({"type": "reset"})
                self._reset_sent = True
        else:
            self._silence_start = None
            self._reset_sent = False

    def _process_loop(self):
        """Process audio chunks from the queue."""
        chunk_samples = int(self._chunk_duration * SAMPLE_RATE)

        while self._running:
            try:
                # Collect audio data until we have enough
                while len(self._buffer) < chunk_samples:
                    try:
                        data = self._audio_queue.get(timeout=0.1)
                        self._buffer = np.concatenate([self._buffer, data])
                        # Log when we first start receiving audio
                        if len(self._buffer) == len(data):
                            logger.info("Audio data received, buffer growing (%.1f sec chunks)", self._chunk_duration)
                    except queue.Empty:
                        if not self._running:
                            return
                        continue

                # Process the chunk
                audio_chunk = self._buffer[:chunk_samples]
                self._buffer = self._buffer[chunk_samples:]

                if not self._engine.is_loaded:
                    time.sleep(0.1)
                    continue

                # Silence detection: check before transcribing
                self._handle_silence(audio_chunk)

                segments = self._engine.transcribe(audio_chunk, self._language)

                for seg in segments:
                    if seg["text"]:
                        text = seg["text"].strip()
                        try:
                            _original_stdout.write(f"[RECOGNIZED] {text}\n")
                            _original_stdout.flush()
                        except UnicodeEncodeError:
                            pass  # Windows console can't print some chars
                        self._text_queue.put({
                            "type": "transcription",
                            "text": text,
                            "language": self._language,
                            "timestamp": time.time()
                        })

            except Exception as e:
                logger.error("Recognition worker error: %s", e)
                time.sleep(0.5)
