"""Main application window.

Orchestrates all components: audio capture, speech recognition,
translation, and subtitle overlay display.
"""

import os
import sys
import json
import queue
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from overlay.subtitle_overlay import SubtitleOverlay
from ui.settings_panel import SettingsPanel
from settings.settings_manager import SettingsManager
from workers.capture_worker import CaptureWorker
from workers.recognition_worker import RecognitionWorker
from workers.translation_worker import TranslationWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self._settings_manager = SettingsManager()
        self._capturing = False

        # Thread-safe queues for the pipeline
        self._audio_queue = queue.Queue(maxsize=100)
        self._text_queue = queue.Queue(maxsize=50)
        self._subtitle_queue = queue.Queue(maxsize=50)

        # Workers (created on start)
        self._capture_worker = None
        self._recognition_worker = None
        self._translation_worker = None
        self._current_engine = "argos"

        # UI
        self._overlay = None
        self._settings_panel = None

        # Debounce timer for settings save
        self._save_debounce = QTimer(self)
        self._save_debounce.setSingleShot(True)
        self._save_debounce.timeout.connect(self._save_settings)

        self._init_ui()
        self._init_overlay()
        self._init_timers()

        # Load saved settings
        self._load_settings()

    def _init_ui(self):
        """Initialize the main window UI."""
        self.setWindowTitle("Lotus Translator")
        self.setMinimumSize(480, 700)
        self.resize(520, 800)

        # Central widget with horizontal splitter
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Settings panel (scrollable)
        self._settings_panel = SettingsPanel()
        self._settings_panel.settings_changed.connect(self._on_settings_changed)
        self._settings_panel.capture_toggled.connect(self._on_capture_toggled)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._settings_panel)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll)

        # Apply light/dark theme
        self._apply_theme("dark")

        # Menu bar
        self._setup_menu()

    def _setup_menu(self):
        """Create menu bar."""
        menubar = self.menuBar()

        overlay_menu = menubar.addMenu("Overlay")
        toggle_action = QAction("Toggle Drag Mode", self)
        toggle_action.triggered.connect(self._toggle_overlay_mode)
        overlay_menu.addAction(toggle_action)

        clear_action = QAction("Clear Subtitles", self)
        clear_action.triggered.connect(self._clear_subtitles)
        overlay_menu.addAction(clear_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_overlay(self):
        """Create the subtitle overlay window."""
        self._overlay = SubtitleOverlay()
        self._overlay.position_changed.connect(self._on_overlay_moved)
        self._overlay.show()

    def _init_timers(self):
        """Set up polling timers."""
        self._subtitle_timer = QTimer(self)
        self._subtitle_timer.timeout.connect(self._process_subtitle_queue)
        self._subtitle_timer.start(100)

    # ---- Settings ----

    def _load_settings(self):
        """Load and apply saved settings."""
        self._settings_manager.load()
        settings = self._settings_manager.get_all()

        self._settings_panel.apply_settings(settings)
        self._overlay.apply_settings(settings)

        theme = settings.get("theme", "dark")
        self._apply_theme(theme)

    def _save_settings(self):
        """Save current settings."""
        settings = self._settings_panel.get_settings()
        pos = self._overlay.save_position()
        settings.update(pos)
        self._settings_manager.set_multiple(settings)

    def _on_settings_changed(self):
        """Handle settings panel changes."""
        settings = self._settings_panel.get_settings()

        self._overlay.set_font_size(settings["font_size"])
        self._overlay.set_font_color(settings["font_color"])
        self._overlay.set_bg_opacity(settings["overlay_opacity"])
        self._overlay.set_line_spacing(settings["line_spacing"])
        self._overlay.set_display_mode(settings["display_mode"])

        self._apply_theme(settings["theme"])

        if self._capturing:
            self._update_worker_settings(settings)

        self._save_debounce.start(300)

    def _update_worker_settings(self, settings: dict):
        """Push settings changes to running workers."""
        if self._recognition_worker:
            self._recognition_worker.set_language(settings["source_language"])
            self._recognition_worker.set_model(settings["whisper_model"])
            self._recognition_worker.set_buffer_duration(settings.get("buffer_duration", 1.9))

        if self._translation_worker:
            self._translation_worker.set_enabled(settings["translation_enabled"])
            self._translation_worker.set_engine(settings.get("translation_engine", "argos"))
            self._translation_worker.set_languages(
                settings["source_language"],
                settings["target_language"],
                settings.get("target_mode", "direct")
            )

    def _apply_theme(self, theme: str):
        """Apply light or dark theme stylesheet."""
        if theme == "light":
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f5f5; }
                QGroupBox { font-weight: bold; border: 1px solid #ccc;
                            border-radius: 4px; margin-top: 10px; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin;
                                   left: 10px; padding: 0 3px; }
                QLabel { color: #333; }
                QPushButton { background-color: #e0e0e0; border: 1px solid #bbb;
                              border-radius: 4px; padding: 6px 12px; }
                QPushButton:hover { background-color: #d0d0d0; }
                QComboBox { background-color: white; border: 1px solid #bbb;
                            border-radius: 3px; padding: 3px; }
                QScrollArea { background-color: #f5f5f5; border: none; }
                QScrollArea > QWidget > QWidget { background-color: #f5f5f5; }
                QSlider::groove:horizontal { height: 6px; background: #ddd; }
                QSlider::handle:horizontal { width: 14px; margin: -4px 0; }
            """)
        else:  # dark
            self.setStyleSheet("""
                QMainWindow { background-color: #1e1e1e; }
                QGroupBox { font-weight: bold; border: 1px solid #555;
                            border-radius: 4px; margin-top: 10px; padding-top: 10px;
                            color: #ddd; }
                QGroupBox::title { subcontrol-origin: margin;
                                   left: 10px; padding: 0 3px; }
                QLabel { color: #ccc; }
                QPushButton { background-color: #333; border: 1px solid #555;
                              border-radius: 4px; padding: 6px 12px; color: #ddd; }
                QPushButton:hover { background-color: #444; }
                QComboBox { background-color: #2d2d2d; border: 1px solid #555;
                            border-radius: 3px; padding: 3px; color: #ddd; }
                QComboBox QAbstractItemView { background-color: #2d2d2d;
                                              color: #ddd; selection-background-color: #444; }
                QCheckBox { color: #ccc; }
                QScrollArea { background-color: #1e1e1e; border: none; }
                QScrollArea > QWidget > QWidget { background-color: #1e1e1e; }
                QScrollBar:vertical { background: #2d2d2d; width: 10px; border: none; }
                QScrollBar::handle:vertical { background: #555; min-height: 30px; border-radius: 4px; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
                QSlider::groove:horizontal { height: 6px; background: #444; }
                QSlider::handle:horizontal { width: 14px; margin: -4px 0;
                                             background: #888; border-radius: 7px; }
            """)

    # ---- Capture Control ----

    def _start_capture(self):
        """Start the audio capture pipeline."""
        settings = self._settings_panel.get_settings()

        try:
            self._capture_worker = CaptureWorker(self._audio_queue)
            chunk_duration = settings.get("buffer_duration", 1.9)
            self._recognition_worker = RecognitionWorker(
                self._audio_queue, self._text_queue,
                model_size=settings["whisper_model"],
                chunk_duration=chunk_duration
            )
            engine = settings.get("translation_engine", "argos")
            self._current_engine = engine
            self._translation_worker = TranslationWorker(
                self._text_queue, self._subtitle_queue, engine_type=engine
            )

            self._recognition_worker.set_language(settings["source_language"])
            self._translation_worker.set_enabled(settings["translation_enabled"])
            self._translation_worker.set_languages(
                settings["source_language"],
                settings["target_language"],
                settings.get("target_mode", "direct")
            )

            self._capture_worker.start()
            self._recognition_worker.start()
            self._translation_worker.start()

            self._capturing = True
            self._settings_panel.set_capturing(True)
            QTimer.singleShot(500, self._update_device_status)
            QTimer.singleShot(2000, self._check_model_status)
            QTimer.singleShot(1000, self._check_translation_status)

            logger.info("Capture started")

        except Exception as e:
            logger.error("Failed to start capture: %s", e)
            QMessageBox.critical(
                self, "Error",
                f"Failed to start audio capture:\n{e}\n\n"
                "Make sure an audio device is connected and playing audio."
            )

    def _stop_capture(self):
        """Stop the audio capture pipeline."""
        self._capturing = False

        if self._capture_worker:
            self._capture_worker.stop()
        if self._recognition_worker:
            self._recognition_worker.stop()
        if self._translation_worker:
            self._translation_worker.stop()

        self._capture_worker = None
        self._recognition_worker = None
        self._translation_worker = None

        self._clear_queue(self._audio_queue)
        self._clear_queue(self._text_queue)
        self._clear_queue(self._subtitle_queue)

        self._settings_panel.set_capturing(False)
        self._settings_panel.set_device_status("Stopped")
        self._overlay.clear()

        logger.info("Capture stopped")

    def _update_device_status(self):
        """Update device status label after capture thread has started."""
        if self._capture_worker and self._capture_worker.device_name:
            self._settings_panel.set_device_status(self._capture_worker.device_name)
        else:
            self._settings_panel.set_device_status("Default Playback Device")

    def _check_model_status(self):
        """Update model loading status indicator."""
        if self._recognition_worker and self._recognition_worker.is_model_loaded:
            device = self._recognition_worker.device
            model = self._recognition_worker.model_size
            self._settings_panel.set_model_status(f"{model} ({device})")
        else:
            self._settings_panel.set_model_status("Loading...")
            if self._capturing:
                QTimer.singleShot(2000, self._check_model_status)

    def _check_translation_status(self):
        """Update translation engine status indicator."""
        if self._translation_worker:
            self._settings_panel.set_translation_status(
                self._translation_worker.status_detail
            )
            # Keep polling until status stabilizes (not_ready changes to offline)
            if self._translation_worker.status == "not_ready":
                QTimer.singleShot(2000, self._check_translation_status)

    @staticmethod
    def _clear_queue(q: queue.Queue):
        """Clear all items from a queue."""
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass

    # ---- Subtitle Processing ----

    def _process_subtitle_queue(self):
        """Process incoming subtitle data from the translation worker."""
        last_msg = None
        try:
            while True:
                msg = self._subtitle_queue.get_nowait()
                last_msg = msg
        except queue.Empty:
            pass

        if last_msg is not None:
            if last_msg.get("type") == "reset":
                self._overlay.clear()
            else:
                self._overlay.set_subtitles(last_msg["original"], last_msg["translated"])

        if self._translation_worker:
            self._settings_panel.set_translation_status(
                self._translation_worker.status_detail
            )

    # ---- Slots ----

    def _toggle_overlay_mode(self):
        """Toggle drag mode on overlay."""
        if self._overlay:
            self._overlay.toggle_mode()

    def _clear_subtitles(self):
        """Clear overlay subtitles."""
        if self._overlay:
            self._overlay.clear()

    def _on_capture_toggled(self, capturing: bool):
        """Handle start/stop capture button."""
        if capturing:
            self._start_capture()
        else:
            self._stop_capture()

    def _on_overlay_moved(self, x: int, y: int):
        """Save overlay position when moved."""
        self._save_debounce.start(300)

    def _show_about(self):
        """Show about dialog."""
        import os
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt

        dlg = QDialog(self)
        dlg.setWindowTitle("About Lotus Translator")
        dlg.setFixedSize(420, 400)

        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "logo.jpg"
        )
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo = QLabel()
            logo.setPixmap(pix.scaled(360, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo)

        # Text
        text = QLabel(
            "<h3>Lotus Translator v1.0.0</h3>"
            "Real-time speech recognition & translation overlay.<br><br>"
            "Captures system audio via WASAPI Loopback.<br>"
            "Powered by faster-whisper, Argos Translate, and Small100.<br><br>"
            "<i>Credit by Sawashi - Kiet Le</i>"
        )
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setOpenExternalLinks(True)
        layout.addWidget(text)

        layout.addSpacing(10)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dlg.exec()

    # ---- Event Overrides ----

    def closeEvent(self, event):
        """Handle window close."""
        self._save_settings()
        self._stop_capture()
        if self._overlay:
            self._overlay.close()
        event.accept()