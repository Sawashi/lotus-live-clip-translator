# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Live Translate Overlay.

Builds a single Windows executable with:
- All Python dependencies bundled
- faster-whisper small model included
- Languages config included
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Collect faster-whisper model files
# The small model is ~500MB, bundled in installer
# For development, we download on first run
model_data = []
if os.path.isdir(MODELS_DIR):
    for root, dirs, files in os.walk(MODELS_DIR):
        for f in files:
            src = os.path.join(root, f)
            dst = os.path.relpath(root, PROJECT_ROOT)
            model_data.append((src, dst))

a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('languages.json', '.'),
    ] + model_data,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'soundcard',
        'soundcard._implementation',
        'faster_whisper',
        'faster_whisper.transcribe',
        'argostranslate',
        'argostranslate.package',
        'argostranslate.translate',
        'ctypes',
        'ctypes.wintypes',
        'queue',
        'threading',
        'logging',
        'json',
        'os',
        'sys',
        'time',
        'struct',
        'comtypes',
        'numpy',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'torchvision',
        'torchaudio',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LiveTranslateOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'assets', 'icon.ico') if os.path.exists(os.path.join(PROJECT_ROOT, 'assets', 'icon.ico')) else None,
)