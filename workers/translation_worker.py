"""Translation worker thread.

Processes transcribed text and translates it using Argos Translate (offline).
"""

import queue
import time
import logging
import threading
from translation.argos_engine import ArgosEngine

logger = logging.getLogger(__name__)

TRANSLATION_MODE_OFFLINE = "offline"


class TranslationWorker(threading.Thread):
    """Worker thread for translation."""

    def __init__(
        self,
        text_queue: queue.Queue,
        subtitle_queue: queue.Queue
    ):
        super().__init__(daemon=True)
        self._text_queue = text_queue
        self._subtitle_queue = subtitle_queue
        self._argos = ArgosEngine()
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
        logger.info("Translation worker started")

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
        return self._status.capitalize()

    def _check_all_engines(self):
        """Check translation engine and update status."""
        self._engines_checked = False

        self._status_detail = "checking argos..."
        logger.info("Checking Argos Translate...")
        if self._argos.is_ready:
            logger.info("Argos Translate: ready")
        else:
            logger.info("Argos Translate: not ready (no packages installed)")

        self._engines_checked = True
        self._update_status()
        logger.info("Engine check complete. Status: %s", self._status)

    def _translate(self, text: str) -> str:
        """Translate text using Argos Translate.

        If it fails, returns the original text as fallback.
        """
        if self._source_language == "auto":
            logger.debug("Source=auto, passing through: '%s'", text[:50])
            return text

        try:
            if self._target_mode == "hop2":
                result = self._argos.translate_via_english(
                    text, self._source_language, self._target_language
                )
            else:
                result = self._argos.translate(
                    text, self._source_language, self._target_language
                )
            if result:
                self._status = "offline"
                return result
            logger.warning("Argos returned no result, falling back to original")

            self._update_status()
            return text

        except Exception as e:
            logger.error("Translation error: %s, falling back to original", e)
            self._update_status()
            return text

    def _update_status(self):
        """Update the status indicator."""
        if self._argos.is_ready:
            self._status = "offline"
        else:
            self._status = "not_ready"
            self._status_detail = "Argos packages not installed"

    def install_argos_package(self, from_code: str, to_code: str) -> bool:
        """Install an Argos translation package."""
        return self._argos.install_package(from_code, to_code)