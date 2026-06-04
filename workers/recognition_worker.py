"""Speech recognition worker thread.

Processes audio chunks from the audio queue using faster-whisper.
Feeds transcribed text into a queue for the translation worker.
"""

import queue
import time
import logging
import threading
import numpy as np
from speech.whisper_engine import WhisperEngine

logger = logging.getLogger(__name__)

CHUNK_DURATION = 2.0  # Seconds of audio to process at a time
SAMPLE_RATE = 16000


class RecognitionWorker(threading.Thread):
    """Worker thread for speech recognition."""

    def __init__(
        self,
        audio_queue: queue.Queue,
        text_queue: queue.Queue,
        model_size: str = "small"
    ):
        super().__init__(daemon=True)
        self._audio_queue = audio_queue
        self._text_queue = text_queue
        self._engine = WhisperEngine(model_size)
        self._running = False
        self._language = "auto"
        self._buffer = np.array([], dtype=np.float32)
        self._model_loaded = threading.Event()

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

    def _process_loop(self):
        """Process audio chunks from the queue."""
        chunk_samples = int(CHUNK_DURATION * SAMPLE_RATE)

        while self._running:
            try:
                # Collect audio data until we have enough
                while len(self._buffer) < chunk_samples:
                    try:
                        data = self._audio_queue.get(timeout=0.1)
                        self._buffer = np.concatenate([self._buffer, data])
                        # Log when we first start receiving audio
                        if len(self._buffer) == len(data):
                            logger.info("Audio data received, buffer growing (%.1f sec chunks)", CHUNK_DURATION)
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

                segments = self._engine.transcribe(audio_chunk, self._language)

                for seg in segments:
                    if seg["text"]:
                        try:
                            print(f"[RECOGNIZED] {seg['text']}")
                        except UnicodeEncodeError:
                            pass  # Windows console can't print some chars
                        self._text_queue.put({
                            "type": "transcription",
                            "text": seg["text"],
                            "language": self._language,
                            "timestamp": time.time()
                        })

            except Exception as e:
                logger.error("Recognition worker error: %s", e)
                time.sleep(0.5)