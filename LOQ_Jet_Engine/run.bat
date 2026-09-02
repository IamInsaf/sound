@echo off
title LOQ Jet Engine
color 0C
cd /d "%~dp0"
python LOQ_Jet_Engine.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    echo If this is your first time, please run setup.bat first.
    pause
)
