"""
Python 3.12 Environment Manager for Lotus Translator.

Ensures the app runs under Python 3.12:
1. Detect current Python version
2. Find or download Python 3.12
3. Create/use .venv with Python 3.12
4. Run commands inside that environment
5. Restore original environment on exit

Usage:
    from python_env_manager import ensure_python312_env
    env_info = ensure_python312_env()
    # env_info["python"] = path to python.exe
    # env_info["ok"] = bool
"""

import os
import sys
import json
import subprocess
import logging
import urllib.request
import urllib.error
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# --- Constants ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
VENV_PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")
VENV_ACTIVATE = os.path.join(VENV_DIR, "Scripts", "activate.bat")

PYTHON_312_MINOR = 12
INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs", "Python", "Python312"
)
INSTALL_PYTHON = os.path.join(INSTALL_DIR, "python.exe")

PYTHON_DOWNLOAD_URL = (
    "https://www.python.org/ftp/python/3.12.9/"
    "python-3.12.9-amd64.exe"
)

# Marker written after first successful setup
SETUP_MARKER = os.path.join(VENV_DIR, ".py312_ready")


def get_python_version(python_exe: str = None) -> Optional[str]:
    """Get version string from a python executable."""
    exe = python_exe or sys.executable
    try:
        result = subprocess.run(
            [exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def is_python312(python_exe: str = None) -> bool:
    """Check if given python (or current) is 3.12.x."""
    ver = get_python_version(python_exe)
    if not ver:
        return False
    parts = ver.split(".")
    return len(parts) >= 2 and parts[0] == "3" and parts[1] == str(PYTHON_312_MINOR)


def find_existing_python312() -> Optional[str]:
    """Find an existing Python 3.12 installation on the system."""
    # 1. Check installed location
    if os.path.isfile(INSTALL_PYTHON) and is_python312(INSTALL_PYTHON):
        return INSTALL_PYTHON

    # 2. Try py launcher
    try:
        result = subprocess.run(
            ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.isfile(path) and is_python312(path):
                return path
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 3. Search PATH
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(p, "python.exe")
        if os.path.isfile(candidate) and is_python312(candidate):
            return candidate

    # 4. Check common install paths
    common_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Python", "Python312", "python.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Python", "Python312", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe"),
        os.path.join(os.environ.get("APPDATA", ""), "..", "Local", "Programs", "Python", "Python312", "python.exe"),
    ]
    for p in common_paths:
        p = os.path.normpath(p)
        if os.path.isfile(p) and is_python312(p):
            return p

    return None


def download_python312() -> bool:
    """Download and silently install Python 3.12 to user-local path."""
    logger.info("Downloading Python 3.12.9 from python.org...")
    try:
        # Download to temp
        tmp_dir = tempfile.mkdtemp(prefix="py312_")
        installer_path = os.path.join(tmp_dir, "python-3.12.9-amd64.exe")

        req = urllib.request.Request(
            PYTHON_DOWNLOAD_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=300) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(installer_path, "wb") as f:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        logger.info("  Download progress: %d%%", pct)

        logger.info("Download complete. Running silent installer...")

        # Silent install, user-local, no telemetry
        cmd = [
            installer_path,
            "/quiet",
            "InstallAllUsers=0",
            "PrependPath=0",
            f"TargetDir={INSTALL_DIR}",
            "Include_launcher=0",
            "Include_test=0",
            "Include_doc=0",
            "Include_tcltk=0",
            "Include_symbols=0",
            "SimpleInstall=1",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Cleanup installer
        try:
            os.remove(installer_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass

        if result.returncode == 0:
            logger.info("Python 3.12 installed to %s", INSTALL_DIR)
            return True
        else:
            logger.error("Installer failed (code %d): %s", result.returncode, result.stderr)
            return False

    except urllib.error.URLError as e:
        logger.error("Download failed: %s", e)
        return False
    except subprocess.TimeoutExpired:
        logger.error("Installation timed out (10 min)")
        return False
    except Exception as e:
        logger.error("Installation error: %s", e)
        return False


def ensure_python312_installed() -> Optional[str]:
    """Find or download Python 3.12. Returns path to python.exe or None."""
    existing = find_existing_python312()
    if existing:
        logger.info("Python 3.12 found at: %s", existing)
        return existing

    logger.warning("Python 3.12 not found on system. Downloading...")
    if download_python312():
        if os.path.isfile(INSTALL_PYTHON) and is_python312(INSTALL_PYTHON):
            logger.info("Python 3.12 successfully installed")
            return INSTALL_PYTHON
        else:
            logger.error("Installation completed but python.exe not found")
    else:
        logger.error("Failed to install Python 3.12")

    return None


def ensure_venv(python312_exe: str) -> bool:
    """Create or update .venv using Python 3.12."""
    # Check if already exists and valid
    if os.path.isfile(VENV_PYTHON) and os.path.isfile(SETUP_MARKER):
        if is_python312(VENV_PYTHON):
            logger.info("Valid .venv with Python 3.12 already exists")
            return True
        else:
            logger.warning(".venv exists but not Python 3.12 — recreating")
            remove_venv()

    # Create venv
    logger.info("Creating .venv with Python 3.12...")
    try:
        result = subprocess.run(
            [python312_exe, "-m", "venv", VENV_DIR],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.error("venv creation failed: %s", result.stderr)
            return False

        # Verify
        if not os.path.isfile(VENV_PYTHON):
            logger.error("venv python.exe not found after creation")
            return False

        # Upgrade pip
        logger.info("Upgrading pip in venv...")
        subprocess.run(
            [VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True, text=True, timeout=120
        )

        # Write marker
        with open(SETUP_MARKER, "w") as f:
            f.write("ready")

        logger.info("Python 3.12 venv ready at: %s", VENV_DIR)
        return True

    except subprocess.TimeoutExpired:
        logger.error("venv creation timed out")
        return False
    except Exception as e:
        logger.error("venv creation error: %s", e)
        return False


def remove_venv():
    """Remove .venv directory (force permissions on Windows)."""
    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if os.path.isdir(VENV_DIR):
        try:
            shutil.rmtree(VENV_DIR, onerror=on_rm_error)
        except Exception as e:
            logger.warning("Could not fully remove venv: %s", e)


def ensure_python312_env() -> Dict[str, Any]:
    """
    Main entry point. Ensures Python 3.12 environment exists.
    Returns dict with:
        ok: bool — whether environment is ready
        python: str — path to python.exe to use
        pip: str — path to pip.exe
        created: bool — whether env was just created
        error: str — error message if failed
    """
    result = {
        "ok": False,
        "python": None,
        "pip": None,
        "created": False,
        "error": None,
    }

    # If already running Python 3.12, use current
    if is_python312():
        logger.info("Already running Python 3.12 (sys.executable=%s)", sys.executable)
        result["ok"] = True
        result["python"] = sys.executable
        # pip might not be in same dir - fallback to -m pip
        pip_exe = os.path.join(os.path.dirname(sys.executable), "pip.exe")
        if os.path.isfile(pip_exe):
            result["pip"] = pip_exe
        else:
            pip_exe = os.path.join(os.path.dirname(sys.executable), "Scripts", "pip.exe")
            result["pip"] = pip_exe if os.path.isfile(pip_exe) else None
        result["created"] = False
        return result

    # Find or install Python 3.12
    py312 = ensure_python312_installed()
    if not py312:
        result["error"] = "Could not find or install Python 3.12"
        return result

    # Create/verify venv
    if not ensure_venv(py312):
        result["error"] = "Failed to create Python 3.12 virtual environment"
        return result

    result["ok"] = True
    result["python"] = VENV_PYTHON
    result["pip"] = VENV_PIP if os.path.isfile(VENV_PIP) else None
    result["created"] = True
    return result


def run_in_env(command: List[str], cwd: str = None, env_info: Dict[str, Any] = None) -> int:
    """
    Run a command inside the Python 3.12 environment.
    If env_info is provided, skips the environment check.
    Returns exit code.
    """
    if env_info is None:
        env_info = ensure_python312_env()
    if not env_info["ok"]:
        logger.error("Cannot run command: %s", env_info.get("error", "unknown"))
        print(f"ERROR: {env_info.get('error', 'unknown')}", file=sys.stderr)
        return 1

    python_exe = env_info["python"]

    # Build env — on Windows, modify env vars directly like activate.bat
    env = os.environ.copy()

    # Set VIRTUAL_ENV so pip etc. know we're in a venv
    venv_root = os.path.dirname(os.path.dirname(python_exe))
    env["VIRTUAL_ENV"] = venv_root

    # Prepend venv Scripts to PATH
    scripts_dir = os.path.dirname(python_exe)
    env["PATH"] = scripts_dir + os.pathsep + env.get("PATH", "")

    # Remove PYTHONHOME if set (venv breaks with it)
    env.pop("PYTHONHOME", None)

    logger.info("Running in Python 3.12 env: %s", " ".join(command))
    try:
        proc = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            env=env,
            shell=False,
        )
        return proc.returncode
    except Exception as e:
        logger.error("Command execution error: %s", e)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    info = ensure_python312_env()
    if info["ok"]:
        print(f"Python 3.12 environment ready: {info['python']}")
    else:
        print(f"FAILED: {info['error']}")
        sys.exit(1)