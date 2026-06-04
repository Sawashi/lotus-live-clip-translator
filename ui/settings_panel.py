"""Settings panel widget for the main window.

Provides all controls for configuring the application.
"""

import os
import json
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QCheckBox, QGroupBox, QGridLayout,
    QColorDialog, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)

LANGUAGES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "languages.json")
MODEL_OPTIONS = [
    ("tiny", "Tiny – fastest, least accurate"),
    ("small", "Small – balanced speed/accuracy (default)"),
    ("medium", "Medium – slower, more accurate")
]


def load_languages() -> dict:
    """Load language definitions from JSON."""
    try:
        with open(LANGUAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load languages: %s", e)
        return {"whisper_languages": [], "translation_pairs": []}


class SettingsPanel(QWidget):
    """Configurable settings for translation and overlay."""

    settings_changed = pyqtSignal()
    capture_toggled = pyqtSignal(bool)  # True = start, False = stop

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lang_data = load_languages()
        self._selected_color = "#FFFFFF"
        self._capturing = False
        self._init_ui()

    def _init_ui(self):
        """Build the settings panel layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Audio Control ---
        audio_group = QGroupBox("Audio Capture")
        audio_layout = QVBoxLayout(audio_group)

        self._start_btn = QPushButton("▶  Start Capture")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.clicked.connect(self._on_start_stop)
        audio_layout.addWidget(self._start_btn)

        self._device_label = QLabel("Device: Not started")
        audio_layout.addWidget(self._device_label)

        self._model_status = QLabel("Model: Not loaded")
        audio_layout.addWidget(self._model_status)

        layout.addWidget(audio_group)

        # --- Language Selection ---
        lang_group = QGroupBox("Language")
        lang_layout = QGridLayout(lang_group)

        lang_layout.addWidget(QLabel("Source:"), 0, 0)
        self._source_lang = QComboBox()
        self._populate_languages(self._source_lang, include_auto=True)
        self._source_lang.currentIndexChanged.connect(self._emit_change)
        lang_layout.addWidget(self._source_lang, 0, 1)

        lang_layout.addWidget(QLabel("Target:"), 1, 0)
        self._target_lang = QComboBox()
        self._populate_languages(self._target_lang, include_auto=False)
        self._target_lang.setCurrentText("English")
        self._target_lang.currentIndexChanged.connect(self._emit_change)
        lang_layout.addWidget(self._target_lang, 1, 1)

        layout.addWidget(lang_group)

        # --- Translation ---
        trans_group = QGroupBox("Translation")
        trans_layout = QVBoxLayout(trans_group)

        self._translation_toggle = QCheckBox("Enable Translation")
        self._translation_toggle.setChecked(True)
        self._translation_toggle.stateChanged.connect(self._emit_change)
        trans_layout.addWidget(self._translation_toggle)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self._translation_mode = QComboBox()
        self._translation_mode.addItem("Offline (Argos)", "offline")
        self._translation_mode.addItem("Online (LibreTranslate)", "online")
        self._translation_mode.currentIndexChanged.connect(self._emit_change)
        mode_layout.addWidget(self._translation_mode)
        mode_layout.addStretch()
        trans_layout.addLayout(mode_layout)

        self._translation_status = QLabel("Translation: Offline")
        trans_layout.addWidget(self._translation_status)

        layout.addWidget(trans_group)

        # --- Display Mode ---
        display_group = QGroupBox("Display Mode")
        display_layout = QVBoxLayout(display_group)

        self._display_mode = QComboBox()
        self._display_mode.addItem("Original Only", "original")
        self._display_mode.addItem("Translated Only", "translated")
        self._display_mode.addItem("Bilingual", "bilingual")
        self._display_mode.setCurrentText("Bilingual")
        self._display_mode.currentIndexChanged.connect(self._emit_change)
        display_layout.addWidget(self._display_mode)

        layout.addWidget(display_group)

        # --- Overlay Settings ---
        overlay_group = QGroupBox("Overlay Settings")
        overlay_layout = QGridLayout(overlay_group)

        overlay_layout.addWidget(QLabel("Font Size:"), 0, 0)
        self._font_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_slider.setRange(12, 72)
        self._font_slider.setValue(24)
        self._font_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._font_slider, 0, 1)
        self._font_label = QLabel("24")
        self._font_slider.valueChanged.connect(lambda v: self._font_label.setText(str(v)))
        overlay_layout.addWidget(self._font_label, 0, 2)

        overlay_layout.addWidget(QLabel("Opacity:"), 1, 0)
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(70)
        self._opacity_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._opacity_slider, 1, 1)
        self._opacity_label = QLabel("70%")
        self._opacity_slider.valueChanged.connect(lambda v: self._opacity_label.setText(f"{v}%"))
        overlay_layout.addWidget(self._opacity_label, 1, 2)

        overlay_layout.addWidget(QLabel("Line Spacing:"), 2, 0)
        self._spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self._spacing_slider.setRange(5, 30)
        self._spacing_slider.setValue(12)
        self._spacing_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._spacing_slider, 2, 1)
        self._spacing_label = QLabel("1.2")
        self._spacing_slider.valueChanged.connect(
            lambda v: self._spacing_label.setText(f"{v / 10:.1f}")
        )
        overlay_layout.addWidget(self._spacing_label, 2, 2)

        # Color picker
        self._color_btn = QPushButton("Text Color")
        self._color_btn.clicked.connect(self._pick_color)
        overlay_layout.addWidget(self._color_btn, 3, 0, 1, 3)

        layout.addWidget(overlay_group)

        # --- Whisper Model ---
        model_group = QGroupBox("Whisper Model")
        model_layout = QVBoxLayout(model_group)

        self._model_selector = QComboBox()
        for value, label in MODEL_OPTIONS:
            self._model_selector.addItem(label, value)
        self._model_selector.currentIndexChanged.connect(self._emit_change)
        model_layout.addWidget(self._model_selector)

        note = QLabel("Note: Larger models are more accurate but slower and use more RAM.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        model_layout.addWidget(note)

        layout.addWidget(model_group)

        # --- Theme ---
        theme_group = QGroupBox("Theme")
        theme_layout = QHBoxLayout(theme_group)
        self._theme_selector = QComboBox()
        self._theme_selector.addItem("Dark", "dark")
        self._theme_selector.addItem("Light", "light")
        self._theme_selector.currentIndexChanged.connect(self._emit_change)
        theme_layout.addWidget(self._theme_selector)
        layout.addWidget(theme_group)

        # --- Utility Buttons ---
        util_layout = QHBoxLayout()

        self._log_btn = QPushButton("Open Log Folder")
        self._log_btn.clicked.connect(self._open_log_folder)
        util_layout.addWidget(self._log_btn)

        self._reset_btn = QPushButton("Reset Settings")
        self._reset_btn.clicked.connect(self._reset_settings)
        util_layout.addWidget(self._reset_btn)

        layout.addLayout(util_layout)

        layout.addStretch()
        self.setLayout(layout)

    def _populate_languages(self, combo, include_auto=False):
        """Fill a combo box with language options."""
        if include_auto:
            combo.addItem("Auto Detect", "auto")
        for lang in self._lang_data.get("whisper_languages", []):
            combo.addItem(lang["name"], lang["code"])

    def _on_start_stop(self):
        """Toggle capture state."""
        self._capturing = not self._capturing
        self._start_btn.setText("■  Stop Capture" if self._capturing else "▶  Start Capture")
        self.capture_toggled.emit(self._capturing)

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(QColor(self._selected_color), self, "Select Text Color")
        if color.isValid():
            self._selected_color = color.name()
            self._emit_change()

    def _open_log_folder(self):
        """Open the log folder in file explorer."""
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LiveTranslateOverlay", "logs")
        os.makedirs(log_dir, exist_ok=True)
        os.startfile(log_dir)

    def _reset_settings(self):
        """Reset to default settings."""
        self._font_slider.setValue(24)
        self._opacity_slider.setValue(70)
        self._spacing_slider.setValue(12)
        self._source_lang.setCurrentText("Auto Detect")
        self._target_lang.setCurrentText("English")
        self._display_mode.setCurrentText("Bilingual")
        self._model_selector.setCurrentIndex(1)
        self._theme_selector.setCurrentText("Dark")
        self._translation_toggle.setChecked(True)
        self._translation_mode.setCurrentText("Offline (Argos)")
        self._selected_color = "#FFFFFF"
        self._emit_change()

    def _emit_change(self):
        """Emit settings changed signal."""
        self.settings_changed.emit()

    # ---- Getters for settings values ----

    def get_settings(self) -> dict:
        """Return current settings as a dict."""
        return {
            "source_language": self._source_lang.currentData(),
            "target_language": self._target_lang.currentData(),
            "translation_enabled": self._translation_toggle.isChecked(),
            "translation_mode": self._translation_mode.currentData(),
            "display_mode": self._display_mode.currentData(),
            "whisper_model": self._model_selector.currentData(),
            "font_size": self._font_slider.value(),
            "font_color": self._selected_color,
            "overlay_opacity": self._opacity_slider.value() / 100.0,
            "line_spacing": self._spacing_slider.value() / 10.0,
            "theme": self._theme_selector.currentData(),
        }

    def apply_settings(self, settings: dict):
        """Apply settings from a dict."""
        # Block signals during bulk update
        self.blockSignals(True)

        # Source language
        src_code = settings.get("source_language", "auto")
        for i in range(self._source_lang.count()):
            if self._source_lang.itemData(i) == src_code:
                self._source_lang.setCurrentIndex(i)
                break

        # Target language
        tgt_code = settings.get("target_language", "en")
        for i in range(self._target_lang.count()):
            if self._target_lang.itemData(i) == tgt_code:
                self._target_lang.setCurrentIndex(i)
                break

        self._translation_toggle.setChecked(settings.get("translation_enabled", True))

        mode = settings.get("translation_mode", "offline")
        for i in range(self._translation_mode.count()):
            if self._translation_mode.itemData(i) == mode:
                self._translation_mode.setCurrentIndex(i)
                break

        display = settings.get("display_mode", "bilingual")
        for i in range(self._display_mode.count()):
            if self._display_mode.itemData(i) == display:
                self._display_mode.setCurrentIndex(i)
                break

        model = settings.get("whisper_model", "small")
        for i in range(self._model_selector.count()):
            if self._model_selector.itemData(i) == model:
                self._model_selector.setCurrentIndex(i)
                break

        self._font_slider.setValue(settings.get("font_size", 24))
        self._selected_color = settings.get("font_color", "#FFFFFF")
        self._opacity_slider.setValue(int(settings.get("overlay_opacity", 0.7) * 100))
        self._spacing_slider.setValue(int(settings.get("line_spacing", 1.2) * 10))

        theme = settings.get("theme", "dark")
        for i in range(self._theme_selector.count()):
            if self._theme_selector.itemData(i) == theme:
                self._theme_selector.setCurrentIndex(i)
                break

        self.blockSignals(False)

    # ---- Status updates ----

    def set_device_status(self, text: str):
        """Update audio device status label."""
        self._device_label.setText(f"Device: {text}")

    def set_model_status(self, text: str):
        """Update model loading status label."""
        self._model_status.setText(f"Model: {text}")

    def set_translation_status(self, text: str):
        """Update translation status label."""
        self._translation_status.setText(f"Translation: {text}")

    def set_capturing(self, capturing: bool):
        """Update start/stop button state."""
        self._start_btn.setText("■  Stop Capture" if capturing else "▶  Start Capture")