@echo off
setlocal
chcp 65001 >nul 2>&1
title Blockchain Crowdfunding - One-Click Launcher
cls

echo ================================================================
echo              BLOCKCHAIN CROWDFUNDING SYSTEM
echo             [ ONE-CLICK TEST LAUNCHER ]
echo ================================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

python "%~dp0one_click_launcher.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Launcher exited with code %EXIT_CODE%.
)

pause
exit /b %EXIT_CODE%