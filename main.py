"""Lotus Translator - Main entry point.

A Windows desktop application that captures system audio, performs
real-time speech recognition, translates text, and displays subtitles
as a floating overlay.
"""

import os
import sys
import io
import logging
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler

# --- Python 3.12 Check ---
# If not running Python 3.12, auto-launch via run_with_py312.py
if sys.version_info.major != 3 or sys.version_info.minor != 12:
    script = os.path.abspath(__file__)
    launcher = os.path.join(os.path.dirname(script), "run_with_py312.py")
    if os.path.isfile(launcher):
        print(f"Python {sys.version_info.major}.{sys.version_info.minor} detected — relaunching with Python 3.12...")
        import subprocess
        cmd = [sys.executable, launcher, script] + sys.argv[1:]
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    else:
        print(f"WARNING: Python {sys.version_info.major}.{sys.version_info.minor} — expected 3.12")
        print(f"  Run: python run_with_py312.py {os.path.basename(script)}")
        # Continue anyway, but log warning

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

# Redirect stdout to suppress argostranslate print() spam BEFORE any imports
_original_stdout = sys.stdout
sys.stdout = io.StringIO()

# Import onnxruntime BEFORE PyQt6 to avoid DLL conflict with Qt native libs
import onnxruntime  # noqa: E402, F401

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from settings.settings_manager import SettingsManager

# Bootstrap marker path
BOOTSTRAP_MARKER = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "LiveTranslateOverlay",
    ".bootstrap_needed"
)


def run_bootstrap(logger):
    """Run first-time environment bootstrap if needed."""
    marker = Path(BOOTSTRAP_MARKER)
    if not marker.exists():
        logger.info("Bootstrap marker not found — checking previous status")
        status_file = marker.parent / "logs" / "bootstrap_status.json"
        if status_file.exists():
            logger.info("Bootstrap previously completed (status file exists)")
            return True

    logger.info("Running first-time environment bootstrap...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from installer.bootstrap_setup import run_bootstrap
        status = run_bootstrap()
        if status.get("packages_ok", False):
            logger.info("Bootstrap completed successfully")
        else:
            logger.warning("Bootstrap completed with warnings — see log")

        if marker.exists():
            marker.unlink()
        return True
    except Exception as e:
        logger.error("Bootstrap error: %s", e)
        return False


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

    # Run first-time bootstrap
    run_bootstrap(logger)

    # Create QApp early so QMessageBox works
    app = QApplication(sys.argv)
    app.setApplicationName("Lotus Translator")
    app.setOrganizationName("LotusTranslator")

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