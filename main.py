"""Live Translate Overlay - Main entry point.

A Windows desktop application that captures system audio, performs
real-time speech recognition, translates text, and displays subtitles
as a floating overlay.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def setup_logging():
    """Configure rotating file logger in AppData."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(appdata, "LiveTranslateOverlay", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "live_translate.log")

    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Also log to console for development
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root_logger.addHandler(console)

    return logging.getLogger(__name__)


def main():
    """Application entry point."""
    logger = setup_logging()
    logger.info("=== Live Translate Overlay starting ===")

    app = QApplication(sys.argv)
    app.setApplicationName("Live Translate Overlay")
    app.setOrganizationName("LiveTranslateOverlay")

    # Enable high DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.show()

    logger.info("Application started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()