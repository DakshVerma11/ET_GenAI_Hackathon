@echo off
cd /d "%~dp0"

echo =======================================================
echo 🎥 AI Market Video Engine - Startup Script
echo =======================================================

set "VENV_DIR=.venv"

IF NOT EXIST "%VENV_DIR%" (
    echo [1/3] Creating virtual environment...
    python -m venv "%VENV_DIR%"
) ELSE (
    echo [1/3] Virtual environment already exists.
)

echo [2/3] Activating virtual environment and installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
"%VENV_DIR%\Scripts\python.exe" -m pip install -q -r requirements.txt

echo [3/3] Launching Streamlit app...
"%VENV_DIR%\Scripts\python.exe" -m streamlit run app.py

pause
