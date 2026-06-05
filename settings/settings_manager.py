"""Settings manager for Lotus Translator.

Handles loading, saving, and migrating application settings
using a JSON config file stored in the user's AppData folder.
"""

import os
import json
import logging
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "theme": "dark",
    "source_language": "auto",
    "target_language": "en",
    "translation_enabled": True,
    "translation_mode": "offline",
    "translation_engine": "argos",
    "display_mode": "bilingual",
    "whisper_model": "small",
    "font_size": 24,
    "font_color": "#FFFFFF",
    "overlay_opacity": 0.7,
    "line_spacing": 1.2,
    "overlay_x": 100,
    "overlay_y": 100,
    "overlay_width": 800,
    "overlay_height": 200,
    "buffer_duration": 1.9,
    # Developer-only: set a date to block the app (format: YYYY-MM-DD)
    # If not set or empty, app runs freely
    "expiry_date": ""
}


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, app_name="LotusTranslator"):
        """Initialize settings manager with AppData path."""
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self._settings = {}
        self._ensure_config_dir()
        self.load()

    def _get_config_dir(self) -> Path:
        """Get platform-specific config directory."""
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".config"
        return base / self.app_name

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def check_expiry(self) -> bool:
        """Check if app is expired. Returns True if still valid."""
        expiry_str = self._settings.get("expiry_date", "")
        # Debug: force print to original stdout so user can see
        try:
            import sys
            sys.stdout.write(f"[DEBUG] check_expiry: expiry_str={expiry_str!r}\n")
            sys.stdout.flush()
        except Exception:
            pass
        if not expiry_str:
            return True  # No expiry set → free to use
        try:
            exp_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            today = date.today()
            if today >= exp_date:
                import sys
                sys.stdout.write(f"[DEBUG] EXPIRED! today={today} >= exp_date={exp_date}\n")
                sys.stdout.flush()
                logger.warning("App expired on %s", expiry_str)
                return False
        except ValueError:
            logger.error("Invalid expiry_date format: %s", expiry_str)
        return True

    def load(self):
        """Load settings from config file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                saved = data.get("settings", {})
                # Merge saved over defaults so missing keys use defaults
                self._settings = DEFAULT_SETTINGS.copy()
                self._settings.update(saved)
                # If expiry_date was saved as empty, reinstate default
                if not self._settings.get("expiry_date"):
                    self._settings["expiry_date"] = DEFAULT_SETTINGS.get("expiry_date", "")
                logger.info("Settings loaded from %s", self.config_file)
            else:
                logger.info("No config file found, using defaults")
                self._settings = DEFAULT_SETTINGS.copy()
                self.save()
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load config: %s", e)
            self._settings = DEFAULT_SETTINGS.copy()

    def save(self):
        """Save current settings to config file."""
        try:
            data = {
                "version": "1.0.0",
                "settings": self._settings
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Settings saved to %s", self.config_file)
        except IOError as e:
            logger.error("Failed to save config: %s", e)

    def get(self, key: str, default=None):
        """Get a setting value by key."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value and save immediately."""
        self._settings[key] = value
        self.save()

    def set_multiple(self, settings: dict):
        """Set multiple settings at once and save."""
        self._settings.update(settings)
        self.save()

    def get_all(self) -> dict:
        """Get all settings as a dictionary."""
        return self._settings.copy()

    def reset(self):
        """Reset all settings to defaults and save."""
        self._settings = DEFAULT_SETTINGS.copy()
        self.save()
        logger.info("Settings reset to defaults")

    def get_config_path(self) -> str:
        """Get the config file path for display purposes."""
        return str(self.config_file)