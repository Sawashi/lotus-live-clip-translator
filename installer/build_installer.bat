@echo off
setlocal enabledelayedexpansion

REM ==============================================================
REM Build Script for Live Translate Overlay Installer
REM
REM This script automates the full build pipeline:
REM   1. Run pre-install checks
REM   2. Build the PyInstaller executable
REM   3. Build the Inno Setup installer (multi-part if large)
REM   4. Output to dist/ folder
REM
REM Prerequisites:
REM   - Python 3.10+ with all dependencies installed
REM   - PyInstaller (pip install pyinstaller)
REM   - Inno Setup 6+ with iscc.exe in PATH
REM     (Download: https://jrsoftware.org/isdl.php)
REM   - Microsoft Visual C++ Redistributable
REM     (Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
REM      and copy to installer/vc_redist.x64.exe)
REM
REM Usage:
REM   From project root:  installer\build_installer.bat
REM ==============================================================

set PROJECT_ROOT=%~dp0..
set LOG_FILE=%PROJECT_ROOT%\dist\build_log.txt
set BUILD_START=%DATE% %TIME%

echo ============================================================
echo     Live Translate Overlay - Installer Builder
echo ============================================================
echo.
echo Build started: %BUILD_START%
echo Project: %PROJECT_ROOT%
echo Log: %LOG_FILE%
echo.

REM Create dist directory
if not exist "%PROJECT_ROOT%\dist" mkdir "%PROJECT_ROOT%\dist"
echo Build started: %BUILD_START% > "%LOG_FILE%"

REM ---- Step 1: Pre-install check ----
echo [Step 1/5] Running pre-install checks...
echo [1/5] Pre-install checks >> "%LOG_FILE%"
python "%PROJECT_ROOT%\installer\preinstall_check.py" 2>&1 >> "%LOG_FILE%"
if %ERRORLEVEL% NEQ 0 (
    echo   WARNING: Some checks failed. Continuing anyway...
    echo   WARNING: Pre-install checks failed >> "%LOG_FILE%"
)
echo.

REM ---- Step 2: Clean previous build ----
echo [Step 2/5] Cleaning previous build artifacts...
echo [2/5] Cleaning build artifacts >> "%LOG_FILE%"
if exist "%PROJECT_ROOT%\build" (
    rmdir /s /q "%PROJECT_ROOT%\build"
    echo   Removed build/
)
if exist "%PROJECT_ROOT%\dist\LiveTranslateOverlay" (
    rmdir /s /q "%PROJECT_ROOT%\dist\LiveTranslateOverlay"
    echo   Removed dist/LiveTranslateOverlay/
)
REM Delete old installer files from previous builds
del /q "%PROJECT_ROOT%\dist\LiveTranslateOverlay_Setup_v*.exe" 2>nul
del /q "%PROJECT_ROOT%\dist\LiveTranslateOverlay_Setup_v*.bin" 2>nul
echo   Removed old installer artifacts
echo   Clean complete.
echo.

REM ---- Step 3: PyInstaller build ----
echo [Step 3/5] Building executable with PyInstaller...
echo [3/5] PyInstaller build >> "%LOG_FILE%"
cd /d "%PROJECT_ROOT%"
pyinstaller --clean --noconfirm live_translate.spec 2>&1 >> "%LOG_FILE%"
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: PyInstaller build FAILED!
    echo   Check log: %LOG_FILE%
    echo   ERROR: PyInstaller build FAILED >> "%LOG_FILE%"
    pause
    exit /b 1
)
echo   PyInstaller build complete.
echo   Output: %PROJECT_ROOT%\dist\LiveTranslateOverlay\
echo.

REM ---- Step 3b: Verify exe exists ----
if not exist "%PROJECT_ROOT%\dist\LiveTranslateOverlay\LiveTranslateOverlay.exe" (
    echo   ERROR: LiveTranslateOverlay.exe not found after build!
    echo   ERROR: Exe not found >> "%LOG_FILE%"
    pause
    exit /b 1
)
for %%a in ("%PROJECT_ROOT%\dist\LiveTranslateOverlay\LiveTranslateOverlay.exe") do (
    set EXE_SIZE=%%~za
)
echo   Exe size: %EXE_SIZE% bytes
echo.

REM ---- Step 4: Check for VC++ redist ----
echo [Step 4/5] Checking for VC++ redistributable...
echo [4/5] VC++ redist check >> "%LOG_FILE%"
if not exist "%PROJECT_ROOT%\installer\vc_redist.x64.exe" (
    echo   WARNING: vc_redist.x64.exe not found.
    echo   The installer will NOT bundle VC++ Redist.
    echo.
    echo   To include it:
    echo     1. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo     2. Save to: installer\vc_redist.x64.exe
    echo.
    echo   Without it, users may need to install VC++ Redist manually.
    echo   WARNING: vc_redist.x64.exe missing >> "%LOG_FILE%"
) else (
    echo   VC++ Redist found.
)

echo.

REM ---- Step 5: Build Inno Setup installer ----
echo [Step 5/5] Building Inno Setup installer...
echo [5/5] Inno Setup build >> "%LOG_FILE%"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "%PROJECT_ROOT%\installer\setup.iss" 2>&1 >> "%LOG_FILE%"
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Inno Setup build FAILED!
    echo   Check log: %LOG_FILE%
    echo.
    echo   Make sure Inno Setup is installed and iscc.exe is in PATH.
    echo   Download: https://jrsoftware.org/isdl.php
    echo   ERROR: Inno Setup build FAILED >> "%LOG_FILE%"
    pause
    exit /b 1
)
echo.
echo   Inno Setup build complete.
echo.

REM ---- Done ----
set BUILD_END=%DATE% %TIME%
echo ============================================================
echo     BUILD COMPLETE
echo ============================================================
echo.
echo Started:  %BUILD_START%
echo Finished: %BUILD_END%
echo.
echo Output in: %PROJECT_ROOT%\dist\
echo.
echo Installer files:
dir "%PROJECT_ROOT%\dist\LiveTranslateOverlay_Setup_v*.exe" 2>nul
dir "%PROJECT_ROOT%\dist\LiveTranslateOverlay_Setup_v*.bin" 2>nul
echo.
echo Build log: %LOG_FILE%
echo.
echo To distribute:
echo   - Zip both: LiveTranslateOverlay_Setup_v*.exe + LiveTranslateOverlay\ folder
echo   - Users run the .exe to install into Program Files
echo   - These are already in: %PROJECT_ROOT%\dist\
echo.
echo Build finished: %BUILD_END% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

pause