"""Online translation engine using LibreTranslate public API.

Provides better quality translation when internet is available.
Falls back gracefully on failure.
"""

import logging
import requests

logger = logging.getLogger(__name__)

# Multiple public instances to try
# libretranslate.com requires API key, removed from default list
PUBLIC_API_URLS = [
    "https://translate.argosopentech.com/translate",
    "https://libretranslate.de/translate",
    "https://translate.fortytwo-it.com/translate",
    "https://lt.vern.cc/translate",
    "https://libretranslate.pussthecat.org/translate",
]

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

    def __init__(self, api_url: str = None, api_key: str = ""):
        self._api_urls = [api_url] if api_url else PUBLIC_API_URLS
        self._api_key = api_key
        self._available = False
        self._current_url = self._api_urls[0] if self._api_urls else ""

    @property
    def is_available(self) -> bool:
        return self._available

    def check_connection(self) -> bool:
        """Check if any LibreTranslate instance is reachable."""
        for url in self._api_urls:
            try:
                base = url.replace("/translate", "")
                resp = requests.get(f"{base}/languages", timeout=3)
                if resp.status_code == 200:
                    self._available = True
                    self._current_url = url
                    logger.info("LibreTranslate connected via %s", url)
                    return True
            except requests.RequestException:
                continue
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

        # Try each URL in order
        for url in self._api_urls:
            try:
                payload = {
                    "q": text,
                    "source": src,
                    "target": tgt,
                    "format": "text"
                }
                if self._api_key:
                    payload["api_key"] = self._api_key

                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    result = resp.json().get("translatedText", "")
                    if result:
                        self._current_url = url
                        self._available = True
                        logger.debug("LibreTranslate: '%s' → '%s'", text[:50], result[:50])
                        return result
                elif resp.status_code == 400 and "API key" in resp.text:
                    # This instance requires API key, try next
                    continue
                else:
                    logger.warning("LibreTranslate %s returned %d: %s", url, resp.status_code, resp.text[:100])
                    continue

            except requests.RequestException as e:
                logger.warning("LibreTranslate %s failed: %s", url, e)
                continue
            except (ValueError, KeyError) as e:
                logger.error("LibreTranslate parse error: %s", e)
                continue

        self._available = False
        return ""
