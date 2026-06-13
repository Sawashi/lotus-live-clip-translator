@echo off
REM python312.bat — Run any command inside the project's Python 3.12 venv.
REM
REM This batch file wraps run_with_py312.py for convenience in cmd.exe.
REM Usage:
REM     python312 pip install -r requirements.txt
REM     python312 main.py
REM     python312 python -c "print('hi')"

python "%~dp0run_with_py312.py" %*
exit /b %ERRORLEVEL%