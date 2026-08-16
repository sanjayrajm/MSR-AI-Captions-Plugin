"""MSR AI Captions - DaVinci Resolve Workspace launcher.

This script is executed by DaVinci Resolve's embedded scripting engine.
Resolve may execute Workspace scripts with exec(), where __file__ is NOT
defined. Therefore this launcher deliberately never uses __file__.

Install this file directly in:
%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility

It launches the standalone MSR AI Captions Studio with normal Windows Python.
"""
from __future__ import annotations

import os
import subprocess
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


def find_python():
    # Prefer Python versions commonly used with the plugin. The user's
    # Python 3.12 is also supported.
    for command in (
        ("py", "-3.11"),
        ("py", "-3.10"),
        ("py", "-3.12"),
        ("py", "-3"),
        ("python",),
    ):
        try:
            result = subprocess.run(
                list(command) + ["--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return list(command)
        except Exception:
            pass
    return None


def candidate_roots():
    """Return likely plugin locations without relying on __file__."""
    roots = []

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        fusion_scripts = (
            Path(appdata)
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
        )
        roots.extend(
            [
                fusion_scripts,
                fusion_scripts / "MSR-AI-Captions-Plugin",
                fusion_scripts / "Utility",
            ]
        )

    home = Path.home()
    roots.extend([
        home / "Downloads" / "MSR-AI-Captions-Plugin-main",
        home / "Downloads" / "MSR-AI-Captions-Plugin",
        home / "Desktop" / "MSR-AI-Captions-Plugin-main",
        home / "Desktop" / "MSR-AI-Captions-Plugin",
        home / "Documents" / "MSR-AI-Captions-Plugin-main",
        home / "Documents" / "MSR-AI-Captions-Plugin",
    ])

    # Also inspect immediate folders in Downloads. This handles GitHub's
    # automatically generated folder name without scanning the whole drive.
    downloads = home / "Downloads"
    if downloads.exists():
        try:
            roots.extend(p for p in downloads.iterdir() if p.is_dir())
        except Exception:
            pass

    unique = []
    seen = set()
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
    """Locate MSR_AI_Captions_Studio.py in known plugin folders."""
    names = (
        "MSR_AI_Captions_Studio.py",
        "MSR AI Captions Studio.py",
    )

    for root in candidate_roots():
        if not root.exists() or not root.is_dir():
            continue

        for name in names:
            direct = root / name
            if direct.is_file():
                return direct

        # Common layouts:
        # root/MSR_AI_Captions_Studio.py
        # root/MSR-AI-Captions-Plugin-main/MSR_AI_Captions_Studio.py
        # root/MSR-AI-Captions-Plugin/main/MSR_AI_Captions_Studio.py
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
            "The GitHub plugin folder must contain:\n"
            "  MSR_AI_Captions_Studio.py\n"
            "  backend\\msr_gemini_backend.py\n"
            "  requirements.txt\n\n"
            "Recommended location:\n"
            "%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\MSR-AI-Captions-Plugin\n\n"
            "The launcher searches that location and Downloads."
        )

    python = find_python()
    if python is None:
        raise RuntimeError(
            "Python 3.10+ was not found.\n\n"
            "Open Command Prompt and run:\n"
            "py --version"
        )

    env = os.environ.copy()
    env.setdefault("RESOLVE_SCRIPT_HOST", "127.0.0.1")
    env.setdefault("MSR_RESOLVE_LAUNCHED", "1")

    # Start the Studio as a normal Windows process, not inside Resolve's
    # embedded Python. This avoids missing package/Tkinter issues.
    subprocess.Popen(
        python + [str(studio)],
        cwd=str(studio.parent),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def main():
    try:
        launch()
    except Exception as exc:
        show_error(APP_NAME, str(exc))


main()
