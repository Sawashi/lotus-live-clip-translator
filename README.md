# Live Translate Overlay

Real-time audio capture → speech recognition → translation → floating subtitle overlay for Windows.

## Quick Start (Users)

1. Download `LiveTranslateOverlay_Setup_v1.0.0_Part1.exe` (and any `.bin` parts)
2. Run the `.exe` — installer extracts everything
3. Launch from Start Menu / Desktop shortcut
4. First launch runs environment check (logs to `%LOCALAPPDATA%\LiveTranslateOverlay\logs\`)
5. Start speaking — subtitles appear as floating overlay

**Requirements:**
- Windows 10 or later
- NVIDIA GPU with CUDA 12.4 recommended (CPU fallback works but slower)
- 8 GB RAM minimum, 16 GB recommended
- 10 GB free disk space (for bundled models)

## Build from Source (Developers)

### Prerequisites

1. **Python 3.12** (auto-managed via `run_with_py312.py` — download/install if missing)
2. **Inno Setup 6+** — https://jrsoftware.org/isdl.php (add `iscc.exe` to PATH)
3. **Visual C++ Redistributable** — https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Download and save to `installer\vc_redist.x64.exe`

### Setup Build Environment

The project auto-manages a Python 3.12 virtual environment. Use `run_with_py312.py` (or the `python312.bat` shortcut) for all pip commands:

```batch
# Install Python dependencies (auto-creates .venv with Python 3.12)
python run_with_py312.py pip install -r requirements.txt

# Or using the batch shortcut
python312.bat pip install -r requirements.txt

# Install PyTorch with CUDA 12.4
python run_with_py312.py pip install torch==2.6.0+cu124 torchaudio==2.6.0+cu124 --index-url https://download.pytorch.org/whl/cu124
```

> **Note:** If Python 3.12 is not installed, it's automatically downloaded and installed silently to `%LOCALAPPDATA%\Programs\Python\Python312`. No manual Python installation required.

### Running the App

```batch
# Auto-ensures Python 3.12 .venv, then launches
python run_with_py312.py main.py

# Or simply (auto-relaunches if wrong Python version):
python main.py
```

### Pre-Build Check

```batch
python installer\preinstall_check.py
```

This verifies:
- Python version
- All pip packages installed
- Inno Setup compiler available
- NVIDIA GPU + CUDA
- All model files present

### Build Installer

```batch
installer\build_installer.bat
```

This will:
1. Clean previous build artifacts
2. Run PyInstaller → `dist\LiveTranslateOverlay\LiveTranslateOverlay.exe`
3. Run Inno Setup → `dist\LiveTranslateOverlay_Setup_v1.0.0_Part1.exe` (+ parts if >2GB)

### Output

| File | Description |
|------|-------------|
| `dist\LiveTranslateOverlay_Setup_v1.0.0_Part1.exe` | Installer (part 1 of N) |
| `dist\LiveTranslateOverlay_Setup_v1.0.0_Part2.bin` | Installer part 2 (if needed) |
| `dist\build_log.txt` | Build log |

## First-Run Bootstrap

On first launch, the app runs `installer/bootstrap_setup.py` which:
1. Checks for NVIDIA GPU + CUDA 12.4
2. Verifies all Python packages are installed
3. Checks CUDA runtime DLLs
4. Verifies model files exist
5. Checks Argos translation packages
6. Writes status to `%LOCALAPPDATA%\LiveTranslateOverlay\logs\bootstrap_*.log`

If CUDA is missing, a notice is shown. Run `installer\cuda_setup.bat` as Administrator to install.

## Logs

| Log | Location |
|-----|----------|
| Installer log | `%LOCALAPPDATA%\LiveTranslateOverlay\logs\install.log` |
| Bootstrap log | `%LOCALAPPDATA%\LiveTranslateOverlay\logs\bootstrap_*.log` |
| App runtime log | `%APPDATA%\LotusTranslator\logs\lotus_translator.log` |
| Build log | `dist\build_log.txt` |

## Architecture

```
live_subtitle/
├── main.py                    # Entry point + bootstrap
├── audio/wasapi_capture.py    # WASAPI loopback audio capture
├── speech/whisper_engine.py   # faster-whisper speech recognition
├── translation/
│   ├── argos_engine.py        # Argos offline translation
│   └── small100_engine.py     # Small100 (M2M-100) translation
├── overlay/subtitle_overlay.py # Floating subtitle window
├── ui/                        # Qt6 UI panels
├── installer/
│   ├── setup.iss              # Inno Setup script
│   ├── build_installer.bat    # One-click build
│   ├── bootstrap_setup.py     # First-run env checker
│   ├── preinstall_check.py    # Pre-build validation
│   └── cuda_setup.bat         # CUDA install helper
├── models/                    # Bundled model files
│   ├── models--Systran--faster-whisper-{tiny,small,medium}/
│   └── small100/
└── config.json                # Default configuration
```

## Troubleshooting

**App won't start:**
- Check `%APPDATA%\LotusTranslator\logs\lotus_translator.log`
- Check `%LOCALAPPDATA%\LiveTranslateOverlay\logs\bootstrap_*.log`

**No GPU detected:**
- Run `installer\cuda_setup.bat` as Administrator
- Ensure NVIDIA driver ≥ 551.61 installed

**Installation fails:**
- Check `%LOCALAPPDATA%\LiveTranslateOverlay\logs\install.log`
- Ensure VC++ Redist is installed
- Run installer as Administrator

# 1. Verify env
python installer\preinstall_check.py

# 2. Build installer
installer\build_installer.bat
