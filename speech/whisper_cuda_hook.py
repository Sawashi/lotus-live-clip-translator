"""
Runtime hook for PyInstaller frozen builds.
Ensures CUDA DLLs are findable at runtime when ctranslate2
initializes its CUDA backend.
"""
import os
import sys

if getattr(sys, 'frozen', False):
    # In frozen builds, nvidia CUDA DLLs are extracted to sys._MEIPASS
    base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    # Add all subdirectories to PATH so ctranslate2 can find CUDA DLLs
    for root, dirs, files in os.walk(base):
        if root == base:
            continue
        for f in files:
            if f.endswith(".dll"):
                os.environ.setdefault("PATH", "")
                if root not in os.environ["PATH"]:
                    os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]
                break