"""MSR AI Captions - DaVinci Resolve Workspace launcher.

Resolve executes Workspace scripts inside its embedded Python environment.
This launcher finds normal Windows Python and starts the Studio UI with
pythonw.exe so no Command Prompt window is opened.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:
    tk = None
    messagebox = None

APP_NAME = "MSR AI Captions"


def show_error(title, text):
    if tk is not None and messagebox is not None:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, text)
            root.destroy()
            return
        except Exception:
            pass
    print(f"{title}: {text}")


def windows_pythonw():
    """Find the real pythonw.exe, avoiding a console window."""
    candidates = []

    for version in ("3.12", "3.11", "3.10"):
        try:
            p = subprocess.run(
                ["py", f"-{version}", "-c", "import sys; print(sys.executable)"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if p.returncode == 0:
                exe = Path(p.stdout.strip())
                if exe.exists():
                    candidates.append(exe)
        except Exception:
            pass

    try:
        current = Path(sys.executable)
        if current.exists():
            candidates.append(current)
    except Exception:
        pass

    for exe in candidates:
        if exe.name.lower() == "pythonw.exe" and exe.exists():
            return exe
        if exe.name.lower() == "python.exe":
            pythonw = exe.with_name("pythonw.exe")
            if pythonw.exists():
                return pythonw

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    for root in [
        local / "Programs" / "Python",
        Path(r"C:\Python312"), Path(r"C:\Python311"), Path(r"C:\Python310")
    ]:
        if root.exists():
            try:
                matches = list(root.glob("**/pythonw.exe"))
                if matches:
                    return matches[0]
            except Exception:
                pass

    return None


def candidate_roots():
    roots = []
    appdata = os.environ.get("APPDATA", "")

    if appdata:
        scripts = (
            Path(appdata) / "Blackmagic Design" / "DaVinci Resolve"
            / "Support" / "Fusion" / "Scripts"
        )
        roots.extend([scripts / "MSR-AI-Captions-Plugin", scripts])

    home = Path.home()
    roots.extend([
        home / "Downloads" / "MSR-AI-Captions-Plugin-main",
        home / "Downloads" / "MSR-AI-Captions-Plugin",
        home / "Desktop" / "MSR-AI-Captions-Plugin-main",
        home / "Desktop" / "MSR-AI-Captions-Plugin",
        home / "Documents" / "MSR-AI-Captions-Plugin-main",
        home / "Documents" / "MSR-AI-Captions-Plugin",
    ])

    downloads = home / "Downloads"
    if downloads.exists():
        try:
            roots.extend(p for p in downloads.iterdir() if p.is_dir())
        except Exception:
            pass

    unique, seen = [], set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def find_studio():
    names = ("MSR_AI_Captions_Studio.py", "MSR AI Captions Studio.py")
    for root in candidate_roots():
        if not root.exists() or not root.is_dir():
            continue
        for name in names:
            direct = root / name
            if direct.is_file():
                return direct
        try:
            for name in names:
                for depth in range(1, 4):
                    pattern = "/".join(["*"] * depth + [name])
                    for match in root.glob(pattern):
                        if match.is_file():
                            return match
        except Exception:
            pass
    return None


def launch():
    studio = find_studio()
    if studio is None:
        raise RuntimeError(
            "MSR AI Captions Studio was not found.\n\n"
            "Keep the GitHub plugin folder intact. It must contain:\n"
            "MSR_AI_Captions_Studio.py\n"
            "backend\\msr_gemini_backend.py\n"
            "requirements.txt\n\n"
            "Recommended location:\n"
            "%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\MSR-AI-Captions-Plugin"
        )

    pythonw = windows_pythonw()
    if pythonw is None:
        raise RuntimeError(
            "pythonw.exe was not found. Python is installed, but its GUI executable could not be located."
        )

    env = os.environ.copy()
    env["RESOLVE_SCRIPT_HOST"] = "127.0.0.1"
    env["MSR_RESOLVE_LAUNCHED"] = "1"

    # Critical fix: pythonw.exe launches the Tkinter Studio without CMD.
    subprocess.Popen(
        [str(pythonw), str(studio)],
        cwd=str(studio.parent),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ),
        close_fds=True,
    )


def main():
    try:
        launch()
    except Exception as exc:
        show_error(APP_NAME, str(exc))


main()
