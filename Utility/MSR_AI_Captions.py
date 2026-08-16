"""MSR AI Captions - DaVinci Resolve Workspace launcher.

IMPORTANT: this file must be installed directly in Resolve's
Fusion/Scripts/Utility folder, not inside an MSR_AI_Captions subfolder.
It launches the standalone Studio outside Resolve's embedded Python.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

APP_NAME = "MSR AI Captions"


def find_python():
    for command in (("py", "-3.11"), ("py", "-3.10"), ("py", "-3.12"), ("py", "-3"), ("python",)):
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


def search_roots():
    """Find the downloaded repository even when only this launcher is copied to Resolve."""
    here = Path(__file__).resolve()
    roots = [
        here.parent,
        here.parent.parent,
        here.parent.parent.parent,
        Path.cwd(),
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents",
    ]

    downloads = Path.home() / "Downloads"
    if downloads.exists():
        try:
            roots.extend(p for p in downloads.iterdir() if p.is_dir())
        except Exception:
            pass

    result = []
    seen = set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key not in seen:
            seen.add(key)
            result.append(root)
    return result


def find_studio():
    names = ("MSR_AI_Captions_Studio.py", "MSR AI Captions Studio.py")
    for root in search_roots():
        if not root.exists():
            continue

        for name in names:
            direct = root / name
            if direct.exists():
                return direct

        try:
            for name in names:
                for pattern in (f"*/{name}", f"*/*/{name}", f"*/*/*/{name}"):
                    for match in root.glob(pattern):
                        if match.exists():
                            return match
        except Exception:
            pass

    return None


def launch():
    studio = find_studio()
    if studio is None:
        raise RuntimeError(
            "MSR AI Captions Studio was not found.\n\n"
            "Keep the downloaded GitHub repository folder intact.\n"
            "It must contain:\n\n"
            "  MSR_AI_Captions_Studio.py\n"
            "  backend\\msr_gemini_backend.py\n"
            "  requirements.txt\n"
            "  .env\n\n"
            "The Workspace script will automatically search Downloads,\n"
            "Desktop and the plugin folder for the Studio."
        )

    python = find_python()
    if python is None:
        raise RuntimeError(
            "Python 3.10+ was not found.\n\n"
            "Open Command Prompt and verify:\n"
            "py --version"
        )

    env = os.environ.copy()
    env.setdefault("RESOLVE_SCRIPT_HOST", "127.0.0.1")

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
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_NAME, str(exc))
            root.destroy()
        except Exception:
            # Resolve will show the exception in its script console.
            raise


if __name__ == "__main__":
    main()
