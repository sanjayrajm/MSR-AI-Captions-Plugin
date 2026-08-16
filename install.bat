@echo off
setlocal EnableExtensions
title MSR AI Captions - DaVinci Resolve Installer

set "PLUGIN=%~dp0"
set "SCRIPTS=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
set "UTILITY=%SCRIPTS%\Utility"
set "BACKEND=%SCRIPTS%\backend"

if not exist "%SCRIPTS%" mkdir "%SCRIPTS%"
if not exist "%UTILITY%" mkdir "%UTILITY%"
if not exist "%BACKEND%" mkdir "%BACKEND%"

echo.
echo ================================================
echo   MSR AI CAPTIONS - RESOLVE INSTALLER
 echo ================================================
echo.
echo Installing to:
echo %SCRIPTS%
echo.

rem IMPORTANT: the Workspace launcher is a FILE directly in Utility.
rem Do not put it inside Utility\MSR_AI_Captions\ because that creates
rem the arrow/submenu shown in Resolve and is a common installation error.
copy /Y "%PLUGIN%Utility\MSR_AI_Captions.py" "%UTILITY%\MSR_AI_Captions.py" >nul

rem The Studio and backend must live together so the Workspace launcher can find them.
copy /Y "%PLUGIN%MSR_AI_Captions_Studio.py" "%SCRIPTS%\MSR_AI_Captions_Studio.py" >nul
copy /Y "%PLUGIN%backend\msr_gemini_backend.py" "%BACKEND%\msr_gemini_backend.py" >nul
copy /Y "%PLUGIN%requirements.txt" "%SCRIPTS%\requirements.txt" >nul

if not exist "%SCRIPTS%\.env" (
  copy /Y "%PLUGIN%.env.example" "%SCRIPTS%\.env" >nul
)

where py >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Python was not found.
  echo Install Python 3.10+ and verify: py --version
  pause
  exit /b 1
)

echo Installing Python dependencies...
py -3 -m pip install -r "%SCRIPTS%\requirements.txt"
if errorlevel 1 (
  echo.
  echo Dependency installation failed. You can run the command manually:
  echo py -3 -m pip install -r "%SCRIPTS%\requirements.txt"
  pause
  exit /b 1
)

echo.
echo ================================================
echo Installation complete.
echo ================================================
echo.
echo IMPORTANT:
echo 1. Edit this file and add your NEW Gemini key:
echo    %SCRIPTS%\.env
 echo 2. Open DaVinci Resolve Studio.
echo 3. Preferences ^> System ^> General.
echo 4. Set External Scripting Using = Local.
echo 5. Restart Resolve.
echo 6. Use Workspace ^> Scripts ^> Utility ^> MSR AI Captions.
echo.
echo The MSR AI Captions entry must NOT have an arrow beside it.
echo It should be a direct script item.
echo.
pause
