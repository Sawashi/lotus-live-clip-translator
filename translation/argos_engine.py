"""Offline translation engine using Argos Translate.

Provides fully offline translation with automatic package download.
No API key or internet required after packages are installed.
"""

import os
import logging
import argostranslate.package
import argostranslate.translate

logger = logging.getLogger(__name__)

PACKAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "argos_packages")


class ArgosEngine:
    """Offline translation engine wrapper for Argos Translate."""

    def __init__(self):
        self._installed_pairs = {}
        self._ready = False
        self._ensure_packages_dir()
        self._load_installed_packages()

    def _ensure_packages_dir(self):
        """Create packages directory if needed."""
        os.makedirs(PACKAGES_DIR, exist_ok=True)
        # Set Argos data directory
        argostranslate.package.update_package_index()
        try:
            argostranslate.package.available_packages()
        except Exception:
            pass  # Will fail if offline, that's fine

    def _load_installed_packages(self):
        """Load already installed language packages."""
        try:
            installed = argostranslate.translate.get_installed_languages()
            self._installed_pairs = {}
            for from_lang in installed:
                for to_lang in from_lang:
                    pair_key = f"{from_lang.code}_{to_lang.code}"
                    self._installed_pairs[pair_key] = {
                        "from": from_lang.code,
                        "to": to_lang.code
                    }
            self._ready = len(self._installed_pairs) > 0
            logger.info("Loaded %d installed Argos packages", len(self._installed_pairs))
        except Exception as e:
            logger.warning("No Argos packages installed yet: %s", e)
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def install_package(self, from_code: str, to_code: str) -> bool:
        """Install a translation package.

        Returns True if successful, False otherwise.
        """
        try:
            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()
            package = next(
                (p for p in available if p.from_code == from_code and p.to_code == to_code),
                None
            )
            if package:
                download_path = package.download()
                package.install(download_path)
                self._load_installed_packages()
                logger.info("Installed Argos package: %s → %s", from_code, to_code)
                return True
            else:
                logger.warning("No Argos package available for %s → %s", from_code, to_code)
                return False
        except Exception as e:
            logger.error("Failed to install Argos package: %s", e)
            return False

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Translate text using Argos Translate.

        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code

        Returns:
            Translated text, or empty string on failure
        """
        if not text or not text.strip():
            return ""

        pair_key = f"{from_code}_{to_code}"
        if pair_key not in self._installed_pairs:
            logger.warning("Package not installed for %s → %s, attempting install", from_code, to_code)
            if not self.install_package(from_code, to_code):
                return ""

        try:
            result = argostranslate.translate.translation(text, from_code, to_code)
            logger.debug("Argos translate: '%s' → '%s'", text[:50], result[:50])
            return result
        except Exception as e:
            logger.error("Argos translate error: %s", e)
            return ""

    def get_installed_languages(self) -> list:
        """Get list of installed language codes."""
        return list(set(
            lang for pair in self._installed_pairs.values()
            for lang in [pair["from"], pair["to"]]
        ))