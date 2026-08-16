@echo off
setlocal
title MSR AI Captions - Resolve Plugin Installer
set "PLUGIN=%~dp0"
set "TARGET=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
echo Installing MSR AI Captions Resolve script...
if not exist "%TARGET%" mkdir "%TARGET%"
copy /Y "%PLUGIN%Utility\MSR_AI_Captions.py" "%TARGET%\MSR_AI_Captions.py" >nul
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.10+ first.
  pause
  exit /b 1
)
py -3 -m pip install -r "%PLUGIN%requirements.txt"
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
echo.
echo Installation complete.
echo Restart DaVinci Resolve and open:
echo Workspace ^> Scripts ^> Utility ^> MSR AI Captions
echo.
pause
