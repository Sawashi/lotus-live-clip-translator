# Live Translate Overlay

A Windows desktop application that captures system audio, performs real-time speech recognition, translates text, and displays subtitles as a floating overlay on top of any application.

Works with YouTube, Netflix, VLC, MP4 files, Bilibili, Twitch, browser audio, desktop applications, and games running in windowed or borderless mode.

**No phone, browser extension, virtual audio cable, OBS, or external device required.**

## Features

- **System Audio Capture** - Captures audio from Windows playback via WASAPI Loopback
- **Real-Time Speech Recognition** - Powered by faster-whisper with models from tiny to medium
- **Offline Translation** - Argos Translate works without internet
- **Online Translation** - LibreTranslate public API for better quality (optional)
- **Floating Subtitle Overlay** - Always-on-top, frameless, transparent, click-through mode
- **Bilingual Display** - Show original + translated text simultaneously
- **Customizable** - Font size, color, opacity, line spacing, themes
- **Lightweight** - Under 1 GB RAM, under 15% CPU on mid-range hardware

## Requirements

- Windows 10 or 11 (64-bit)
- 4 GB RAM minimum, 8 GB recommended
- 2 GB free disk space
- No GPU required (CUDA auto-detected)

## Quick Start

### From Source (Development)

1. Install Python 3.11 or later from [python.org](https://python.org)

2. Clone or extract the project:

```bash
cd live_translate_overlay
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python main.py
```

5. Click **Start Capture** in the UI.
6. Play any audio/video on your computer.
7. Subtitles appear on the floating overlay.

### Building the Installer

1. Install PyInstaller:

```bash
pip install pyinstaller
```

2. Build the executable:

```bash
pyinstaller live_translate.spec
```

3. Download and install [Inno Setup](https://jrsoftware.org/isinfo.php).
4. Open `installer/setup.iss` and compile (or run from command line):

```bash
iscc installer/setup.iss
```

5. The installer is created in the `dist/` folder.

## Usage

### Main Window

| Control | Description |
|---------|-------------|
| **Start/Stop Capture** | Begin or end audio capture |
| **Source Language** | Select input language (Auto Detect available) |
| **Translation Toggle** | Enable or disable translation |
| **Translation Mode** | Offline (Argos) or Online (LibreTranslate) |
| **Target Language** | Select output language |
| **Display Mode** | Original, Translated, or Bilingual |
| **Font Size** | Slider from 12px to 72px |
| **Opacity** | Overlay background opacity |
| **Line Spacing** | Adjust subtitle line spacing |
| **Text Color** | Pick any color |
| **Whisper Model** | tiny (fastest) / small (balanced) / medium (accurate) |
| **Theme** | Light or Dark |

### Overlay

- **Double-click** to toggle between Drag Mode and Click-Through Mode
- **Drag Mode**: Visible border, clickable, resizable
- **Click-Through Mode**: Transparent to mouse, clicks pass through to underlying windows

### Supported Languages

Auto Detect, English, Japanese, Chinese, Korean, Vietnamese, Spanish, French, German.

Language configuration is data-driven via `languages.json` — add more without code changes.

### Translation Pairs (Minimum)

Japanese ↔ English, Chinese ↔ English, Korean ↔ English, Vietnamese ↔ English, Spanish ↔ English, French ↔ English, German ↔ English.

## Architecture

```
Audio (WASAPI Loopback)
  → Audio Queue (thread-safe)
    → faster-whisper (speech recognition thread)
      → Text Queue (thread-safe)
        → Translation Engine (translation thread)
          → Subtitle Queue (thread-safe)
            → Overlay UI (main thread, 100ms polling)
```

All components run in separate worker threads to keep the UI responsive.

## Project Structure

```
live_translate_overlay/
├── main.py                      # Entry point
├── config.json                  # Application configuration
├── languages.json               # Data-driven language definitions
├── requirements.txt             # Python dependencies
├── live_translate.spec          # PyInstaller spec
├── README.md                    # This file
├── ui/                          # UI components
│   ├── main_window.py           # Main application window
│   └── settings_panel.py        # Settings controls
├── overlay/
│   └── subtitle_overlay.py      # Floating subtitle overlay
├── audio/
│   └── wasapi_capture.py        # WASAPI loopback capture
├── speech/
│   └── whisper_engine.py        # faster-whisper wrapper
├── translation/
│   ├── argos_engine.py          # Argos Translate offline
│   └── libretranslate_engine.py # LibreTranslate online
├── settings/
│   └── settings_manager.py      # JSON config persistence
├── workers/
│   ├── capture_worker.py        # Audio capture thread
│   ├── recognition_worker.py    # Speech recognition thread
│   └── translation_worker.py    # Translation thread
├── assets/                      # Icons, images
├── models/                      # Bundled whisper models
└── installer/
    └── setup.iss                # Inno Setup script
```

## Logging

Logs are stored in:
```
%APPDATA%\LiveTranslateOverlay\logs\live_translate.log
```

Maximum log size: 5 MB with 3 rotating backups.

## Error Recovery

| Scenario | Behavior |
|----------|----------|
| No audio device | Shows error message, waits for device |
| Device disconnected | Graceful stop, shows status |
| Whisper model not loaded | Shows error, retries |
| Argos package missing | Clear instructions to install |
| LibreTranslate fails | Silent fallback to Argos |
| GPU not available | Silent fallback to CPU |

## License

Free and open source. No API keys, no subscriptions, no paid services.