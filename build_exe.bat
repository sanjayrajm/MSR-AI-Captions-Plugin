@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
py -3 -m PyInstaller --noconfirm --clean --windowed --name MSR_AI_Captions --paths app app\main.py
if exist app\MSR_AI_Captions.exe del /q app\MSR_AI_Captions.exe
copy /y dist\MSR_AI_Captions\MSR_AI_Captions.exe app\MSR_AI_Captions.exe
echo.
echo EXE is ready:
echo %CD%\app\MSR_AI_Captions.exe
pause
