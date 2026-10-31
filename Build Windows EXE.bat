@echo off
setlocal
cd /d "%~dp0"

where python.exe >nul 2>nul
if errorlevel 1 (
    echo Python 3 is not installed or python.exe is not on PATH.
    pause
    exit /b 1
)

python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller for the current Windows user...
    python -m pip install --user pyinstaller
    if errorlevel 1 (
        echo Could not install PyInstaller.
        pause
        exit /b 1
    )
)

python -m PyInstaller --noconfirm --clean --windowed --name ZishanIslamicClock desktop\zishan_clock.py
if errorlevel 1 (
    echo EXE build failed.
    pause
    exit /b 1
)

echo Built dist\ZishanIslamicClock\ZishanIslamicClock.exe
pause
