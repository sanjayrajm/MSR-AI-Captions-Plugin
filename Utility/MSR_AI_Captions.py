#!/usr/bin/env python3
"""MSR AI Captions - DaVinci Resolve Utility Script.

Place under Resolve's Fusion Scripts/Utility folder. The script launches a
separate Python worker for Gemini so Resolve's embedded Python environment
doesn't need the Google SDK.
"""
import json
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    resolve_api = resolve
except NameError:
    resolve_api = None

APP_NAME = "MSR AI Captions"
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
BACKEND = PLUGIN_ROOT / "backend" / "msr_gemini_backend.py"
LANGUAGES = [
    "Original", "Auto Detect", "English", "Tamil", "Hindi", "Telugu",
    "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi",
    "Urdu", "Spanish", "French", "German", "Italian", "Portuguese",
    "Arabic", "Japanese", "Korean", "Chinese", "Indonesian"
]


def current_timeline():
    if resolve_api is None:
        return None
    try:
        project = resolve_api.GetProjectManager().GetCurrentProject()
        return project.GetCurrentTimeline() if project else None
    except Exception:
        return None


def import_srt(path):
    timeline = current_timeline()
    if timeline is None:
        return False, "No active Resolve timeline."
    method = getattr(timeline, "CreateSubtitlesFromFile", None)
    if not callable(method):
        return False, "CreateSubtitlesFromFile is unavailable; import the generated SRT manually."
    try:
        result = method(str(path))
        return result is not False, "Subtitle track import requested."
    except Exception as exc:
        return False, f"Resolve subtitle import failed: {exc}"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x650")
        self.media = tk.StringVar()
        self.language = tk.StringVar(value="Original")
        self.import_resolve = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready.")
        self.progress = tk.DoubleVar()
        self.build()

    def build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="MSR AI CAPTIONS", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Gemini-powered multilingual captions for DaVinci Resolve").pack(anchor="w", pady=(0, 15))

        source = ttk.LabelFrame(outer, text="Media", padding=10)
        source.pack(fill="x", pady=5)
        ttk.Entry(source, textvariable=self.media).pack(side="left", fill="x", expand=True)
        ttk.Button(source, text="Browse", command=self.browse).pack(side="left", padx=(8, 0))

        settings = ttk.LabelFrame(outer, text="Caption Settings", padding=10)
        settings.pack(fill="x", pady=8)
        row = ttk.Frame(settings)
        row.pack(fill="x")
        ttk.Label(row, text="Caption language:").pack(side="left")
        ttk.Combobox(row, textvariable=self.language, values=LANGUAGES, state="readonly", width=22).pack(side="left", padx=8)
        ttk.Checkbutton(row, text="Import into current Resolve timeline", variable=self.import_resolve).pack(side="left", padx=8)

        algo = ttk.LabelFrame(outer, text="Smart Caption Algorithm", padding=10)
        algo.pack(fill="x", pady=8)
        ttk.Label(algo, text="42 chars/line • 2 lines • 9 words/caption • 0.8–5.5 sec • punctuation-aware splitting").pack(anchor="w")

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=16)
        self.generate = ttk.Button(buttons, text="GENERATE CAPTIONS", command=self.start)
        self.generate.pack(side="left")
        ttk.Button(buttons, text="Close", command=self.root.destroy).pack(side="left", padx=8)
        ttk.Progressbar(outer, variable=self.progress, maximum=100).pack(fill="x", pady=5)
        ttk.Label(outer, textvariable=self.status, wraplength=690).pack(anchor="w", pady=5)
        log_frame = ttk.LabelFrame(outer, text="Log", padding=7)
        log_frame.pack(fill="both", expand=True)
        self.logbox = tk.Text(log_frame, height=13, wrap="word", state="disabled")
        self.logbox.pack(fill="both", expand=True)

    def log(self, msg):
        def write():
            self.logbox.configure(state="normal")
            self.logbox.insert("end", msg + "\n")
            self.logbox.see("end")
            self.logbox.configure(state="disabled")
        self.root.after(0, write)

    def status_update(self, text, progress=None):
        def update():
            self.status.set(text)
            if progress is not None:
                self.progress.set(progress)
        self.root.after(0, update)

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select video or audio",
            filetypes=[("Media", "*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac"), ("All files", "*.*")]
        )
        if path:
            self.media.set(path)

    def find_python(self):
        for exe in ("py", "python"):
            try:
                p = subprocess.run([exe, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if p.returncode == 0:
                    return exe
            except Exception:
                pass
        raise RuntimeError("Python 3 was not found. Install Python 3.10+ and add it to PATH.")

    def start(self):
        if not self.media.get():
            messagebox.showwarning(APP_NAME, "Select a video or audio file.")
            return
        if not BACKEND.exists():
            messagebox.showerror(APP_NAME, f"Backend missing:\n{BACKEND}")
            return
        self.generate.configure(state="disabled")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            media = Path(self.media.get()).resolve()
            if not media.exists():
                raise FileNotFoundError(str(media))
            env = os.environ.copy()
            env["GEMINI_PROJECT_ID"] = env.get("GEMINI_PROJECT_ID", "774512798784")
            cmd = [self.find_python(), str(BACKEND), "--input", str(media), "--language", self.language.get()]
            self.status_update("Starting Gemini worker...", 5)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
            result = None
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.log(line)
                if line.startswith("PROGRESS|"):
                    _, value, msg = line.split("|", 2)
                    try:
                        self.status_update(msg, float(value))
                    except ValueError:
                        pass
                elif line.startswith("RESULT|"):
                    result = json.loads(line[7:])
            if proc.wait() != 0:
                raise RuntimeError("Gemini worker failed. Check the log for details.")
            if not result:
                raise RuntimeError("Gemini worker produced no output paths.")

            resolve_msg = "Resolve import disabled."
            if self.import_resolve.get():
                ok, resolve_msg = import_srt(result["srt"])
                self.log(resolve_msg)
            self.status_update("Completed.", 100)
            message = (f"SRT:\n{result['srt']}\n\nVTT:\n{result['vtt']}\n\n"
                       f"JSON:\n{result['json']}\n\nDetected language: {result['detected_language']}\n\n{resolve_msg}")
            self.root.after(0, lambda: messagebox.showinfo(APP_NAME, message))
        except Exception as exc:
            self.log("ERROR: " + str(exc))
            self.status_update("Failed.", 0)
            self.root.after(0, lambda: messagebox.showerror(APP_NAME, str(exc)))
        finally:
            self.root.after(0, lambda: self.generate.configure(state="normal"))


def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()


main()
