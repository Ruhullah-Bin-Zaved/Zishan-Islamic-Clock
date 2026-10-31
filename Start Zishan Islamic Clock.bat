@echo off
cd /d "%~dp0"
where pythonw.exe >nul 2>nul
if errorlevel 1 (
    echo Python 3 is not installed or pythonw.exe is not on PATH.
    echo Install Python from https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
start "" pythonw.exe "%~dp0desktop\zishan_clock.py"
