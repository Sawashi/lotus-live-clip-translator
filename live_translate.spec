# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Live Translate Overlay.

Builds a single Windows executable with:
- All Python dependencies bundled
- faster-whisper models (tiny/small/medium) included
- small100 ONNX model (skip safetensors/pytorch_model.bin dups)
- Configuration files included
"""

import sys
import os
from pathlib import Path

block_cipher = None

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Collect faster-whisper model files (tiny, small, medium)
# Exclude .cache junk and duplicate small100 formats (keep only ONNX)
model_data = []
if os.path.isdir(MODELS_DIR):
    for root, dirs, files in os.walk(MODELS_DIR):
        # Skip .cache directories
        if ".cache" in root or "__pycache__" in root:
            continue
        # For small100, only bundle ONNX + tokenizer/config, skip safetensors/pytorch_model.bin
        if "small100" in root:
            keep_exts = {".onnx", ".json", ".model", ".py", ".txt", ".gitattributes"}
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in keep_exts:
                    continue
                src = os.path.join(root, f)
                dst = os.path.relpath(root, PROJECT_ROOT)
                model_data.append((src, dst))
        else:
            for f in files:
                src = os.path.join(root, f)
                dst = os.path.relpath(root, PROJECT_ROOT)
                model_data.append((src, dst))

# Collect argos packages if any
argos_data = []
argos_dir = os.path.join(MODELS_DIR, "argos_packages")
if os.path.isdir(argos_dir):
    for root, dirs, files in os.walk(argos_dir):
        for f in files:
            src = os.path.join(root, f)
            dst = os.path.relpath(root, PROJECT_ROOT)
            argos_data.append((src, dst))

a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('languages.json', '.'),
        ('assets', 'assets'),
        (os.path.join(PROJECT_ROOT, 'installer', 'bootstrap_setup.py'), 'installer'),
        (os.path.join(PROJECT_ROOT, 'installer', 'preinstall_check.py'), 'installer'),
    ] + model_data + argos_data,
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
        'transformers',
        'transformers.models.m2m_100',
        'transformers.models.m2m_100.modeling_m2m_100',
        'transformers.generation',
        'sentencepiece',
        'accelerate',
        'accelerate.utils',
        'huggingface_hub',
        'huggingface_hub.snapshot_download',
        'tokenization_small100',
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
        'tensorflow',
        'tensorboard',
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