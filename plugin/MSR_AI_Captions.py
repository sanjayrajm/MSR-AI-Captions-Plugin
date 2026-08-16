from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Resolve loads this file from:
# ...\Fusion\Scripts\MSR-AI-Captions-Plugin\plugin\MSR_AI_Captions.py
ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
EXE = APP_DIR / "MSR_AI_Captions.exe"
MAIN = APP_DIR / "main.py"
LOG = APP_DIR / "MSR_AI_Captions_launcher.log"


# Never show a console window when launching the desktop application.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def pythonw_executable():
    """Use the same Python installation without opening a CMD window."""
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def launch():
    try:
        if EXE.exists():
            command = [str(EXE)]
        elif MAIN.exists():
            command = [pythonw_executable(), str(MAIN)]
        else:
            raise FileNotFoundError(
                "MSR AI Captions application was not found.\n"
                f"Expected EXE: {EXE}\n"
                f"Expected Python app: {MAIN}"
            )

        subprocess.Popen(
            command,
            cwd=str(APP_DIR),
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )

    except Exception as exc:
        try:
            LOG.write_text(
                f"MSR AI Captions launcher error:\n{type(exc).__name__}: {exc}\n",
                encoding="utf-8",
            )
        except Exception:
            pass


launch()
