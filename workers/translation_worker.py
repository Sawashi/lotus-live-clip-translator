"""Translation worker thread.

Processes transcribed text and translates it using either
Argos Translate (offline) or Small100 (offline) engine.
"""

import queue
import time
import logging
import threading
from translation.argos_engine import ArgosEngine

logger = logging.getLogger(__name__)

ENGINE_ARGOS = "argos"
ENGINE_SMALL100 = "small100"


class TranslationWorker(threading.Thread):
    """Worker thread for translation."""

    def __init__(
        self,
        text_queue: queue.Queue,
        subtitle_queue: queue.Queue,
        engine_type: str = ENGINE_ARGOS,
    ):
        super().__init__(daemon=True)
        self._text_queue = text_queue
        self._subtitle_queue = subtitle_queue
        self._engine_type = engine_type
        self._argos = ArgosEngine()
        self._small100 = None  # lazy init
        self._current_engine = None  # active engine instance
        self._running = False
        self._enabled = True
        self._source_language = "auto"
        self._target_language = "en"
        self._target_mode = "direct"
        self._status = "not_ready"
        self._status_detail = ""
        self._engines_checked = False
        self._last_original = ""
        self._last_translated = ""

    def run(self):
        """Run the translation loop."""
        self._running = True
        logger.info("Translation worker started (engine=%s)", self._engine_type)

        # Check engines in background thread
        threading.Thread(target=self._check_all_engines, daemon=True).start()

        while self._running:
            try:
                msg = self._text_queue.get(timeout=0.5)

                if msg.get("type") == "reset":
                    logger.debug("Translation worker: received reset signal, clearing state")
                    self._last_original = ""
                    self._last_translated = ""
                    self._subtitle_queue.put({"type": "reset"})
                    continue

                if not self._enabled:
                    self._subtitle_queue.put({
                        "original": msg["text"],
                        "translated": "",
                        "timestamp": msg["timestamp"]
                    })
                    continue

                text = msg["text"]
                translated = self._translate(text)
                if translated:
                    logger.debug("Translated: '%s' → '%s'", text[:30], translated[:30])

                self._last_original = text
                self._last_translated = translated

                self._subtitle_queue.put({
                    "original": text,
                    "translated": translated,
                    "timestamp": msg["timestamp"]
                })

            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Translation worker error: %s", e)

    def stop(self):
        """Stop the translation worker."""
        self._running = False

    def set_enabled(self, enabled: bool):
        """Enable or disable translation."""
        self._enabled = enabled

    def set_mode(self, mode: str):
        """Set translation mode (only offline supported)."""
        self._mode = mode
        self._update_status()

    def set_engine(self, engine_type: str):
        """Change translation engine type."""
        self._engine_type = engine_type
        self._current_engine = None  # force re-init
        self._update_status()

    def set_languages(self, source: str, target: str, mode: str = "direct"):
        """Set source and target languages with translation mode."""
        self._source_language = source
        self._target_language = target
        self._target_mode = mode

    @property
    def status(self) -> str:
        return self._status

    @property
    def status_detail(self) -> str:
        """Get detailed status string for UI display."""
        if self._status == "not_ready":
            if not self._engines_checked:
                return "Not ready (checking engines...)"
            return f"Not ready ({self._status_detail})"
        return f"{self._status.capitalize()} ({self._engine_type})"

    @property
    def engine_type(self) -> str:
        return self._engine_type

    def _get_engine(self):
        """Get or initialize the active engine."""
        if self._current_engine is not None:
            return self._current_engine

        if self._engine_type == ENGINE_SMALL100:
            if self._small100 is None:
                from translation.small100_engine import Small100Engine
                self._small100 = Small100Engine()
            self._current_engine = self._small100
        else:
            self._current_engine = self._argos

        return self._current_engine

    def _check_all_engines(self):
        """Check translation engine and update status."""
        self._engines_checked = False

        engine = self._get_engine()
        self._status_detail = f"checking {self._engine_type}..."
        logger.info("Checking %s ...", self._engine_type)

        if engine.is_ready:
            logger.info("%s: ready", self._engine_type)
        else:
            logger.info("%s: not ready", self._engine_type)

        self._engines_checked = True
        self._update_status()
        logger.info("Engine check complete. Status: %s", self._status)

    def _translate(self, text: str) -> str:
        """Translate text using the active engine.

        If it fails, returns the original text as fallback.
        """
        if self._source_language == "auto":
            logger.debug("Source=auto, passing through: '%s'", text[:50])
            return text

        try:
            engine = self._get_engine()
            if self._engine_type == ENGINE_ARGOS and self._target_mode == "hop2":
                result = self._argos.translate_via_english(
                    text, self._source_language, self._target_language
                )
            else:
                result = engine.translate(
                    text, self._source_language, self._target_language
                )
            if result:
                self._status = "offline"
                return result
            logger.warning("%s returned no result, falling back to original", self._engine_type)

            self._update_status()
            return text

        except Exception as e:
            logger.error("Translation error: %s, falling back to original", e)
            self._update_status()
            return text

    def _update_status(self):
        """Update the status indicator."""
        engine = self._get_engine()
        if engine.is_ready:
            self._status = "offline"
        else:
            self._status = "not_ready"
            self._status_detail = f"{self._engine_type} not loaded"

    def install_argos_package(self, from_code: str, to_code: str) -> bool:
        """Install an Argos translation package."""
        return self._argos.install_package(from_code, to_code)
