"""Local translation engine using LTEngine (Rust-based LLM translation server).

LTEngine is a self-hosted translation server that runs GGUF models locally.
Uses the same HTTP API format as LibreTranslate for compatibility.
"""

import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_LTENGINE_URL = "http://0.0.0.0:5050"

# Language codes supported by LTEngine (Gemma3 models)
# LTEngine uses standard ISO 639-1 codes, same as LibreTranslate
SUPPORTED_LANGUAGES = [
    "en", "ja", "zh", "ko", "vi", "es", "fr", "de",
    "it", "pt", "ru", "ar", "hi", "th", "id", "ms",
    "tl", "my", "km", "lo", "mn", "ne", "si", "bn"
]


class LTEngine:
    """Local translation via LTEngine HTTP API (Rust binary)."""

    def __init__(self, api_url: str = DEFAULT_LTENGINE_URL):
        self._api_url = api_url.rstrip("/")
        self._available = False
        self._languages_cache = None

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def api_url(self) -> str:
        return self._api_url

    def set_api_url(self, url: str):
        """Set custom LTEngine server URL."""
        self._api_url = url.rstrip("/")
        self._available = False

    def check_connection(self) -> bool:
        """Check if LTEngine server is reachable.

        Tries /languages endpoint (same as LibreTranslate API).
        """
        try:
            resp = requests.get(f"{self._api_url}/languages", timeout=3)
            if resp.status_code == 200:
                self._available = True
                try:
                    self._languages_cache = resp.json()
                except Exception:
                    self._languages_cache = None
                logger.info("LTEngine connected at %s", self._api_url)
                return True
            else:
                logger.debug("LTEngine returned status %d", resp.status_code)
        except requests.ConnectionError:
            logger.debug("LTEngine not reachable at %s", self._api_url)
        except requests.Timeout:
            logger.debug("LTEngine timeout at %s", self._api_url)
        except Exception as e:
            logger.debug("LTEngine check failed: %s", e)

        self._available = False
        return False

    def get_languages(self) -> list:
        """Get list of supported languages from LTEngine server."""
        if self._languages_cache:
            return self._languages_cache
        try:
            resp = requests.get(f"{self._api_url}/languages", timeout=3)
            if resp.status_code == 200:
                self._languages_cache = resp.json()
                return self._languages_cache
        except Exception:
            pass
        return SUPPORTED_LANGUAGES

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Translate text using LTEngine API.

        Uses same request/response format as LibreTranslate.

        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code

        Returns:
            Translated text, or empty string on failure
        """
        if not text or not text.strip():
            return ""

        try:
            payload = {
                "q": text,
                "source": from_code,
                "target": to_code,
                "format": "text"
            }

            resp = requests.post(
                f"{self._api_url}/translate",
                json=payload,
                timeout=30  # LLM inference can be slow
            )

            if resp.status_code == 200:
                data = resp.json()
                result = data.get("translatedText", "")
                if result:
                    self._available = True
                    logger.debug("LTEngine: '%s' → '%s'", text[:50], result[:50])
                    return result
                else:
                    logger.warning("LTEngine returned empty translation")
            else:
                logger.warning(
                    "LTEngine returned %d: %s",
                    resp.status_code, resp.text[:200]
                )

        except requests.ConnectionError:
            logger.warning("LTEngine connection failed (server down?)")
            self._available = False
        except requests.Timeout:
            logger.warning("LTEngine request timed out (model still loading?)")
        except Exception as e:
            logger.error("LTEngine translate error: %s", e)

        return ""