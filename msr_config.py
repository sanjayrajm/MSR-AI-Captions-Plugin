from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ID = "774512798784"
DEFAULT_MODEL = "gemini-3.6-flash"
ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def ensure_env_file() -> Path:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            f"GEMINI_API_KEY=PASTE_NEW_KEY_HERE\n"
            f"GEMINI_PROJECT_ID={PROJECT_ID}\n"
            f"GEMINI_MODEL={DEFAULT_MODEL}\n",
            encoding="utf-8",
        )
    return ENV_FILE


def load_env_file() -> dict[str, str]:
    ensure_env_file()
    values: dict[str, str] = {}
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def gemini_configured() -> bool:
    env = load_env_file()
    key = os.getenv("GEMINI_API_KEY", "").strip() or env.get("GEMINI_API_KEY", "").strip()
    return bool(key and key != "PASTE_NEW_KEY_HERE")


def resolve_paths() -> list[Path]:
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    return [
        program_files / "Blackmagic Design" / "DaVinci Resolve" / "Developer" / "Scripting" / "Modules",
        program_files / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripting" / "Modules",
        program_files_x86 / "Blackmagic Design" / "DaVinci Resolve" / "Developer" / "Scripting" / "Modules",
        program_data / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting" / "Modules",
    ]


def python_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    for version in ("3.11", "3.10", "3.12"):
        commands.append(["py", f"-{version}"])
    commands += [["py"], ["python"]]
    return commands


def find_python() -> list[str]:
    for command in python_commands():
        try:
            p = subprocess.run(
                command + ["--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if p.returncode == 0:
                return command
        except Exception:
            pass
    raise RuntimeError("Python 3.10+ was not found. Install Python and restart this app.")
