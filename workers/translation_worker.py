"""Translation worker thread.

Processes transcribed text and translates it.
Supports offline (Argos) and online (LibreTranslate) modes with fallback.
"""

import queue
import time
import logging
import threading
from translation.argos_engine import ArgosEngine
from translation.libretranslate_engine import LibreTranslateEngine

logger = logging.getLogger(__name__)

TRANSLATION_MODE_OFFLINE = "offline"
TRANSLATION_MODE_ONLINE = "online"


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
        self._running = False
        self._enabled = True
        self._mode = TRANSLATION_MODE_OFFLINE
        self._source_language = "auto"
        self._target_language = "en"
        self._status = "offline"  # offline, online, fallback

    def run(self):
        """Run the translation loop."""
        self._running = True
        logger.info("Translation worker started")
        self._update_status()

        while self._running:
            try:
                msg = self._text_queue.get(timeout=0.5)
                if not self._enabled:
                    # Pass through without translation
                    self._subtitle_queue.put({
                        "original": msg["text"],
                        "translated": "",
                        "timestamp": msg["timestamp"]
                    })
                    continue

                translated = self._translate(msg["text"])
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
        """Set translation mode (offline/online)."""
        self._mode = mode
        self._update_status()

    def set_languages(self, source: str, target: str):
        """Set source and target languages."""
        self._source_language = source
        self._target_language = target

    @property
    def status(self) -> str:
        return self._status

    def _translate(self, text: str) -> str:
        """Translate text using current mode with fallback."""
        if self._source_language == "auto":
            # Can't translate from auto-detect without knowing the language
            # Pass through as-is
            return ""

        try:
            if self._mode == TRANSLATION_MODE_ONLINE:
                result = self._libre.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "online"
                    return result
                # Fallback to offline
                logger.info("LibreTranslate failed, falling back to Argos")
                result = self._argos.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "fallback"
                    return result
            else:
                # Offline mode
                result = self._argos.translate(
                    text, self._source_language, self._target_language
                )
                if result:
                    self._status = "offline"
                    return result
                # Try online as fallback
                if self._libre.check_connection():
                    result = self._libre.translate(
                        text, self._source_language, self._target_language
                    )
                    if result:
                        self._status = "fallback"
                        return result

            self._update_status()
            return ""

        except Exception as e:
            logger.error("Translation error: %s", e)
            self._update_status()
            return ""

    def _update_status(self):
        """Update the status indicator."""
        if self._mode == TRANSLATION_MODE_ONLINE:
            if self._libre.is_available:
                self._status = "online"
            else:
                self._status = "offline" if self._argos.is_ready else "fallback"
        else:
            self._status = "offline" if self._argos.is_ready else "not_ready"

    def install_argos_package(self, from_code: str, to_code: str) -> bool:
        """Install an Argos translation package."""
        return self._argos.install_package(from_code, to_code)