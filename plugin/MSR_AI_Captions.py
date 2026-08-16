import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
EXE = APP / "MSR_AI_Captions.exe"
PY = APP / "main.py"

startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW

if EXE.exists():
    subprocess.Popen(
        [str(EXE)],
        cwd=str(APP),
        startupinfo=startup,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
else:
    subprocess.Popen(
        ["py", "-3", str(PY)],
        cwd=str(APP),
        startupinfo=startup,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
