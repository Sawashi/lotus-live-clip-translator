@echo off
REM ==============================================================
REM CUDA 12.4 Setup Helper for Live Translate Overlay
REM
REM This script helps users install / verify CUDA 12.4
REM and required NVIDIA dependencies.
REM
REM Usage:
REM   Run as Administrator:  installer\cuda_setup.bat
REM
REM This will:
REM   1. Check if CUDA 12.4 is already installed
REM   2. If not, prompt to download and install
REM   3. Install required Python CUDA packages via pip
REM ==============================================================
setlocal enabledelayedexpansion

set APP_NAME=Live Translate Overlay
set REQUIRED_CUDA_MAJOR=12
set REQUIRED_CUDA_MINOR=4

echo ============================================================
echo         %APP_NAME% - CUDA Setup Helper
echo ============================================================
echo.

REM ---- Step 1: Check NVIDIA GPU ----
echo [1/4] Checking for NVIDIA GPU...
nvidia-smi --query-gpu=name --format=csv,noheader >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   WARNING: nvidia-smi not found.
    echo   This means no NVIDIA GPU driver is installed.
    echo   The app will run in CPU-only mode (slower).
    echo.
    echo   To install NVIDIA driver:
    echo     https://www.nvidia.com/download/index.aspx
    echo.
    set /p INSTALL_DRIVER=Would you like to open the NVIDIA driver page? (y/n): 
    if /i "!INSTALL_DRIVER!"=="y" start https://www.nvidia.com/download/index.aspx
) else (
    for /f "tokens=*" %%a in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader') do (
        echo   GPU detected: %%a
    )
)

echo.

REM ---- Step 2: Check CUDA Version ----
echo [2/4] Checking CUDA version...
nvcc --version 2>&1 | findstr "release" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   CUDA toolkit not found (nvcc missing).
    echo   Checking via nvidia-smi...
    nvidia-smi 2>&1 | findstr "CUDA Version" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        for /f "tokens=4" %%a in ('nvidia-smi ^| findstr "CUDA Version"') do (
            echo   CUDA driver version: %%a
        )
        echo   Compatible CUDA runtime available via driver.
        echo   No additional CUDA toolkit installation needed.
    ) else (
        echo.
        echo   CUDA not detected. The app will run in CPU mode.
        echo.
        echo   To install CUDA 12.4:
        echo     https://developer.nvidia.com/cuda-12-4-0-download-archive
        echo.
        set /p INSTALL_CUDA=Open CUDA download page? (y/n): 
        if /i "!INSTALL_CUDA!"=="y" start https://developer.nvidia.com/cuda-12-4-0-download-archive
    )
) else (
    for /f "tokens=*" %%a in ('nvcc --version ^| findstr "release"') do (
        echo   CUDA toolkit: %%a
    )
)

echo.

REM ---- Step 3: Install Python CUDA packages ----
echo [3/4] Installing Python CUDA packages...
echo   These are needed for GPU-accelerated inference.
pip install nvidia-cublas-cu12==12.9.2.10 nvidia-cudnn-cu12==8.9.7.29 nvidia-cuda-nvrtc-cu12==12.9.86
if %ERRORLEVEL% EQU 0 (
    echo   CUDA Python packages installed successfully.
) else (
    echo   WARNING: Some CUDA packages failed to install.
    echo   The app may fall back to CPU mode.
)

echo.

REM ---- Step 4: Verify ----
echo [4/4] Verifying CUDA setup...
python -c "import torch; print('PyTorch CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')" 2>&1

echo.
echo ============================================================
echo         CUDA Setup Complete
echo ============================================================
echo.
echo If PyTorch reports CUDA available, you're all set!
echo If not, try restarting your computer and running this again.
echo.
echo For logs, check: %%LOCALAPPDATA%%\%APP_NAME%\logs\
echo.
pause