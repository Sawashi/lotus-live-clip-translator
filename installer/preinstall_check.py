"""
Pre-installation environment checker.
Run BEFORE building the installer to ensure all prerequisites are met.

Usage:
    python installer/preinstall_check.py
"""

import os
import sys
import subprocess
import importlib.util
import shutil

REQUIRED_PACKAGES = {
    "PyQt6": "6.7.0",
    "soundcard": "0.4.1",
    "faster-whisper": "1.0.2",
    "onnxruntime": "1.18.1",
    "argostranslate": "1.11.0",
    "requests": "2.31.0",
    "PyInstaller": "6.5.0",
    "transformers": "4.44.2",
    "sentencepiece": "0.2.0",
    "accelerate": "1.13.0",
    "huggingface-hub": "0.26.0",
    "torch": "2.6.0",
    "torchaudio": "2.6.0",
    "ctranslate2": "4.4.0",
}

REQUIRED_TOOLS = {
    "iscc": "Inno Setup Compiler (iscc.exe)",
    "git": "Git -- optional",
}

# Model directories (check if dir exists, since model.bin is nested in snapshots/)
EXPECTED_MODELS = [
    "models/models--Systran--faster-whisper-medium",
    "models/models--Systran--faster-whisper-small",
    "models/models--Systran--faster-whisper-tiny",
    "models/small100/model.onnx",
]


def check_python_version():
    ver = sys.version_info
    ok = ver.major >= 3 and ver.minor >= 10
    print(f"  [+] Python {ver.major}.{ver.minor}.{ver.micro}" if ok else f"  [!] Python {ver.major}.{ver.minor}.{ver.micro} (need 3.10+)")
    return ok


def check_packages():
    ok = True
    for pkg, ver in sorted(REQUIRED_PACKAGES.items()):
        try:
            spec = importlib.util.find_spec(pkg.replace("-", "_"))
            if spec is None:
                print(f"  [!] {pkg} -- NOT INSTALLED")
                ok = False
                continue
            try:
                mod = __import__(pkg.replace("-", "_"))
                actual = getattr(mod, "__version__", "?")
                match = actual.startswith(ver[:3]) if actual != "?" else False
                status = "[+]" if match else f"[~]"
                print(f"  {status} {pkg}=={actual}")
            except Exception:
                print(f"  [+] {pkg} (version unknown)")
        except Exception as e:
            print(f"  [!] {pkg} -- {e}")
            ok = False
    return ok


def check_tools():
    ok = True
    for tool, desc in REQUIRED_TOOLS.items():
        path = shutil.which(tool)
        if path:
            print(f"  [+] {tool} found at: {path}")
        else:
            print(f"  [~] {tool} -- {desc}")
    return ok


def check_models():
    ok = True
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for model_path in EXPECTED_MODELS:
        full = os.path.join(root, model_path)
        if os.path.exists(full):
            if os.path.isdir(full):
                total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(full) for f in fn)
                print(f"  [+] {model_path}/ ({total // (1024*1024)} MB)")
            else:
                size = os.path.getsize(full) // (1024 * 1024)
                print(f"  [+] {model_path} ({size} MB)")
        else:
            print(f"  [!] {model_path} -- MISSING")
            ok = False
    return ok


def check_cuda():
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "NVIDIA-SMI" in line:
                    print(f"  [+] NVIDIA driver: {line.strip()}")
                    return True
        print("  [~] nvidia-smi failed -- no GPU?")
        return False
    except FileNotFoundError:
        print("  [~] nvidia-smi not found -- no GPU?")
        return False


def main():
    # Fix console encoding for Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("PRE-INSTALL ENVIRONMENT CHECK")
    print("=" * 60)
    all_ok = True

    print("\n1. Python version:")
    all_ok &= check_python_version()

    print("\n2. Required packages:")
    all_ok &= check_packages()

    print("\n3. Build tools:")
    check_tools()  # Non-fatal

    print("\n4. CUDA/GPU:")
    check_cuda()  # Non-critical

    print("\n5. Model files:")
    all_ok &= check_models()

    print("\n" + "=" * 60)
    if all_ok:
        print("All checks passed! Ready to build.")
        print("   Run: installer\\build_installer.bat")
    else:
        print("Some checks FAILED. Fix issues above before building.")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())