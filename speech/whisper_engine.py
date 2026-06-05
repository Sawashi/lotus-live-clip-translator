"""Speech recognition engine using faster-whisper.

Handles loading Whisper models and transcribing audio chunks
with support for CPU and CUDA (auto-detected).
"""

import os
import sys
import logging
import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    MODEL_DIR = os.path.join(os.path.dirname(sys.executable), "_internal", "models")
else:
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

# Map model size names to actual HuggingFace cache-style directory names
WHISPER_MODEL_DIR_MAP = {
    "tiny": "models--Systran--faster-whisper-tiny",
    "small": "models--Systran--faster-whisper-small",
    "medium": "models--Systran--faster-whisper-medium",
}

# Hallucination detection thresholds
NO_SPEECH_THRESHOLD = 0.8  # Only filter if model is very confident it's silence
COMPRESSION_RATIO_THRESHOLD = 2.0  # High compression ratio = repetitive hallucination
# Common Whisper hallucinations on silence by language
HALLUCINATED_PHRASES = {
    "ご視聴ありがとうございました",
    "ありがとうございました",
    "ご視聴ありがとうございます",
}


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

            # Use mapped directory name if known, fall back to model_size directly
            model_dir_name = WHISPER_MODEL_DIR_MAP.get(self._model_size, self._model_size)
            model_path = os.path.join(MODEL_DIR, model_dir_name)
            if not os.path.exists(model_path):
                logger.info("Model not found locally at %s, will download", model_path)
                model_path = self._model_size
            else:
                # HF cache layout: models--repo--name/snapshots/<hash>/
                # faster-whisper needs the snapshot subdir with model.bin directly inside
                snapshots_dir = os.path.join(model_path, "snapshots")
                if os.path.isdir(snapshots_dir):
                    snapshots = os.listdir(snapshots_dir)
                    if snapshots:
                        model_path = os.path.join(snapshots_dir, snapshots[0])
                        logger.info("Using HF cache snapshot path: %s", model_path)

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
        """Detect best available device (CUDA > DirectML > CPU)."""
        logger.info("Detecting compute device...")
        gpu_compute = "int8"

        # 1) CUDA (NVIDIA GPUs)
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("GPU detected: NVIDIA CUDA (compute=%s)", gpu_compute)
                return "cuda", gpu_compute
        except ImportError:
            pass
        # 2) DirectML
        try:
            import torch_directml
            dml = torch_directml.device()
            if dml is not None:
                logger.info("GPU detected: DirectML (compute=%s)", gpu_compute)
                return "dml", gpu_compute
        except ImportError:
            pass
        # 3) ctranslate2 DML
        try:
            from ctranslate2 import get_supported_device
            devices = get_supported_device()
            if "dml" in devices:
                logger.info("GPU detected: DirectML (ctranslate2 native, compute=%s)", gpu_compute)
                return "dml", gpu_compute
        except ImportError:
            pass
        logger.info("No GPU detected, falling back to CPU")
        return "cpu", "int8"

    def _is_hallucination(self, seg) -> bool:
        """Check if a segment is likely a hallucination on silence."""
        text = seg.text.strip()
        if not text:
            return True

        # 1) Known hallucination phrases
        if text in HALLUCINATED_PHRASES:
            logger.debug("Hallucination: known phrase '%s'", text[:40])
            return True

        # 2) High no_speech_prob (only if also very short — real speech with noise
        #    can have mid-range no_speech_prob)
        no_speech = getattr(seg, "no_speech_prob", 0.0)
        if no_speech > NO_SPEECH_THRESHOLD and len(text) < 30:
            logger.debug("Hallucination: no_speech=%.2f text='%s'", no_speech, text[:40])
            return True

        # 3) High compression ratio = repetitive/looping text (hallucination pattern)
        comp_ratio = getattr(seg, "compression_ratio", 0.0)
        if comp_ratio > COMPRESSION_RATIO_THRESHOLD:
            logger.debug("Hallucination: compression_ratio=%.2f text='%s'", comp_ratio, text[:40])
            return True

        return False

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
            # VAD disabled for real-time loopback capture — it's too aggressive
            # and discards most audio from WASAPI loopback
            segments, info = self._model.transcribe(
                audio_data,
                language=language if language != "auto" else None,
                beam_size=5,
                vad_filter=False,
            )

            results = []
            filtered = 0
            for seg in segments:
                if self._is_hallucination(seg):
                    filtered += 1
                    continue

                text = seg.text.strip()
                results.append({
                    "text": text,
                    "start": seg.start,
                    "end": seg.end
                })

            logger.debug(
                "Transcribed %.2f sec audio: %d results (%d filtered), language=%s prob=%.2f",
                len(audio_data) / 16000,
                len(results),
                filtered,
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