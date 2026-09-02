@echo off
title LOQ Jet Engine - Setup
color 0B
echo =======================================================
echo          LOQ JET ENGINE - AUTOMATED SETUP
echo   Lenovo LOQ 15IRX9 (83DV) - i7-13645HX / RTX 4050
echo =======================================================
echo.
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing required Python packages...
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some packages failed to install. Retrying with --user...
    python -m pip install --user -r requirements.txt
)

echo.
echo =======================================================
echo [SUCCESS] Setup complete! You can now run the app via run.bat.
echo =======================================================
echo.
pause
