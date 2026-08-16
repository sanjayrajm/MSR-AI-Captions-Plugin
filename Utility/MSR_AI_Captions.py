#!/usr/bin/env python3
"""MSR AI Captions Resolve Workspace launcher.

This file deliberately does not run Tkinter, Gemini, or third-party packages
inside Resolve's embedded Python. It only launches the standalone Studio app.
That avoids the common 'Workspace > Scripts > MSR AI Captions does nothing'
problem caused by missing Tkinter/google packages inside Resolve Python.
"""

from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "MSR_AI_Captions_Studio.py"


def find_python():
    candidates = [
        ["py", "-3.11"],
        ["py", "-3.10"],
        ["py", "-3.12"],
        ["py"],
        ["python"],
    ]
    for command in candidates:
        try:
            result = subprocess.run(
                command + ["--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return command
        except Exception:
            pass
    return None


def main():
    if not STUDIO.exists():
        raise RuntimeError(f"MSR AI Captions Studio was not found:\n{STUDIO}")

    python = find_python()
    if python is None:
        raise RuntimeError(
            "Python 3.10+ was not found. Install Python 3.10 or 3.11, "
            "then restart DaVinci Resolve."
        )

    env = os.environ.copy()
    env.setdefault("RESOLVE_SCRIPT_HOST", "127.0.0.1")
    subprocess.Popen(
        python + [str(STUDIO)],
        cwd=str(ROOT),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


if __name__ == "__main__":
    main()
