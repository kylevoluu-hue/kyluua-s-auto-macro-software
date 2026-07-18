@echo off
REM ============================================================
REM  Build AutoMacro into a single pinnable Windows .exe
REM  Just double-click this file (or run it from a terminal).
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo === Building AutoMacro for Windows ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo Install Python 3.9+ from https://python.org and tick "Add to PATH".
    pause
    exit /b 1
)

echo Creating build environment...
python -m venv .buildenv || goto :error
call .buildenv\Scripts\activate.bat || goto :error

echo Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller || goto :error

echo Packaging (this can take a couple of minutes)...
pyinstaller --noconfirm automacro.spec || goto :error

echo.
echo ============================================================
echo  Done!  Your app is here:
echo      dist\AutoMacro.exe
echo.
echo  Right-click it -> "Pin to taskbar" or "Pin to Start"
echo  to keep it handy like any other application.
echo ============================================================
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] Build failed. Scroll up to see what went wrong.
pause
exit /b 1
