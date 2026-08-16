from __future__ import annotations

import json
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config import DEFAULT_MODEL, PROJECT_ID, ENV_FILE, gemini_configured, load_env_file, find_python, resolve_paths
from resolve_overlay import add_text_plus_overlays

APP_NAME = "MSR AI Captions Studio"
LANGUAGES = [
    "Original", "Auto Detect", "English", "Tamil", "Hindi", "Telugu",
    "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi",
    "Urdu", "Spanish", "French", "German", "Italian", "Portuguese",
    "Arabic", "Japanese", "Korean", "Chinese", "Indonesian"
]


def load_resolve_module():
    try:
        import DaVinciResolveScript as dvr
        return dvr
    except Exception:
        pass

    import sys
    for path in resolve_paths():
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
            try:
                import DaVinciResolveScript as dvr
                return dvr
            except Exception:
                pass
    return None


def connect_resolve():
    dvr = load_resolve_module()
    if dvr is None:
        return None, "Resolve scripting module was not found."
    try:
        app = dvr.scriptapp("Resolve")
        if app is None:
            return None, "Resolve rejected the external scripting connection."
        return app, "Connected to DaVinci Resolve."
    except Exception as exc:
        return None, f"Resolve connection error: {exc}"


def resolve_info(app):
    result = {"version": "Unknown", "project": "No project", "timeline": "No timeline"}
    try:
        result["version"] = app.GetVersionString()
    except Exception:
        pass
    try:
        project = app.GetProjectManager().GetCurrentProject()
        if project:
            result["project"] = project.GetName()
            timeline = project.GetCurrentTimeline()
            if timeline:
                result["timeline"] = timeline.GetName()
    except Exception:
        pass
    return result


class Studio:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1080x760")
        self.root.minsize(920, 650)
        self.resolve = None
        self.media = tk.StringVar()
        self.language = tk.StringVar(value="Original")
        self.overlay_mode = tk.StringVar(value="Text+ Video Overlay")
        self.resolve_status = tk.StringVar(value="Resolve: checking...")
        self.project_status = tk.StringVar(value="Project: —")
        self.timeline_status = tk.StringVar(value="Timeline: —")
        self.gemini_status = tk.StringVar(value="Gemini: checking...")
        self.python_status = tk.StringVar(value="Python: checking...")
        self.status = tk.StringVar(value="Starting...")
        self.progress = tk.DoubleVar(value=0)
        self.auto_import = tk.BooleanVar(value=True)
        self.installing = False
        self.build_ui()
        self.root.after(150, self.startup_check)

    def build_ui(self):
        try:
            ttk.Style(self.root).theme_use("vista")
        except Exception:
            pass

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="MSR AI CAPTIONS", font=("Segoe UI", 25, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Gemini transcription → smart timing → real captions directly over your Resolve video",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        conn = ttk.LabelFrame(outer, text="DaVinci Resolve", padding=12)
        conn.pack(fill="x", pady=(18, 8))
        r1 = ttk.Frame(conn)
        r1.pack(fill="x")
        ttk.Label(r1, textvariable=self.resolve_status).pack(side="left")
        ttk.Button(r1, text="Connect / Reconnect", command=self.connect_async).pack(side="right")
        ttk.Button(r1, text="Check Permissions", command=self.permissions).pack(side="right", padx=8)
        ttk.Button(r1, text="Repair Setup", command=self.repair_setup).pack(side="right", padx=8)

        r2 = ttk.Frame(conn)
        r2.pack(fill="x", pady=(9, 0))
        ttk.Label(r2, textvariable=self.project_status).pack(side="left", padx=(0, 24))
        ttk.Label(r2, textvariable=self.timeline_status).pack(side="left")

        ai = ttk.LabelFrame(outer, text="Gemini / Automatic Configuration", padding=12)
        ai.pack(fill="x", pady=8)
        ttk.Label(ai, textvariable=self.gemini_status).pack(side="left")
        ttk.Label(ai, textvariable=self.python_status).pack(side="left", padx=25)
        ttk.Button(ai, text="Configure .env", command=self.open_env).pack(side="right")

        job = ttk.LabelFrame(outer, text="Caption Generation", padding=12)
        job.pack(fill="x", pady=8)
        row = ttk.Frame(job)
        row.pack(fill="x")
        ttk.Label(row, text="Video / Audio:").pack(side="left")
        ttk.Entry(row, textvariable=self.media).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=self.browse).pack(side="left")

        opts = ttk.Frame(job)
        opts.pack(fill="x", pady=(12, 0))
        ttk.Label(opts, text="Language:").pack(side="left")
        ttk.Combobox(opts, textvariable=self.language, values=LANGUAGES, state="readonly", width=19).pack(side="left", padx=8)
        ttk.Label(opts, text="Output:").pack(side="left", padx=(20, 5))
        ttk.Combobox(opts, textvariable=self.overlay_mode, values=["Text+ Video Overlay", "SRT Only"], state="readonly", width=22).pack(side="left")
        ttk.Checkbutton(opts, text="Put captions directly on timeline", variable=self.auto_import).pack(side="left", padx=18)

        alg = ttk.LabelFrame(outer, text="Caption Engine", padding=10)
        alg.pack(fill="x", pady=8)
        ttk.Label(
            alg,
            text="Gemini timestamps + Python optimization • 42 chars/line • 2 lines • 9 words • 0.8–5.5 sec • punctuation-aware • reading-speed control",
            wraplength=900,
        ).pack(anchor="w")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=16)
        self.generate = ttk.Button(actions, text="GENERATE & OVERLAY CAPTIONS", command=self.generate_async)
        self.generate.pack(side="left")
        ttk.Button(actions, text="Refresh", command=self.startup_check).pack(side="left", padx=8)
        ttk.Button(actions, text="Open Output", command=self.open_output).pack(side="left")

        ttk.Progressbar(outer, variable=self.progress, maximum=100).pack(fill="x")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(7, 5))

        log_frame = ttk.LabelFrame(outer, text="Diagnostics", padding=8)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, wrap="word", height=14, state="disabled")
        self.log.pack(fill="both", expand=True)

    def write_log(self, text):
        def action():
            self.log.configure(state="normal")
            self.log.insert("end", text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, action)

    def set_status(self, text, value=None):
        def action():
            self.status.set(text)
            if value is not None:
                self.progress.set(value)
        self.root.after(0, action)

    def startup_check(self):
        self.write_log("Running automatic configuration check...")
        self.root.after(100, self._check_config)
        self.connect_async()

    def _check_config(self):
        try:
            load_env_file()
            if gemini_configured():
                self.gemini_status.set("Gemini: CONFIGURED")
                self.write_log("Gemini .env configuration detected.")
            else:
                self.gemini_status.set("Gemini: API KEY REQUIRED")
                self.write_log(f"Create a new Gemini key in: {ENV_FILE}")
        except Exception as exc:
            self.gemini_status.set("Gemini: configuration error")
            self.write_log(str(exc))

        try:
            py = find_python()
            self.python_status.set("Python: " + " ".join(py))
        except Exception as exc:
            self.python_status.set("Python: NOT FOUND")
            self.write_log(str(exc))

    def connect_async(self):
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        self.set_status("Connecting to DaVinci Resolve...", 5)
        app, message = connect_resolve()
        self.write_log(message)
        if not app:
            self.resolve = None
            self.root.after(0, lambda: self.resolve_status.set("Resolve: NOT CONNECTED"))
            self.root.after(0, lambda: self.project_status.set("Project: —"))
            self.root.after(0, lambda: self.timeline_status.set("Timeline: —"))
            self.set_status("Resolve connection unavailable.", 0)
            return

        self.resolve = app
        info = resolve_info(app)
        self.root.after(0, lambda: self.resolve_status.set(f"Resolve: CONNECTED • {info['version']}"))
        self.root.after(0, lambda: self.project_status.set(f"Project: {info['project']}"))
        self.root.after(0, lambda: self.timeline_status.set(f"Timeline: {info['timeline']}"))
        self.write_log(f"Project: {info['project']}")
        self.write_log(f"Timeline: {info['timeline']}")
        self.set_status("Resolve connected.", 10)

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select video or audio",
            filetypes=[
                ("Video/Audio", "*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.media.set(path)

    def open_env(self):
        from config import ensure_env_file
        env = ensure_env_file()
        try:
            os.startfile(str(env))
        except Exception:
            messagebox.showinfo(APP_NAME, f"Edit this file:\n{env}")

    def permissions(self):
        win = tk.Toplevel(self.root)
        win.title("MSR AI Captions — Resolve Permission Check")
        win.geometry("760x570")
        win.transient(self.root)

        outer = ttk.Frame(win, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Resolve permission / connection check", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="The plugin cannot silently change Resolve's security permission. It can detect the connection and guide you to the correct setting.",
            wraplength=700,
        ).pack(anchor="w", pady=(7, 14))

        steps = [
            "1. Use DaVinci Resolve Studio for external application control.",
            "2. Open DaVinci Resolve → Preferences → System → General.",
            "3. Find External Scripting Using.",
            "4. Select Local for this same Windows PC.",
            "5. Click Save, then restart DaVinci Resolve.",
            "6. Open a project and a timeline.",
            "7. Start MSR AI Captions again and press Connect / Reconnect.",
        ]
        for s in steps:
            ttk.Label(outer, text=s, wraplength=700).pack(anchor="w", pady=4)

        ttk.Separator(outer).pack(fill="x", pady=12)
        ttk.Label(
            outer,
            text=(
                "Windows scripting module: " + 
                (str(next((p for p in resolve_paths() if p.exists()), "NOT FOUND")))
            ),
            wraplength=700,
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text="Current connection: " + ("CONNECTED" if self.resolve else "NOT CONNECTED"),
        ).pack(anchor="w", pady=6)
        ttk.Button(outer, text="Connect Again", command=lambda: (win.destroy(), self.connect_async())).pack(anchor="e", pady=8)

    def repair_setup(self):
        if self.installing:
            return
        self.installing = True
        self.set_status("Checking/installing Python dependencies...", 5)
        threading.Thread(target=self._repair, daemon=True).start()

    def _repair(self):
        try:
            python = find_python()
            req = Path(__file__).with_name("requirements.txt")
            if not req.exists():
                raise RuntimeError("requirements.txt was not found.")
            self.write_log("Installing/updating Python dependencies...")
            p = subprocess.run(
                python + ["-m", "pip", "install", "-r", str(req)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.write_log(p.stdout[-6000:])
            if p.returncode != 0:
                raise RuntimeError("Dependency installation failed. See Diagnostics.")
            self.set_status("Setup repaired successfully.", 15)
            self.root.after(0, self._check_config)
            self.root.after(0, lambda: messagebox.showinfo(APP_NAME, "Python dependencies are ready."))
        except Exception as exc:
            self.write_log("SETUP ERROR: " + str(exc))
            self.set_status("Setup failed.", 0)
            self.root.after(0, lambda: messagebox.showerror(APP_NAME, str(exc)))
        finally:
            self.installing = False

    def generate_async(self):
        if not self.media.get():
            messagebox.showwarning(APP_NAME, "Select a video/audio file first.")
            return
        if not Path(self.media.get()).exists():
            messagebox.showwarning(APP_NAME, "The selected file does not exist.")
            return
        if not gemini_configured():
            self.open_env()
            messagebox.showwarning(APP_NAME, "Add your NEW Gemini API key to .env, save it, then click Generate again.")
            return
        if self.auto_import.get() and self.resolve is None:
            self.connect_async()
            messagebox.showwarning(APP_NAME, "Resolve is not connected yet. Set External Scripting Using to Local, restart Resolve, then press Connect / Reconnect.")
            return

        self.generate.configure(state="disabled")
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self):
        try:
            root = Path(__file__).resolve().parent
            backend = root / "backend" / "msr_gemini_backend.py"
            if not backend.exists():
                raise RuntimeError(f"Gemini backend not found: {backend}")

            python = find_python()
            env = os.environ.copy()
            cfg = load_env_file()
            env["GEMINI_PROJECT_ID"] = cfg.get("GEMINI_PROJECT_ID", PROJECT_ID)
            env["GEMINI_MODEL"] = cfg.get("GEMINI_MODEL", DEFAULT_MODEL)
            if cfg.get("GEMINI_API_KEY"):
                env["GEMINI_API_KEY"] = cfg["GEMINI_API_KEY"]

            source = Path(self.media.get()).resolve()
            cmd = python + [str(backend), "--input", str(source), "--language", self.language.get()]
            self.set_status("Gemini caption engine starting...", 5)
            self.write_log("Generating transcript. Caption text will not be shown in this dashboard.")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=str(root),
            )
            result = None
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("PROGRESS|"):
                    _, value, msg = line.split("|", 2)
                    try:
                        self.set_status(msg, float(value))
                    except Exception:
                        pass
                elif line.startswith("RESULT|"):
                    result = json.loads(line[7:])
                else:
                    self.write_log(line)

            code = proc.wait()
            if code != 0:
                raise RuntimeError("Gemini backend failed. Check Diagnostics.")
            if not result:
                raise RuntimeError("Gemini backend returned no result.")

            self.set_status("Transcript ready. Preparing Resolve overlay...", 88)

            with open(result["json"], "r", encoding="utf-8") as f:
                payload = json.load(f)
            captions = payload.get("captions", [])

            overlay_message = "SRT generated only."
            if self.auto_import.get() and self.overlay_mode.get() == "Text+ Video Overlay":
                if not self.resolve:
                    self.resolve, _ = connect_resolve()
                if not self.resolve:
                    raise RuntimeError("Resolve disconnected before overlay creation.")
                overlay = add_text_plus_overlays(self.resolve, captions)
                overlay_message = overlay.get("message", "Overlay finished.")
                self.write_log(overlay_message)
                if not overlay.get("ok"):
                    raise RuntimeError(
                        "Resolve could not create the Text+ overlay. "
                        "The SRT was still created successfully. See Diagnostics."
                    )

            self.set_status("Complete — captions are on the timeline.", 100)
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    APP_NAME,
                    "Caption generation complete.\n\n"
                    + overlay_message
                    + "\n\nSRT:\n"
                    + result["srt"]
                    + "\n\nThe dashboard does not display the captions; the Text+ captions are placed on the Resolve timeline."
                ),
            )
        except Exception as exc:
            self.write_log("ERROR: " + str(exc))
            self.set_status("Failed.", 0)
            self.root.after(0, lambda: messagebox.showerror(APP_NAME, str(exc)))
        finally:
            self.root.after(0, lambda: self.generate.configure(state="normal"))

    def open_output(self):
        if not self.media.get():
            messagebox.showinfo(APP_NAME, "Select media first.")
            return
        folder = Path(self.media.get()).resolve().parent / "_msr_ai_captions"
        if folder.exists():
            os.startfile(str(folder))
        else:
            messagebox.showinfo(APP_NAME, "Generate captions first. The output folder will be created beside your media.")


def main():
    root = tk.Tk()
    Studio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
