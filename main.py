"""Lotus Translator - Main entry point.

A Windows desktop application that captures system audio, performs
real-time speech recognition, translates text, and displays subtitles
as a floating overlay.
"""

import os
import sys

# Point to cuDNN 9 DLLs
def _add_cudnn_path():
    import site
    search_patterns = [
        os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "nvidia", "cudnn", "bin"),
        os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "cudnn", "bin"),
    ]
    for sp in site.getsitepackages():
        search_patterns.append(os.path.join(sp, "nvidia", "cudnn", "bin"))

    for path in search_patterns:
        if os.path.isdir(path) and any("cudnn" in f for f in os.listdir(path)):
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            return True
    return False

_add_cudnn_path()

import io
import logging
from logging.handlers import RotatingFileHandler

# Redirect stdout to suppress argostranslate print() spam BEFORE any imports
_original_stdout = sys.stdout
sys.stdout = io.StringIO()

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from settings.settings_manager import SettingsManager


def setup_logging():
    """Configure rotating file logger in AppData."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(appdata, "LotusTranslator", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "lotus_translator.log")

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

    # Suppress verbose third-party loggers
    for logger_name in [
        "argostranslate",
        "argostranslate.utils",
        "stanza",
        "sentence_splitter",
        "sacremoses",
        "tokenizers",
        "transformers",
        "httpx",
        "httpcore",
        "urllib3",
        "faster_whisper",
        "ctranslate2",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Console handler
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                super().emit(record)
            except UnicodeEncodeError:
                msg = self.format(record)
                safe = msg.encode('ascii', errors='replace').decode('ascii')
                try:
                    _original_stdout.write(safe + '\n')
                    _original_stdout.flush()
                except Exception:
                    pass

    console = SafeStreamHandler(_original_stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root_logger.addHandler(console)

    return logging.getLogger(__name__)


def main():
    """Application entry point."""
    logger = setup_logging()
    logger.info("=== Lotus Translator starting ===")

    # Create QApp early so QMessageBox works
    app = QApplication(sys.argv)
    app.setApplicationName("Lotus Translator")
    app.setOrganizationName("LotusTranslator")

    # Check expiry before launching main UI
    settings_mgr = SettingsManager()
    if not settings_mgr.check_expiry():
        expiry = settings_mgr.get("expiry_date", "unknown")
        QMessageBox.critical(
            None, "Lotus Translator - Expired",
            f"This application has expired ({expiry}).\n\n"
            "Please contact the developer for a new version."
        )
        sys.exit(1)

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