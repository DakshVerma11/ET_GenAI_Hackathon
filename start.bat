@echo off
chcp 65001 >nul
title ET Markets AI Intelligence Platform

echo.
echo  ╔════════════════════════════════════════════════════════╗
echo  ║       ET Markets AI Intelligence Platform              ║
echo  ║       Starting all services...                         ║
echo  ╚════════════════════════════════════════════════════════╝
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found in PATH.
    echo  Please install Python 3.8+ from https://www.python.org
    echo.
    pause
    exit /b 1
)

:: Run the master launcher
python "%~dp0start.py" %*

echo.
pause
