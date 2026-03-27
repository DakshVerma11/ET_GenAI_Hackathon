@echo off
echo.
echo ╔════════════════════════════════════════════════╗
echo ║   ET Markets - Chart Pattern Intelligence      ║
echo ║         Starting FastAPI Server...             ║
echo ╚════════════════════════════════════════════════╝
echo.
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo.
echo Checking dependencies...
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo ✓ All checks passed
echo.
echo Starting server on http://localhost:8000
echo.
echo Press CTRL+C to stop the server
echo.
python main.py
pause
