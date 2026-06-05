"""Offline translation engine using alirezamsh/small100 (M2M-100 based).

Provides fully offline translation after model download.
Model is cached locally in models/small100/ via huggingface_hub.
No API key or internet required after first download.

Usage (from README):
    model = M2M100ForConditionalGeneration.from_pretrained("alirezamsh/small100")
    tokenizer = SMALL100Tokenizer.from_pretrained("alirezamsh/small100")
    tokenizer.tgt_lang = "en"       # target language for decoding
    encoded = tokenizer(text, return_tensors="pt")
    gen = model.generate(**encoded)  # NO forced_bos_token_id
    result = tokenizer.batch_decode(gen, skip_special_tokens=True)
"""

import os
import sys
import logging
from pathlib import Path

import torch
from transformers import M2M100ForConditionalGeneration

logger = logging.getLogger(__name__)

MODEL_REPO = "alirezamsh/small100"
if getattr(sys, 'frozen', False):
    DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(sys.executable), "_internal", "models", "small100")
else:
    DEFAULT_MODEL_DIR = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models", "small100"
    )


class Small100Engine:
    """Offline translation engine using Small100 (M2M-100)."""

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR):
        self._model_dir = model_dir
        self._tokenizer = None
        self._model = None
        self._device = "cpu"
        self._ready = False
        self._maybe_download()
        self._load_model()

    def _maybe_download(self):
        """Download model from HF hub if not already on disk."""
        if os.path.isdir(self._model_dir) and any(
            f.endswith(".bin") or f.endswith(".safetensors") or f.endswith(".onnx")
            for f in os.listdir(self._model_dir)
        ):
            logger.info("Small100 model already cached at %s", self._model_dir)
            return

        logger.info("Downloading Small100 model to %s ...", self._model_dir)
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=MODEL_REPO,
                local_dir=self._model_dir,
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            logger.info("Small100 model downloaded to %s", self._model_dir)
        except Exception as e:
            logger.error("Failed to download Small100 model: %s", e)
            raise

    def _load_model(self):
        """Load SMALL100Tokenizer and model from disk.

        SMALL100Tokenizer is a custom tokenizer (tokenization_small100.py)
        that differs from M2M100Tokenizer. We need to load it from the
        model directory because the tokenizer_config.json doesn't declare
        the class name for auto-discovery.
        """
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Loading Small100 tokenizer from %s ...", self._model_dir)
            # Put model dir on path so SMALL100Tokenizer class is importable
            if self._model_dir not in sys.path:
                sys.path.insert(0, self._model_dir)
            # Import the custom tokenizer
            from tokenization_small100 import SMALL100Tokenizer as SmallTokenizer
            self._tokenizer = SmallTokenizer.from_pretrained(self._model_dir)

            logger.info("Loading Small100 model on %s ...", self._device)
            self._model = M2M100ForConditionalGeneration.from_pretrained(
                self._model_dir
            ).to(self._device)
            self._ready = True
            logger.info("Small100 engine ready on %s", self._device)
        except Exception as e:
            logger.error("Failed to load Small100 model: %s", e)
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Translate text using Small100.

        Args:
            text: Text to translate
            from_code: Source language code (e.g. 'en', 'ja', 'vi')
            to_code: Target language code

        Returns:
            Translated text, or empty string on failure
        """
        if not text or not text.strip():
            return ""
        if not self._ready:
            logger.warning("Small100 engine not ready")
            return ""

        try:
            # IMPORTANT: SMALL100Tokenizer uses tokenizer.tgt_lang to set the
            # target language prefix in the encoder input. DO NOT use
            # forced_bos_token_id during generation - the model handles the
            # target language via the tokenizer's prefix mechanism.
            self._tokenizer.tgt_lang = to_code

            encoded = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
            ).to(self._device)

            generated = self._model.generate(
                **encoded,
                max_length=512,
                num_beams=5,
            )

            results = self._tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
            )
            result = results[0] if results else ""
            logger.debug("Small100: '%s' (%s) → '%s' (%s)", text[:50], from_code, result[:50], to_code)
            return result

        except Exception as e:
            logger.error("Small100 translate error: %s", e)
            return ""