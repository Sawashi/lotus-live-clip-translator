"""Translation worker thread.

Processes transcribed text and translates it.
Supports offline (Argos), online (LibreTranslate), and local (LTEngine) modes.
Only uses the engine matching the user's selected mode.
"""

import queue
import time
import logging
import threading
from translation.argos_engine import ArgosEngine
from translation.libretranslate_engine import LibreTranslateEngine
from translation.ltengine_engine import LTEngine

logger = logging.getLogger(__name__)

TRANSLATION_MODE_OFFLINE = "offline"
TRANSLATION_MODE_ONLINE = "online"
TRANSLATION_MODE_LTENGINE = "ltengine"


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
        self._libre = LibreTranslateEngine()
        self._ltengine = LTEngine()
        self._running = False
        self._enabled = True
        self._mode = TRANSLATION_MODE_OFFLINE
        self._source_language = "auto"
        self._target_language = "en"
        self._status = "not_ready"
        self._status_detail = ""
        self._engines_checked = False

    def run(self):
        """Run the translation loop."""
        self._running = True
        logger.info("Translation worker started")

        # Check engines in background thread (don't block startup)
        threading.Thread(target=self._check_all_engines, daemon=True).start()

        while self._running:
            try:
                msg = self._text_queue.get(timeout=0.5)
                if not self._enabled:
                    self._subtitle_queue.put({
                        "original": msg["text"],
                        "translated": "",
                        "timestamp": msg["timestamp"]
                    })
                    continue

                translated = self._translate(msg["text"])
                if translated:
                    logger.debug("Translated: '%s' → '%s'", msg["text"][:30], translated[:30])
                self._subtitle_queue.put({
                    "original": msg["text"],
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
        """Set translation mode (offline/online/ltengine)."""
        self._mode = mode
        self._update_status()

    def set_languages(self, source: str, target: str):
        """Set source and target languages."""
        self._source_language = source
        self._target_language = target

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
        """Check all translation engines and update status (for UI display only)."""
        self._engines_checked = False

        # Check Argos
        self._status_detail = "checking argos..."
        logger.info("Checking Argos Translate...")
        if self._argos.is_ready:
            logger.info("Argos Translate: ready")
        else:
            logger.info("Argos Translate: not ready (no packages installed)")

        # Check LibreTranslate
        self._status_detail = "checking libre..."
        logger.info("Checking LibreTranslate...")
        libre_ok = self._libre.check_connection()
        if libre_ok:
            logger.info("LibreTranslate: available")
        else:
            logger.info("LibreTranslate: not available")

        # Check LTEngine
        self._status_detail = "checking ltengine..."
        logger.info("Checking LTEngine...")
        lt_ok = self._ltengine.check_connection()
        if lt_ok:
            logger.info("LTEngine: available")
        else:
            logger.info("LTEngine: not available")

        self._engines_checked = True
        self._update_status()
        logger.info("Engine check complete. Status: %s", self._status)

    def _translate(self, text: str) -> str:
        """Translate text using the user-selected engine mode.

        If the selected engine fails, returns the original text as fallback
        so the user still sees subtitles.
        """
        if self._source_language == "auto":
            logger.debug("Source=auto, passing through: '%s'", text[:50])
            return text

        try:
            if self._mode == TRANSLATION_MODE_ONLINE:
                result = self._libre.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "online"
                    return result
                logger.warning("LibreTranslate returned no result, falling back to original")

            elif self._mode == TRANSLATION_MODE_LTENGINE:
                result = self._ltengine.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "ltengine"
                    return result
                logger.warning("LTEngine returned no result, falling back to original")

            else:
                # Offline mode - Argos
                result = self._argos.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "offline"
                    return result
                logger.warning("Argos returned no result, falling back to original")

            self._update_status()
            return text  # Fallback: show original text

        except Exception as e:
            logger.error("Translation error: %s, falling back to original", e)
            self._update_status()
            return text  # Fallback: show original text

    def _update_status(self):
        """Update the status indicator based on current mode and engine availability."""
        if self._mode == TRANSLATION_MODE_ONLINE:
            if self._libre.is_available:
                self._status = "online"
            else:
                self._status = "not_ready"
                self._status_detail = "LibreTranslate unavailable"

        elif self._mode == TRANSLATION_MODE_LTENGINE:
            if self._ltengine.is_available:
                self._status = "ltengine"
            else:
                self._status = "not_ready"
                self._status_detail = "LTEngine unavailable"

        else:  # offline
            if self._argos.is_ready:
                self._status = "offline"
            else:
                self._status = "not_ready"
                self._status_detail = "Argos packages not installed"

    def install_argos_package(self, from_code: str, to_code: str) -> bool:
        """Install an Argos translation package."""
        return self._argos.install_package(from_code, to_code)