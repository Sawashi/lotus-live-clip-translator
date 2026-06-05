"""Settings panel widget for the main window.

Provides all controls for configuring the application.
"""

import os
import json
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QCheckBox, QGroupBox, QGridLayout,
    QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QWheelEvent

logger = logging.getLogger(__name__)

LANGUAGES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "languages.json")
MODEL_OPTIONS = [
    ("tiny", "Tiny – fastest, least accurate"),
    ("small", "Small – balanced speed/accuracy (default)"),
    ("medium", "Medium – slower, more accurate")
]

# Layout constants
GROUP_MARGINS = 10
GROUP_SPACING = 8
SECTION_SPACING = 12
SLIDER_VALUE_WIDTH = 44


def load_languages() -> dict:
    """Load language definitions from JSON."""
    try:
        with open(LANGUAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load languages: %s", e)
        return {"whisper_languages": []}


class WheelIgnoringSlider(QSlider):
    """Slider that ignores mouse wheel."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class WheelIgnoringComboBox(QComboBox):
    """ComboBox that ignores mouse wheel."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class SettingsPanel(QWidget):
    """Configurable settings for translation and overlay."""

    settings_changed = pyqtSignal()
    capture_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lang_data = load_languages()
        self._argos_pairs = self._lang_data.get("argos_pairs", {})
        self._small100_pairs = self._lang_data.get("small100_pairs", {})
        self._selected_color = "#FFFFFF"
        self._capturing = False
        self._engine = "argos"  # default
        self._init_ui()

    def _init_ui(self):
        """Build the settings panel layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SECTION_SPACING)
        layout.setContentsMargins(8, 8, 8, 8)

        # --- Audio Control ---
        audio_group = QGroupBox("Audio Capture")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        audio_layout.setSpacing(GROUP_SPACING)

        self._start_btn = QPushButton("▶  Start Capture")
        self._start_btn.setMinimumHeight(70)
        self._start_btn.clicked.connect(self._on_start_stop)
        audio_layout.addWidget(self._start_btn)

        self._device_label = QLabel("Device: Not started")
        self._device_label.setMinimumHeight(28)
        audio_layout.addWidget(self._device_label)

        self._model_status = QLabel("Model: Not loaded")
        self._model_status.setMinimumHeight(28)
        audio_layout.addWidget(self._model_status)

        # Buffer duration
        buf_row = QHBoxLayout()
        buf_row.setSpacing(6)
        buf_row.addWidget(QLabel("Buffer:"))
        self._buffer_slider = WheelIgnoringSlider(Qt.Orientation.Horizontal)
        self._buffer_slider.setRange(5, 50)
        self._buffer_slider.setValue(19)
        self._buffer_slider.valueChanged.connect(self._emit_change)
        buf_row.addWidget(self._buffer_slider, 1)
        self._buffer_label = QLabel("1.9s")
        self._buffer_label.setFixedWidth(36)
        self._buffer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._buffer_slider.valueChanged.connect(
            lambda v: self._buffer_label.setText(f"{v / 10:.1f}s")
        )
        buf_row.addWidget(self._buffer_label)
        audio_layout.addLayout(buf_row)

        buf_note = QLabel("Lower buffer if speaking slow, increase if fast.\nGood range: 1.5s – 2.0s")
        buf_note.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        buf_note.setWordWrap(True)
        audio_layout.addWidget(buf_note)

        layout.addWidget(audio_group)

        # --- Language Selection ---
        lang_group = QGroupBox("Language")
        lang_layout = QGridLayout(lang_group)
        lang_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        lang_layout.setSpacing(GROUP_SPACING)
        lang_layout.setColumnStretch(0, 0)
        lang_layout.setColumnStretch(1, 1)

        lang_layout.addWidget(QLabel("Source:"), 0, 0)
        self._source_lang = WheelIgnoringComboBox()
        self._source_lang.setMinimumWidth(160)
        self._populate_languages(self._source_lang, include_auto=False)
        self._source_lang.currentIndexChanged.connect(self._on_source_lang_changed)
        lang_layout.addWidget(self._source_lang, 0, 1)

        lang_layout.addWidget(QLabel("Target:"), 1, 0)
        self._target_lang = WheelIgnoringComboBox()
        self._target_lang.setMinimumWidth(160)
        lang_layout.addWidget(self._target_lang, 1, 1)

        # Constraint note
        self._lang_note = QLabel("⚠ slower options use 2-hop via English (source→en→target).")
        self._lang_note.setStyleSheet("color: #FF9800; font-size: 10px; font-style: italic;")
        self._lang_note.setWordWrap(True)
        lang_layout.addWidget(self._lang_note, 2, 0, 1, 2)

        layout.addWidget(lang_group)

        # --- Whisper Model (moved between Language and Translation) ---
        model_group = QGroupBox("Whisper Model")
        model_layout = QVBoxLayout(model_group)
        model_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        model_layout.setSpacing(GROUP_SPACING)

        self._model_selector = WheelIgnoringComboBox()
        self._model_selector.setMinimumWidth(280)
        for value, label in MODEL_OPTIONS:
            self._model_selector.addItem(label, value)
        self._model_selector.currentIndexChanged.connect(self._on_model_selection_changed)
        model_layout.addWidget(self._model_selector)

        download_row = QHBoxLayout()
        download_row.setSpacing(8)
        self._model_status_label = QLabel("")
        download_row.addWidget(self._model_status_label, 1)
        self._download_btn = QPushButton("Download")
        self._download_btn.setMinimumHeight(32)
        self._download_btn.clicked.connect(self._download_selected_model)
        self._download_btn.setEnabled(False)
        download_row.addWidget(self._download_btn)
        model_layout.addLayout(download_row)

        self._update_model_download_status()

        model_layout.addWidget(QLabel(
            "Note: Larger models are more accurate but slower and use more RAM"
        ))
        model_layout.addWidget(QLabel(
            "Note: Choose tiny if you dont have a vga."
        ))

        layout.addWidget(model_group)

        # --- Translation ---
        trans_group = QGroupBox("Translation")
        trans_layout = QVBoxLayout(trans_group)
        trans_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        trans_layout.setSpacing(GROUP_SPACING)

        self._translation_toggle = QCheckBox("Enable Translation")
        self._translation_toggle.setChecked(True)
        self._translation_toggle.stateChanged.connect(self._emit_change)
        trans_layout.addWidget(self._translation_toggle)

        # Engine selector
        engine_row = QHBoxLayout()
        engine_row.setSpacing(6)
        engine_row.addWidget(QLabel("Engine:"))
        self._engine_selector = WheelIgnoringComboBox()
        self._engine_selector.setMinimumWidth(160)
        self._engine_selector.addItem("Argos Translate", "argos")
        self._engine_selector.addItem("Small100 (M2M-100)", "small100")
        self._engine_selector.currentIndexChanged.connect(self._on_engine_changed)
        engine_row.addWidget(self._engine_selector, 1)
        trans_layout.addLayout(engine_row)

        self._translation_status = QLabel("Translation: Not ready (checking engines...)")
        self._translation_status.setMinimumHeight(35)
        trans_layout.addWidget(self._translation_status)
        trans_layout.addWidget(QLabel("Note: Choose Argos if you dont have a vga"))

        layout.addWidget(trans_group)

        # --- Display Mode ---
        display_group = QGroupBox("Display Mode")
        display_layout = QVBoxLayout(display_group)
        display_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        display_layout.setSpacing(GROUP_SPACING)

        self._display_mode = WheelIgnoringComboBox()
        self._display_mode.setMinimumWidth(200)
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
        overlay_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        overlay_layout.setSpacing(GROUP_SPACING)
        overlay_layout.setColumnStretch(0, 0)
        overlay_layout.setColumnStretch(1, 1)
        overlay_layout.setColumnStretch(2, 0)

        overlay_layout.setRowMinimumHeight(0, 10)
        overlay_layout.setRowMinimumHeight(1, 10)
        overlay_layout.setRowMinimumHeight(2, 10)
        overlay_layout.setRowMinimumHeight(3, 10)

        overlay_layout.addWidget(QLabel("Font Size:"), 0, 0)
        self._font_slider = WheelIgnoringSlider(Qt.Orientation.Horizontal)
        self._font_slider.setRange(12, 72)
        self._font_slider.setValue(24)
        self._font_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._font_slider, 0, 1)
        self._font_label = QLabel("24")
        self._font_label.setFixedWidth(SLIDER_VALUE_WIDTH)
        self._font_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._font_slider.valueChanged.connect(lambda v: self._font_label.setText(str(v)))
        overlay_layout.addWidget(self._font_label, 0, 2)

        overlay_layout.addWidget(QLabel("Opacity:"), 1, 0)
        self._opacity_slider = WheelIgnoringSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(70)
        self._opacity_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._opacity_slider, 1, 1)
        self._opacity_label = QLabel("70%")
        self._opacity_label.setFixedWidth(SLIDER_VALUE_WIDTH)
        self._opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._opacity_slider.valueChanged.connect(lambda v: self._opacity_label.setText(f"{v}%"))
        overlay_layout.addWidget(self._opacity_label, 1, 2)

        overlay_layout.addWidget(QLabel("Spacing:"), 2, 0)
        self._spacing_slider = WheelIgnoringSlider(Qt.Orientation.Horizontal)
        self._spacing_slider.setRange(5, 30)
        self._spacing_slider.setValue(12)
        self._spacing_slider.valueChanged.connect(self._emit_change)
        overlay_layout.addWidget(self._spacing_slider, 2, 1)
        self._spacing_label = QLabel("1.2")
        self._spacing_label.setFixedWidth(SLIDER_VALUE_WIDTH)
        self._spacing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spacing_slider.valueChanged.connect(
            lambda v: self._spacing_label.setText(f"{v / 10:.1f}")
        )
        overlay_layout.addWidget(self._spacing_label, 2, 2)

        self._color_btn = QPushButton("Text Color")
        self._color_btn.setMinimumHeight(36)
        self._color_btn.clicked.connect(self._pick_color)
        overlay_layout.addWidget(self._color_btn, 3, 0, 1, 3)

        layout.addWidget(overlay_group)

        # --- Theme ---
        theme_group = QGroupBox("Theme")
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.setContentsMargins(GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS, GROUP_MARGINS)
        theme_layout.setSpacing(GROUP_SPACING)
        self._theme_selector = WheelIgnoringComboBox()
        self._theme_selector.setMinimumWidth(160)
        self._theme_selector.addItem("Dark", "dark")
        self._theme_selector.addItem("Light", "light")
        self._theme_selector.currentIndexChanged.connect(self._emit_change)
        theme_layout.addWidget(self._theme_selector)
        theme_layout.addStretch()
        layout.addWidget(theme_group)

        # --- Utility Buttons ---
        util_layout = QHBoxLayout()
        util_layout.setSpacing(GROUP_SPACING)

        self._log_btn = QPushButton("Open Log Folder")
        self._log_btn.setMinimumHeight(36)
        self._log_btn.clicked.connect(self._open_log_folder)
        util_layout.addWidget(self._log_btn)

        self._reset_btn = QPushButton("Reset Settings")
        self._reset_btn.setMinimumHeight(36)
        self._reset_btn.clicked.connect(self._reset_settings)
        util_layout.addWidget(self._reset_btn)

        layout.addLayout(util_layout)

        # --- Credit ---
        credit_label = QLabel("Credit by Sawashi - Kiet Le")
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_label.setStyleSheet("color: #888; font-size: 11px; padding: 6px;")
        layout.addWidget(credit_label)

        layout.addStretch()
        self.setLayout(layout)

        # Set defaults: en → vi, then populate target
        self._source_lang.setCurrentIndex(0)  # English is first
        self._rebuild_target_lang(self._source_lang.currentData())

    def _populate_languages(self, combo: QComboBox, include_auto: bool = False):
        """Fill a combo box with language options."""
        if include_auto:
            combo.addItem("Auto Detect", "auto")
        for lang in self._lang_data.get("whisper_languages", []):
            if lang["code"] == "auto":
                continue
            combo.addItem(lang["name"], lang["code"])

    def _rebuild_target_lang(self, src_code: str):
        """Rebuild target lang combo based on source and active engine.

        For Argos:
          - no marker = direct translation (fast, 1 hop)
          - ⚠ slower = via English (2 hops: src → en → target)
        For Small100: all pairs direct, no markers.
        """
        self._target_lang.blockSignals(True)
        self._target_lang.clear()

        if self._engine == "small100":
            pairs = self._small100_pairs
            direct_codes = set(pairs.get(src_code, []))
            for lang in self._lang_data.get("whisper_languages", []):
                code = lang["code"]
                if code == src_code:
                    continue
                if code in direct_codes:
                    self._target_lang.addItem(lang["name"], ("direct", code))
        else:
            direct_codes = set(self._argos_pairs.get(src_code, []))
            en_targets = set(self._argos_pairs.get("en", []))
            for lang in self._lang_data.get("whisper_languages", []):
                code = lang["code"]
                if code == src_code:
                    continue
                if code in direct_codes:
                    self._target_lang.addItem(lang["name"], ("direct", code))
                elif src_code != "en" and "en" in self._argos_pairs.get(src_code, []) and code in en_targets:
                    self._target_lang.addItem(f"{lang['name']} ⚠ slower", ("hop2", code))

        # Select Vietnamese if available, else first item
        vi_idx = None
        for i in range(self._target_lang.count()):
            item = self._target_lang.itemData(i)
            if isinstance(item, tuple) and item[1] == "vi":
                vi_idx = i
                break
        if vi_idx is not None:
            self._target_lang.setCurrentIndex(vi_idx)
        elif self._target_lang.count() > 0:
            self._target_lang.setCurrentIndex(0)

        self._target_lang.blockSignals(False)
        self._emit_change()

    def _on_engine_changed(self):
        """Engine selection changed → rebuild target options."""
        self._engine = self._engine_selector.currentData()
        # Show/hide the hop2 warning note
        if self._engine == "small100":
            self._lang_note.setVisible(False)
        else:
            self._lang_note.setVisible(True)
        src = self._source_lang.currentData()
        self._rebuild_target_lang(src)

    def _on_source_lang_changed(self):
        """Source language changed → rebuild target options."""
        src = self._source_lang.currentData()
        self._rebuild_target_lang(src)

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
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LotusTranslator", "logs")
        os.makedirs(log_dir, exist_ok=True)
        os.startfile(log_dir)

    def _reset_settings(self):
        """Reset to default settings."""
        self._font_slider.setValue(24)
        self._opacity_slider.setValue(20)
        self._spacing_slider.setValue(12)
        self._buffer_slider.setValue(19)
        self._buffer_label.setText("1.9s")
        self._source_lang.setCurrentIndex(0)  # English
        # target rebuilds via _on_source_lang_changed → _rebuild_target_lang which picks vi
        self._display_mode.setCurrentText("Bilingual")
        self._model_selector.setCurrentIndex(1)
        self._theme_selector.setCurrentText("Dark")
        self._translation_toggle.setChecked(True)
        self._engine_selector.setCurrentIndex(1)  # Argos (default)
        self._selected_color = "#FFFFFF"
        self._emit_change()
        # Reposition overlay to screen center and reset size
        main_window = self.window()
        if hasattr(main_window, '_overlay') and main_window._overlay:
            main_window._overlay.center_on_screen_and_reset_size()

    def _on_model_selection_changed(self):
        """Update download status and emit change when model selection changes."""
        self._update_model_download_status()
        self._emit_change()

    def _emit_change(self):
        """Emit settings changed signal."""
        self.settings_changed.emit()

    # ---- Getters for settings values ----

    def get_target_data(self) -> tuple:
        """Get (mode, code) tuple from target combo, e.g. ('direct', 'ja') or ('hop2', 'vi')."""
        data = self._target_lang.currentData()
        if data is None:
            return ("direct", "vi")
        return data

    def get_settings(self) -> dict:
        """Return current settings as a dict."""
        mode, tgt_code = self.get_target_data()
        return {
            "source_language": self._source_lang.currentData(),
            "target_language": tgt_code,
            "target_mode": mode,
            "translation_enabled": self._translation_toggle.isChecked(),
            "translation_mode": "offline",
            "translation_engine": self._engine_selector.currentData(),
            "display_mode": self._display_mode.currentData(),
            "whisper_model": self._model_selector.currentData(),
            "font_size": self._font_slider.value(),
            "font_color": self._selected_color,
            "overlay_opacity": self._opacity_slider.value() / 100.0,
            "line_spacing": self._spacing_slider.value() / 10.0,
            "theme": self._theme_selector.currentData(),
            "buffer_duration": self._buffer_slider.value() / 10.0,
        }

    def apply_settings(self, settings: dict):
        """Apply settings from a dict."""
        self.blockSignals(True)

        src_code = settings.get("source_language", "en")
        for i in range(self._source_lang.count()):
            if self._source_lang.itemData(i) == src_code:
                self._source_lang.setCurrentIndex(i)
                break

        # Rebuild target after source set
        self._rebuild_target_lang(self._source_lang.currentData())

        tgt_code = settings.get("target_language", "vi")
        for i in range(self._target_lang.count()):
            item = self._target_lang.itemData(i)
            if isinstance(item, tuple) and item[1] == tgt_code:
                self._target_lang.setCurrentIndex(i)
                break
            elif item == tgt_code:
                self._target_lang.setCurrentIndex(i)
                break

        self._translation_toggle.setChecked(settings.get("translation_enabled", True))

        # Apply engine selector
        engine = settings.get("translation_engine", "argos")
        for i in range(self._engine_selector.count()):
            if self._engine_selector.itemData(i) == engine:
                self._engine_selector.setCurrentIndex(i)
                break
        self._engine = engine  # sync internal state

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
        buf = settings.get("buffer_duration", 1.9)
        self._buffer_slider.setValue(int(buf * 10))
        self._buffer_label.setText(f"{buf:.1f}s")

        theme = settings.get("theme", "dark")
        for i in range(self._theme_selector.count()):
            if self._theme_selector.itemData(i) == theme:
                self._theme_selector.setCurrentIndex(i)
                break

        self.blockSignals(False)
        self._update_model_download_status()

    # ---- Model download management ----

    @staticmethod
    def _model_dir() -> str:
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

    def _check_model_on_disk(self, size: str) -> bool:
        """Check if a Whisper model is fully downloaded on disk."""
        import glob
        pattern = os.path.join(self._model_dir(), f"models--Systran--faster-whisper-{size}", "snapshots", "*", "model.bin")
        return len(glob.glob(pattern)) > 0

    def _update_model_download_status(self):
        """Update the download status label and button state."""
        selected = self._model_selector.currentData()
        on_disk = self._check_model_on_disk(selected)
        if on_disk:
            self._model_status_label.setText("✓ Downloaded")
            self._model_status_label.setStyleSheet("color: #4CAF50;")
            self._download_btn.setText("Downloaded")
            self._download_btn.setEnabled(False)
        else:
            size_map = {"tiny": "~150 MB", "small": "~460 MB", "medium": "~1.5 GB"}
            est = size_map.get(selected, "")
            self._model_status_label.setText(f"Not downloaded {est}")
            self._model_status_label.setStyleSheet("color: #FF9800;")
            self._download_btn.setText("Download")
            self._download_btn.setEnabled(True)

    def _download_selected_model(self):
        """Download the selected Whisper model in a background thread with progress."""
        selected = self._model_selector.currentData()
        self._download_btn.setEnabled(False)
        self._download_btn.setText("Downloading...")
        self._model_status_label.setText("0%")
        self._model_status_label.setStyleSheet("color: #2196F3;")

        import threading
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

        size_map = {"tiny": 150_000_000, "small": 470_000_000, "medium": 1_500_000_000}
        total_size = size_map.get(selected, 500_000_000)

        def _poll_progress():
            import glob, os
            while True:
                model_cache_dir = os.path.join(
                    self._model_dir(), f"models--Systran--faster-whisper-{selected}"
                )
                downloaded = 0
                if os.path.isdir(model_cache_dir):
                    for root, dirs, files in os.walk(model_cache_dir):
                        dirs[:] = [d for d in dirs if not d.startswith(".cache") and d != "locks"]
                        downloaded += sum(
                            os.path.getsize(os.path.join(root, f))
                            for f in files
                            if os.path.isfile(os.path.join(root, f))
                            and not f.startswith(".incomplete")
                            and not f.endswith(".lock")
                        )
                pct = min(int(downloaded * 100 / total_size), 99) if total_size > 0 else 0
                try:
                    QMetaObject.invokeMethod(
                        self._model_status_label, "setText",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, f"{pct}%")
                    )
                except RuntimeError:
                    break
                if self._check_model_on_disk(selected):
                    break
                threading.Event().wait(0.5)

        def _do_download():
            poller = threading.Thread(target=_poll_progress, daemon=True)
            poller.start()
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute = "int8"
                from faster_whisper import WhisperModel
                _ = WhisperModel(
                    selected,
                    device=device,
                    compute_type=compute,
                    download_root=self._model_dir()
                )
                self._update_model_download_status()
            except Exception as e:
                logger.error("Download failed: %s", e)
                self._download_btn.setEnabled(True)
                self._download_btn.setText("Retry")
                self._model_status_label.setText(f"Failed: {e}")
                self._model_status_label.setStyleSheet("color: #f44336;")

        t = threading.Thread(target=_do_download, daemon=True)
        t.start()

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