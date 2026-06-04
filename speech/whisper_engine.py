"""Speech recognition engine using faster-whisper.

Handles loading Whisper models and transcribing audio chunks
with support for CPU and CUDA (auto-detected).
"""

import os
import logging
import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


class WhisperEngine:
    """Whisper-based speech recognition engine."""

    def __init__(self, model_size: str = "small"):
        self._model_size = model_size
        self._model = None
        self._device = "auto"
        self._compute_type = "auto"
        self._loaded = False
        self._load_error = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_size(self) -> str:
        return self._model_size

    @property
    def device(self) -> str:
        return self._device

    @property
    def load_error(self) -> str:
        return self._load_error

    def load_model(self, model_size: str = None):
        """Load the Whisper model.

        Args:
            model_size: Model size (tiny, small, medium). Uses current if None.
        """
        if model_size:
            self._model_size = model_size

        try:
            # Determine device and compute type
            self._device, self._compute_type = self._detect_device()
            logger.info(
                "Loading Whisper model '%s' on %s (compute=%s)",
                self._model_size, self._device, self._compute_type
            )

            model_path = os.path.join(MODEL_DIR, self._model_size)
            if not os.path.exists(model_path):
                logger.info("Model not found locally at %s, will download", model_path)
                model_path = self._model_size

            self._model = WhisperModel(
                model_path,
                device=self._device,
                compute_type=self._compute_type,
                download_root=MODEL_DIR
            )
            self._loaded = True
            self._load_error = None
            logger.info("Whisper model '%s' loaded successfully", self._model_size)

        except Exception as e:
            self._loaded = False
            self._load_error = str(e)
            logger.error("Failed to load Whisper model: %s", e)

    def _detect_device(self) -> tuple:
        """Detect best available device (CUDA > CPU)."""
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
        return "cpu", "int8"

    def transcribe(self, audio_data: np.ndarray, language: str = None) -> list:
        """Transcribe audio data.

        Args:
            audio_data: Float32 numpy array of audio samples (16kHz)
            language: Language code (e.g. 'en', 'ja') or None for auto

        Returns:
            List of segment dicts with 'text', 'start', 'end' keys
        """
        if not self._loaded or self._model is None:
            logger.warning("Model not loaded, cannot transcribe")
            return []

        try:
            segments, info = self._model.transcribe(
                audio_data,
                language=language if language != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                    threshold=0.5
                )
            )

            results = []
            for seg in segments:
                results.append({
                    "text": seg.text.strip(),
                    "start": seg.start,
                    "end": seg.end
                })

            logger.debug(
                "Transcribed %.2f sec audio: %d segments, language=%s prob=%.2f",
                len(audio_data) / 16000,
                len(results),
                info.language,
                info.language_probability
            )
            return results

        except Exception as e:
            logger.error("Transcription error: %s", e)
            return []

    def unload(self):
        """Unload the model to free memory."""
        self._model = None
        self._loaded = False
        logger.info("Whisper model unloaded")