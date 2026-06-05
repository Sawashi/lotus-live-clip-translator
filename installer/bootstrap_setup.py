"""
Live Translate Overlay — First-run Bootstrap

Runs on first application launch after installation:
1. Checks environment (Python, CUDA, GPU, dependencies)
2. Installs missing dependencies (CUDA runtime, Python packages)
3. Downloads additional models if needed
4. Logs everything to %LOCALAPPDATA%\LiveTranslateOverlay\logs\

Usage:
    python bootstrap_setup.py
    (Or auto-called from main.py on first-run detection)
"""

import os
import sys
import json
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import importlib.util

# --- Configuration ---
APP_NAME = "LiveTranslateOverlay"
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "logs")
BOOTSTRAP_LOG = os.path.join(LOG_DIR, f"bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

REQUIRED_PACKAGES = {
    "torch": "2.6.0",
    "torchaudio": "2.6.0",
    "faster-whisper": "1.0.2",
    "ctranslate2": "4.4.0",
    "argostranslate": "1.11.0",
    "transformers": "4.44.2",
    "onnxruntime": "1.18.1",
    "sentencepiece": "0.2.0",
    "accelerate": "1.13.0",
}

# Minimum CUDA driver version
MIN_CUDA_MAJOR = 12
MIN_CUDA_MINOR = 4

# Expected nvidia DLLs
NVIDIA_DLLS = [
    "nvidia-cublas-cu12",
    "nvidia-cuda-nvrtc-cu12",
    "nvidia-cudnn-cu12",
]


def setup_logger():
    """Configure bootstrap logger."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("bootstrap")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = RotatingFileHandler(BOOTSTRAP_LOG, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger


logger = setup_logger()


def log_system_info():
    """Log basic system information."""
    logger.info("=== Bootstrap Environment Check ===")
    logger.info("Python: %s", sys.version)
    logger.info("Platform: %s", sys.platform)
    logger.info("OS: %s", os.name)
    logger.info("App path: %s", os.path.dirname(os.path.abspath(__file__)))
    logger.info("Log file: %s", BOOTSTRAP_LOG)

    # Check if running from PyInstaller bundle
    if getattr(sys, 'frozen', False):
        logger.info("Running from: PyInstaller bundle (%s)", sys.executable)
    else:
        logger.info("Running from: Python interpreter (%s)", sys.executable)


def check_cuda_gpu():
    """
    Check for NVIDIA GPU with CUDA support.
    Returns dict with gpu info or error.
    """
    result = {
        "gpu_found": False,
        "cuda_version": None,
        "driver_version": None,
        "gpu_name": None,
        "cuda_available": False,
        "error": None,
    }

    # 1. Check nvidia-smi
    try:
        nvidia_smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30
        )
        if nvidia_smi.returncode == 0 and nvidia_smi.stdout.strip():
            parts = nvidia_smi.stdout.strip().split(", ")
            result["gpu_name"] = parts[0] if len(parts) > 0 else "Unknown"
            result["driver_version"] = parts[1] if len(parts) > 1 else None
            result["gpu_found"] = True
            logger.info("GPU detected: %s (Driver: %s)", result["gpu_name"], result["driver_version"])
        else:
            logger.warning("nvidia-smi returned no output")
    except FileNotFoundError:
        logger.warning("nvidia-smi not found — no NVIDIA driver?")
        result["error"] = "nvidia-smi not found"
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
        result["error"] = "nvidia-smi timeout"
    except Exception as e:
        logger.warning("nvidia-smi error: %s", e)
        result["error"] = str(e)

    # 2. Check CUDA version via nvidia-smi
    try:
        cuda_ver = subprocess.run(
            ["nvidia-smi", "--query", "--display=STATS"],
            capture_output=True, text=True, timeout=30
        )
        # Alternative: check nvcc
        nvcc = subprocess.run(
            ["nvcc", "--version"], capture_output=True, text=True, timeout=15
        )
        if nvcc.returncode == 0:
            for line in nvcc.stdout.splitlines():
                if "release" in line:
                    import re
                    m = re.search(r"release (\d+)\.(\d+)", line)
                    if m:
                        result["cuda_version"] = f"{m.group(1)}.{m.group(2)}"
                        result["cuda_available"] = True
                        logger.info("CUDA toolkit version: %s", result["cuda_version"])
                        break
        else:
            logger.info("nvcc not found (CUDA toolkit not installed, may use runtime-only)")
    except FileNotFoundError:
        logger.info("nvcc not found — using GPU via driver-only mode")
    except Exception as e:
        logger.warning("CUDA version check error: %s", e)

    # 3. Try torch CUDA check
    try:
        import torch
        if torch.cuda.is_available():
            result["cuda_available"] = True
            if not result["cuda_version"]:
                result["cuda_version"] = f"{torch.version.cuda}"
            logger.info("PyTorch CUDA available: %s", torch.cuda.get_device_name(0))
        else:
            logger.warning("PyTorch reports CUDA not available")
    except ImportError:
        logger.warning("PyTorch not installed yet — cannot check CUDA")
    except Exception as e:
        logger.warning("PyTorch CUDA check error: %s", e)

    return result


def verify_python_packages():
    """
    Check installed Python packages against required versions.
    Returns dict with status.
    """
    result = {"all_installed": True, "missing": [], "wrong_version": [], "installed": {}}

    for pkg_name, expected_ver in REQUIRED_PACKAGES.items():
        try:
            spec = importlib.util.find_spec(pkg_name.replace("-", "_"))
            if spec is None:
                result["all_installed"] = False
                result["missing"].append(pkg_name)
                logger.warning("Package MISSING: %s", pkg_name)
                continue

            # Try to get version
            try:
                mod = importlib.import_module(pkg_name.replace("-", "_"))
                ver = getattr(mod, "__version__", "unknown")
            except ImportError:
                ver = "import_error"

            result["installed"][pkg_name] = ver
            logger.info("Package %s: installed=%s (expected=%s)", pkg_name, ver, expected_ver)
        except Exception as e:
            result["all_installed"] = False
            result["missing"].append(pkg_name)
            logger.warning("Package check error for %s: %s", pkg_name, e)

    return result


def install_missing_packages(missing_packages):
    """Install missing Python packages via pip."""
    if not missing_packages:
        logger.info("No missing packages to install")
        return True

    logger.info("Installing missing packages: %s", missing_packages)
    try:
        # Build install command
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
        for pkg in missing_packages:
            ver = REQUIRED_PACKAGES.get(pkg)
            if pkg == "torch":
                cmd.append(f"{pkg}=={ver}+cu124")
            elif pkg == "torchaudio":
                cmd.append(f"{pkg}=={ver}+cu124")
            else:
                cmd.append(f"{pkg}=={ver}")

        # Add PyTorch index URL if torch in list
        if "torch" in missing_packages:
            cmd.extend(["--index-url", "https://download.pytorch.org/whl/cu124"])

        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            logger.info("Package installation successful")
            return True
        else:
            logger.error("Package installation failed:\n%s", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.error("Package installation timed out (10 min)")
        return False
    except Exception as e:
        logger.error("Package installation error: %s", e)
        return False


def check_cuda_runtime_dlls():
    """Check if NVIDIA CUDA runtime DLLs are accessible."""
    result = {"all_found": True, "missing": []}
    for dll in NVIDIA_DLLS:
        try:
            # Try importing the package (should be installed via pip)
            spec = importlib.util.find_spec(dll.replace("-", "_"))
            if spec:
                logger.info("CUDA runtime %s: FOUND", dll)
            else:
                logger.warning("CUDA runtime %s: MISSING", dll)
                result["all_found"] = False
                result["missing"].append(dll)
        except Exception:
            result["all_found"] = False
            result["missing"].append(dll)
    return result


def check_models():
    """Check if model files exist."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(app_dir, "models")
    result = {"all_found": True, "missing": []}

    expected_models = [
        ("faster-whisper-medium", os.path.join(models_dir, "models--Systran--faster-whisper-medium")),
        ("faster-whisper-small", os.path.join(models_dir, "models--Systran--faster-whisper-small")),
        ("faster-whisper-tiny", os.path.join(models_dir, "models--Systran--faster-whisper-tiny")),
        ("small100", os.path.join(models_dir, "small100")),
    ]

    for name, path in expected_models:
        if os.path.isdir(path):
            files = os.listdir(path)
            logger.info("Model %s: FOUND (%d items)", name, len(files))
        else:
            logger.warning("Model %s: MISSING at %s", name, path)
            result["all_found"] = False
            result["missing"].append(name)

    return result


def check_argos_packages():
    """Check if Argos translation packages are available."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    argos_dir = os.path.join(app_dir, "models", "argos_packages")
    result = {"found": False, "package_count": 0}

    if os.path.isdir(argos_dir):
        packages = [f for f in os.listdir(argos_dir) if f.endswith(".argospackage")]
        result["package_count"] = len(packages)
        result["found"] = len(packages) > 0
        logger.info("Argos packages: %d found", len(packages))
    else:
        logger.info("Argos packages directory not found")

    return result


def run_bootstrap():
    """Main bootstrap routine."""
    logger.info("=" * 60)
    logger.info("BOOTSTRAP STARTED")
    logger.info("=" * 60)

    log_system_info()

    # Step 1: Check CUDA/GPU
    logger.info("\n--- Step 1: GPU / CUDA Check ---")
    gpu_info = check_cuda_gpu()
    if gpu_info["gpu_found"]:
        logger.info("✅ GPU detected: %s", gpu_info["gpu_name"])
        if gpu_info["cuda_available"]:
            logger.info("✅ CUDA %s available", gpu_info["cuda_version"])
        else:
            logger.warning("⚠️  GPU found but CUDA not fully available — running CPU fallback")
    else:
        logger.warning("⚠️  No GPU detected. App will run on CPU (slower)")
        logger.warning("   If you have an NVIDIA GPU, install CUDA 12.4:")
        logger.warning("   Run: installer\\cuda_setup.bat")

    # Step 2: Check Python packages
    logger.info("\n--- Step 2: Python Package Check ---")
    pkg_result = verify_python_packages()
    if pkg_result["all_installed"]:
        logger.info("✅ All required packages are installed")
    else:
        if pkg_result["missing"]:
            logger.warning("⚠️  Missing packages: %s", pkg_result["missing"])
            logger.info("→ Attempting auto-install...")
            success = install_missing_packages(pkg_result["missing"])
            if success:
                logger.info("✅ Missing packages installed successfully")
            else:
                logger.error("❌ Failed to install missing packages")
                logger.error("   Try manually: pip install -r requirements.txt")

    # Step 3: Check CUDA runtime DLLs
    logger.info("\n--- Step 3: CUDA Runtime DLLs ---")
    dll_result = check_cuda_runtime_dlls()
    if dll_result["all_found"]:
        logger.info("✅ CUDA runtime DLLs OK")
    else:
        logger.warning("⚠️  Missing CUDA DLLs: %s", dll_result["missing"])
        logger.info("→ Run: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-nvrtc-cu12")

    # Step 4: Check models
    logger.info("\n--- Step 4: Model Files ---")
    model_result = check_models()
    if model_result["all_found"]:
        logger.info("✅ All models present")
    else:
        logger.warning("⚠️  Missing models: %s", model_result["missing"])

    # Step 5: Check Argos packages
    logger.info("\n--- Step 5: Argos Translation Packages ---")
    argos_result = check_argos_packages()
    if argos_result["found"]:
        logger.info("✅ Argos packages: %d", argos_result["package_count"])
    else:
        logger.info("ℹ️  No Argos packages bundled — will download on-demand")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BOOTSTRAP COMPLETE")
    logger.info("Log saved to: %s", BOOTSTRAP_LOG)

    # Determine overall status
    has_gpu = gpu_info["gpu_found"]
    has_cuda = gpu_info["cuda_available"]
    all_pkgs = pkg_result["all_installed"]
    all_models = model_result["all_found"]

    status = {
        "gpu": has_gpu,
        "cuda": has_cuda,
        "packages_ok": all_pkgs,
        "models_ok": all_models,
        "gpu_name": gpu_info.get("gpu_name"),
        "cuda_version": gpu_info.get("cuda_version"),
        "log_file": BOOTSTRAP_LOG,
        "missing_models": model_result["missing"],
        "missing_packages": pkg_result["missing"],
    }

    # Write a status JSON for main.py to read
    status_path = os.path.join(LOG_DIR, "bootstrap_status.json")
    try:
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
        logger.info("Status written to: %s", status_path)
    except Exception as e:
        logger.warning("Failed to write status: %s", e)

    return status


if __name__ == "__main__":
    status = run_bootstrap()
    if not status["packages_ok"] or not status["models_ok"]:
        print("\n⚠️  Some checks failed. See log for details.")
        print(f"   Log: {BOOTSTRAP_LOG}")
    else:
        print("\n✅ Environment is ready!")