from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "MSR AI Captions Studio"
PROJECT_ID = "774512798784"
DEFAULT_MODEL = "gemini-3.6-flash"

LANGUAGES = [
    "Original", "Auto Detect", "English", "Tamil", "Hindi", "Telugu",
    "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi",
    "Urdu", "Spanish", "French", "German", "Italian", "Portuguese",
    "Arabic", "Japanese", "Korean", "Chinese", "Indonesian"
]


def candidate_resolve_module_paths():
    paths = []
    program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
    local_app = os.environ.get("LOCALAPPDATA", "")

    roots = [
        Path(program_files) / "Blackmagic Design" / "DaVinci Resolve",
        Path(program_files_x86) / "Blackmagic Design" / "DaVinci Resolve",
        Path(local_app) / "Programs" / "Blackmagic Design" / "DaVinci Resolve",
    ]

    for root in roots:
        paths.extend([
            root / "fusionscript.dll",
            root / "Developer" / "Scripting" / "Modules",
            root / "Fusion" / "Scripting" / "Modules",
            root / "Support" / "Developer" / "Scripting" / "Modules",
        ])
    return paths


def load_resolve_api():
    """Load Resolve's scripting module from common Windows locations."""
    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script
    except Exception:
        pass

    for candidate in candidate_resolve_module_paths():
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
        elif candidate.name == "fusionscript.dll" and candidate.exists():
            dll_dir = str(candidate.parent)
            if dll_dir not in sys.path:
                sys.path.insert(0, dll_dir)
            try:
                import DaVinciResolveScript as dvr_script
                return dvr_script
            except Exception:
                continue
    return None


def connect_resolve(mode="Local", host="127.0.0.1", timeout=5):
    dvr = load_resolve_api()
    if dvr is None:
        return None, "DaVinciResolveScript module was not found."

    try:
        if mode == "Network":
            app = dvr.scriptapp("Resolve", host, float(timeout))
        else:
            app = dvr.scriptapp("Resolve")
        if app is None:
            return None, "Resolve returned no scripting connection."
        return app, "Connected to DaVinci Resolve."
    except Exception as exc:
        return None, f"Resolve connection error: {exc}"


def resolve_info(resolve):
    data = {}
    try:
        data["version"] = resolve.GetVersionString()
    except Exception:
        data["version"] = "Unknown"
    try:
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        data["project"] = project.GetName() if project else "No project"
        timeline = project.GetCurrentTimeline() if project else None
        data["timeline"] = timeline.GetName() if timeline else "No timeline"
    except Exception:
        data["project"] = "Unknown"
        data["timeline"] = "Unknown"
    return data


def find_python():
    for command in ("py", "python"):
        try:
            result = subprocess.run(
                [command, "--version"],
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


class Studio:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1050x720")
        self.root.minsize(900, 650)

        self.resolve = None
        self.media = tk.StringVar()
        self.language = tk.StringVar(value="Original")
        self.mode = tk.StringVar(value="Local")
        self.host = tk.StringVar(value="127.0.0.1")
        self.api_status = tk.StringVar(value="Gemini key: not checked")
        self.resolve_status = tk.StringVar(value="Resolve: not connected")
        self.project_status = tk.StringVar(value="Project: —")
        self.timeline_status = tk.StringVar(value="Timeline: —")
        self.status = tk.StringVar(value="Ready")
        self.progress = tk.DoubleVar(value=0)
        self.import_resolve = tk.BooleanVar(value=True)

        self.build_ui()
        self.root.after(300, self.check_all)

    def build_ui(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except Exception:
            pass

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="MSR AI CAPTIONS", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(header, text="Gemini transcription + smart subtitles + DaVinci Resolve control", font=("Segoe UI", 10)).pack(anchor="w")

        connection = ttk.LabelFrame(outer, text="DaVinci Resolve Connection", padding=12)
        connection.pack(fill="x", pady=(18, 8))

        top = ttk.Frame(connection)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.resolve_status).pack(side="left")
        ttk.Button(top, text="Connect / Reconnect", command=self.connect_clicked).pack(side="right")
        ttk.Button(top, text="Check Permissions", command=self.permissions).pack(side="right", padx=8)

        details = ttk.Frame(connection)
        details.pack(fill="x", pady=(10, 0))
        ttk.Label(details, textvariable=self.project_status).pack(side="left", padx=(0, 20))
        ttk.Label(details, textvariable=self.timeline_status).pack(side="left")

        mode = ttk.Frame(connection)
        mode.pack(fill="x", pady=(10, 0))
        ttk.Label(mode, text="External scripting:").pack(side="left")
        ttk.Combobox(mode, textvariable=self.mode, values=["Local", "Network"], state="readonly", width=12).pack(side="left", padx=8)
        ttk.Label(mode, text="Host:").pack(side="left")
        ttk.Entry(mode, textvariable=self.host, width=18).pack(side="left", padx=8)
        ttk.Label(mode, text="Use Local for this PC.").pack(side="left")

        media = ttk.LabelFrame(outer, text="Caption Job", padding=12)
        media.pack(fill="x", pady=8)
        row = ttk.Frame(media)
        row.pack(fill="x")
        ttk.Label(row, text="Media:").pack(side="left")
        ttk.Entry(row, textvariable=self.media).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=self.browse).pack(side="left")

        settings = ttk.Frame(media)
        settings.pack(fill="x", pady=(12, 0))
        ttk.Label(settings, text="Output language:").pack(side="left")
        ttk.Combobox(settings, textvariable=self.language, values=LANGUAGES, state="readonly", width=20).pack(side="left", padx=8)
        ttk.Checkbutton(settings, text="Import subtitle track into Resolve", variable=self.import_resolve).pack(side="left", padx=15)

        ai = ttk.LabelFrame(outer, text="Gemini", padding=12)
        ai.pack(fill="x", pady=8)
        ttk.Label(ai, textvariable=self.api_status).pack(side="left")
        ttk.Button(ai, text="Open .env", command=self.open_env).pack(side="right")
        ttk.Label(ai, text=f"Project: {PROJECT_ID}   Model: {DEFAULT_MODEL}").pack(side="right", padx=15)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=16)
        self.generate = ttk.Button(actions, text="GENERATE CAPTIONS", command=self.generate_clicked)
        self.generate.pack(side="left")
        ttk.Button(actions, text="Refresh Connection", command=self.check_all).pack(side="left", padx=8)
        ttk.Button(actions, text="Open Output Folder", command=self.open_output).pack(side="left")

        ttk.Progressbar(outer, variable=self.progress, maximum=100).pack(fill="x")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(7, 5))

        log_frame = ttk.LabelFrame(outer, text="Diagnostics", padding=8)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, wrap="word", state="disabled", height=14)
        self.log.pack(fill="both", expand=True)

    def write_log(self, text):
        def action():
            self.log.configure(state="normal")
            self.log.insert("end", text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, action)

    def set_status(self, text, progress=None):
        def action():
            self.status.set(text)
            if progress is not None:
                self.progress.set(progress)
        self.root.after(0, action)

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select video or audio",
            filetypes=[("Media", "*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac"), ("All files", "*.*")],
        )
        if path:
            self.media.set(path)

    def connect_clicked(self):
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        self.set_status("Connecting to Resolve...", 10)
        app, message = connect_resolve(self.mode.get(), self.host.get())
        if app:
            self.resolve = app
            info = resolve_info(app)
            self.root.after(0, lambda: self.resolve_status.set(f"Resolve: CONNECTED • {info['version']}"))
            self.root.after(0, lambda: self.project_status.set(f"Project: {info['project']}"))
            self.root.after(0, lambda: self.timeline_status.set(f"Timeline: {info['timeline']}"))
            self.write_log(message)
            self.write_log(f"Resolve version: {info['version']}")
            self.set_status("Resolve connected.", 25)
        else:
            self.resolve = None
            self.root.after(0, lambda: self.resolve_status.set("Resolve: NOT CONNECTED"))
            self.write_log(message)
            self.set_status("Resolve connection failed.", 0)

    def check_all(self):
        self._check_api()
        self.connect_clicked()

    def _check_api(self):
        env_file = Path(__file__).with_name(".env")
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key and env_file.exists():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if key and key != "PASTE_NEW_KEY_HERE":
            self.api_status.set("Gemini key: configured")
            self.write_log("Gemini API key found.")
        else:
            self.api_status.set("Gemini key: MISSING — configure .env")
            self.write_log("Gemini API key is missing.")

    def permissions(self):
        win = tk.Toplevel(self.root)
        win.title("MSR AI Captions — Resolve Permissions")
        win.geometry("700x520")
        win.transient(self.root)

        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="DaVinci Resolve permission checklist", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="For external software control, Resolve Studio must allow external scripting.", wraplength=640).pack(anchor="w", pady=(8, 15))

        steps = [
            "1. Open DaVinci Resolve Studio.",
            "2. Go to DaVinci Resolve > Preferences.",
            "3. Open System > General.",
            "4. Find External Scripting Using.",
            "5. Set it to Local when this software runs on the same PC.",
            "6. Click Save and restart Resolve if prompted.",
            "7. Keep Resolve open and open a project/timeline.",
            "8. Return here and click Connect / Reconnect.",
        ]
        for step in steps:
            ttk.Label(frame, text=step, wraplength=640).pack(anchor="w", pady=4)

        ttk.Separator(frame).pack(fill="x", pady=12)
        ttk.Label(frame, text="If you use Network mode, set the Resolve host to the machine IP. For same-PC Network mode use 127.0.0.1.", wraplength=640).pack(anchor="w")
        ttk.Label(frame, text="Note: Blackmagic documents External Scripting Using as a Resolve Studio setting. The free edition may not provide external scripting control.", wraplength=640).pack(anchor="w", pady=10)
        ttk.Button(frame, text="Close", command=win.destroy).pack(anchor="e", pady=8)

    def open_env(self):
        env = Path(__file__).with_name(".env")
        if not env.exists():
            env.write_text(
                "GEMINI_API_KEY=PASTE_NEW_KEY_HERE\n"
                f"GEMINI_PROJECT_ID={PROJECT_ID}\n"
                f"GEMINI_MODEL={DEFAULT_MODEL}\n",
                encoding="utf-8",
            )
        try:
            os.startfile(str(env))
        except Exception:
            messagebox.showinfo(APP_NAME, f"Edit this file:\n{env}")

    def open_output(self):
        if self.media.get():
            folder = Path(self.media.get()).resolve().parent / "_msr_ai_captions"
            if folder.exists():
                os.startfile(str(folder))
                return
        messagebox.showinfo(APP_NAME, "Generate captions first. Output will be stored in _msr_ai_captions beside the source media.")

    def generate_clicked(self):
        if not self.media.get():
            messagebox.showwarning(APP_NAME, "Select a video or audio file first.")
            return
        if not Path(self.media.get()).exists():
            messagebox.showwarning(APP_NAME, "The selected media file does not exist.")
            return
        self.generate.configure(state="disabled")
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self):
        try:
            backend = Path(__file__).with_name("backend") / "msr_gemini_backend.py"
            if not backend.exists():
                raise RuntimeError(f"Backend not found: {backend}")

            python = find_python()
            if not python:
                raise RuntimeError("Python 3 was not found. Install Python 3.10+.")

            env = os.environ.copy()
            env["GEMINI_PROJECT_ID"] = PROJECT_ID

            # Read local .env without displaying the secret in the log.
            env_file = Path(__file__).with_name(".env")
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        env["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("GEMINI_MODEL="):
                        env["GEMINI_MODEL"] = line.split("=", 1)[1].strip().strip('"').strip("'")

            if not env.get("GEMINI_API_KEY") or env["GEMINI_API_KEY"] == "PASTE_NEW_KEY_HERE":
                raise RuntimeError("Gemini API key is missing. Click Open .env and add a new key.")

            source = Path(self.media.get()).resolve()
            cmd = [python, str(backend), "--input", str(source), "--language", self.language.get()]
            self.set_status("Starting Gemini caption engine...", 5)
            self.write_log("Starting caption generation.")

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
            result = None
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("PROGRESS|"):
                    _, value, msg = line.split("|", 2)
                    self.set_status(msg, float(value))
                elif line.startswith("RESULT|"):
                    result = json.loads(line[7:])
                elif line.startswith("ERROR|"):
                    self.write_log(line)
                else:
                    self.write_log(line)

            code = proc.wait()
            if code != 0:
                raise RuntimeError("Gemini backend failed. See Diagnostics for the error.")
            if not result:
                raise RuntimeError("Backend finished without returning output files.")

            self.set_status("Captions generated.", 90)
            if self.import_resolve.get():
                if not self.resolve:
                    self._connect()
                if self.resolve:
                    timeline = None
                    try:
                        pm = self.resolve.GetProjectManager()
                        project = pm.GetCurrentProject()
                        timeline = project.GetCurrentTimeline() if project else None
                    except Exception:
                        pass
                    if timeline and callable(getattr(timeline, "CreateSubtitlesFromFile", None)):
                        ok = timeline.CreateSubtitlesFromFile(result["srt"])
                        self.write_log("Resolve subtitle-track import requested." if ok is not False else "Resolve rejected subtitle-track import.")
                    else:
                        self.write_log("Resolve subtitle API is unavailable; SRT is ready for manual import.")
                else:
                    self.write_log("Resolve is not connected; SRT is ready for manual import.")

            self.set_status("Completed.", 100)
            self.root.after(0, lambda: messagebox.showinfo(APP_NAME, f"Captions complete.\n\nSRT:\n{result['srt']}\n\nVTT:\n{result['vtt']}\n\nJSON:\n{result['json']}"))
        except Exception as exc:
            self.write_log("ERROR: " + str(exc))
            self.set_status("Failed.", 0)
            self.root.after(0, lambda: messagebox.showerror(APP_NAME, str(exc)))
        finally:
            self.root.after(0, lambda: self.generate.configure(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    Studio(root)
    root.mainloop()
