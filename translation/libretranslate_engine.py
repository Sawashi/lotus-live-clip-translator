"""Online translation engine using LibreTranslate public API.

Provides better quality translation when internet is available.
Falls back gracefully on failure.
"""

import logging
import requests

logger = logging.getLogger(__name__)

PUBLIC_API_URL = "https://libretranslate.com/translate"

# Language code mapping for LibreTranslate compatibility
LANG_MAP = {
    "en": "en",
    "ja": "ja",
    "zh": "zh",
    "ko": "ko",
    "vi": "vi",
    "es": "es",
    "fr": "fr",
    "de": "de"
}


class LibreTranslateEngine:
    """Online translation via LibreTranslate public API."""

    def __init__(self, api_url: str = PUBLIC_API_URL):
        self._api_url = api_url
        self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def check_connection(self) -> bool:
        """Check if LibreTranslate is reachable."""
        try:
            resp = requests.get(
                PUBLC_API_URL.replace("/translate", "/languages"),
                timeout=3
            )
            self._available = resp.status_code == 200
            return self._available
        except requests.RequestException:
            self._available = False
            return False

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Translate text using LibreTranslate API.

        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code

        Returns:
            Translated text, or empty string on failure
        """
        if not text or not text.strip():
            return ""

        src = LANG_MAP.get(from_code, from_code)
        tgt = LANG_MAP.get(to_code, to_code)

        try:
            resp = requests.post(
                self._api_url,
                json={
                    "q": text,
                    "source": src,
                    "target": tgt,
                    "format": "text"
                },
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json().get("translatedText", "")
                logger.debug("LibreTranslate: '%s' → '%s'", text[:50], result[:50])
                return result
            else:
                logger.warning("LibreTranslate returned %d: %s", resp.status_code, resp.text)
                return ""

        except requests.RequestException as e:
            logger.warning("LibreTranslate request failed: %s", e)
            self._available = False
            return ""
        except (ValueError, KeyError) as e:
            logger.error("LibreTranslate parse error: %s", e)
            return ""