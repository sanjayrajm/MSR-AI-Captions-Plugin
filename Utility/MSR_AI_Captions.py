"""MSR AI Captions - native DaVinci Resolve Workspace script.

This version does NOT launch a separate Tkinter application and does NOT ask
for a video import. The script runs inside Resolve, reads the active project
and timeline, renders only the timeline audio to a temporary WAV, sends that
WAV to the hidden Gemini worker, writes an SRT, and creates editable Text+
overlays on the active timeline.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

try:
    import DaVinciResolveScript as dvr
except Exception:
    dvr = None

# Resolve injects Fusion globals when this script is run from Workspace.
try:
    import bmd  # type: ignore
except Exception:
    bmd = None

APP_NAME = "MSR AI Captions"
LANGUAGES = [
    "Auto Detect", "Original", "English", "Tamil", "Hindi", "Telugu",
    "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi",
    "Urdu", "Spanish", "French", "German", "Italian", "Portuguese",
    "Arabic", "Japanese", "Korean", "Chinese", "Indonesian"
]


def get_resolve():
    if dvr is None:
        raise RuntimeError("DaVinciResolveScript could not be loaded inside Resolve.")
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Resolve did not provide a scripting object. Check Preferences > System > General > External Scripting Using.")
    return resolve


def get_ui(resolve):
    fusion = resolve.Fusion()
    ui = getattr(fusion, "UIManager", None)
    if ui is None:
        raise RuntimeError("Fusion UIManager is unavailable. This MSR interface requires DaVinci Resolve Studio.")
    dispatcher = (bmd.UIDispatcher(ui) if bmd is not None else None)
    if dispatcher is None:
        raise RuntimeError("DaVinci Resolve UIDispatcher is unavailable.")
    return ui, dispatcher


def get_worker_python():
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
    if local.exists():
        matches = sorted(local.glob("Python*/pythonw.exe"), reverse=True)
        if matches:
            return matches[0]
        matches = sorted(local.glob("Python*/python.exe"), reverse=True)
        if matches:
            return matches[0]
    # The Windows launcher is intentionally invoked without a console.
    for version in ("3.12", "3.11", "3.10"):
        try:
            p = subprocess.run(
                ["py", f"-{version}", "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if p.returncode == 0:
                exe = Path(p.stdout.strip())
                pw = exe.with_name("pythonw.exe")
                if pw.exists():
                    return pw
        except Exception:
            pass
    raise RuntimeError("Normal Windows Python/pythonw.exe was not found.")


def project_and_timeline(resolve):
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if not project:
        raise RuntimeError("Open a DaVinci Resolve project first.")
    timeline = project.GetCurrentTimeline()
    if not timeline:
        raise RuntimeError("Open a timeline first. MSR AI Captions never imports a video; it uses the current Resolve timeline.")
    return project, timeline


def timeline_fps(timeline):
    for key in ("timelineFrameRate", "timelineFrameRateFloat"):
        try:
            value = timeline.GetSetting(key)
            if value:
                return float(value)
        except Exception:
            pass
    return 24.0


def render_timeline_audio(project, timeline, out_dir, log):
    """Use Resolve's own render engine to create a WAV of the current timeline."""
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = project.GetRenderFormats() or {}
    wav_format = None
    for fmt, ext in formats.items():
        if str(fmt).lower() in ("wav", "wave") or str(ext).lower() in ("wav", "wave"):
            wav_format = fmt
            break
    if not wav_format:
        raise RuntimeError("Resolve does not expose a WAV render format on this installation. Enable the Audio Only/Wave render support in Resolve.")

    codecs = project.GetRenderCodecs(wav_format) or {}
    codec = None
    for description, value in codecs.items():
        text = (str(description) + " " + str(value)).lower()
        if "pcm" in text or "linear" in text or "wave" in text:
            codec = value
            break
    if codec is None and codecs:
        codec = next(iter(codecs.values()))
    if codec is None:
        raise RuntimeError("No WAV audio codec is available in Resolve.")

    previous = None
    try:
        previous = project.GetCurrentRenderFormatAndCodec()
    except Exception:
        pass

    project.SetCurrentRenderFormatAndCodec(wav_format, codec)
    name = "msr_timeline_audio"
    settings = {
        "SelectAllFrames": True,
        "TargetDir": str(out_dir),
        "CustomName": name,
        "ExportVideo": False,
        "ExportAudio": True,
        "AudioSampleRate": 16000,
        "AudioBitDepth": 16,
    }
    if not project.SetRenderSettings(settings):
        raise RuntimeError("Resolve rejected the temporary audio render settings.")

    job = project.AddRenderJob()
    if not job:
        raise RuntimeError("Resolve could not add the temporary audio render job.")
    log("Resolve is rendering timeline audio only — no video is imported or exported.")
    try:
        if not project.StartRendering(False):
            raise RuntimeError("Resolve could not start the temporary audio render.")
        while project.IsRenderingInProgress():
            time.sleep(0.4)
    finally:
        try:
            project.DeleteRenderJob(job)
        except Exception:
            pass
        if previous and previous.get("format") and previous.get("codec"):
            try:
                project.SetCurrentRenderFormatAndCodec(previous["format"], previous["codec"])
            except Exception:
                pass

    candidates = list(out_dir.glob("msr_timeline_audio.*"))
    wav = next((p for p in candidates if p.suffix.lower() == ".wav"), None)
    if wav is None:
        raise RuntimeError("Resolve completed the audio render, but no WAV file was produced.")
    return wav


def launch_worker(root, wav, language, out_dir, log):
    worker = root / "backend" / "msr_gemini_backend.py"
    if not worker.exists():
        raise RuntimeError(f"Gemini worker is missing: {worker}")
    python = get_worker_python()
    env = os.environ.copy()
    env["MSR_AI_CAPTIONS_ROOT"] = str(root)
    cmd = [str(python), str(worker), "--audio", str(wav), "--language", language, "--output-dir", str(out_dir)]
    log("Starting hidden Gemini worker. No Command Prompt window is used.")
    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
    )
    result = None
    for line in proc.stdout or []:
        line = line.strip()
        if line.startswith("PROGRESS|"):
            parts = line.split("|", 2)
            if len(parts) == 3:
                log(parts[2])
        elif line.startswith("RESULT|"):
            try:
                result = json.loads(line.split("|", 1)[1])
            except Exception:
                pass
        elif line:
            log(line)
    code = proc.wait()
    if code != 0 or not result:
        raise RuntimeError("Gemini worker failed. Open Resolve > Workspace > Console to see the Python error, or inspect the MSR diagnostics log.")
    return result


def create_overlays(resolve, captions, log):
    # Load the overlay module relative to this script without relying on
    # site-packages or a separate GUI application.
    root = Path(__file__).resolve().parents[1]
    import importlib.util
    spec = importlib.util.spec_from_file_location("msr_resolve_overlay", root / "resolve_overlay.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("resolve_overlay.py could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.add_text_plus_overlays(resolve, captions)
    log(result.get("message", "Text+ overlay operation finished."))
    return result


def write_ui(win, ui, key, value):
    try:
        win.Find(key).Text = value
    except Exception:
        try:
            win[key].Text = value
        except Exception:
            pass


def main():
    resolve = get_resolve()
    project, timeline = project_and_timeline(resolve)
    ui, disp = get_ui(resolve)
    root = Path(__file__).resolve().parents[1]

    state = {"busy": False}

    win = disp.AddWindow(
        {
            "ID": "MSRAICaptions",
            "TargetID": "MSRAICaptions",
            "WindowTitle": "MSR AI Captions",
            "Geometry": [260, 180, 760, 620],
            "Spacing": 8,
        },
        ui.VGroup(
            [
                ui.Label({"Text": "MSR AI CAPTIONS", "Font": {"PixelSize": 24}, "Alignment": {"AlignHCenter": True}}),
                ui.Label({"ID": "subtitle", "Text": "Gemini transcription • smart captions • Resolve timeline overlays", "Alignment": {"AlignHCenter": True}}),
                ui.HGroup([
                    ui.Label({"ID": "resolveInfo", "Text": f"Resolve Studio • Project: {project.GetName()} • Timeline: {timeline.GetName()}", "Weight": 1}),
                    ui.Button({"ID": "refresh", "Text": "Refresh"}),
                ]),
                ui.Separator({"Orientation": "Horizontal"}),
                ui.Label({"Text": "This tool uses the CURRENT Resolve timeline. No video/image import is required."}),
                ui.HGroup([
                    ui.Label({"Text": "Language:", "Weight": 0}),
                    ui.ComboBox({"ID": "language", "Weight": 1}),
                    ui.Label({"Text": "Output:", "Weight": 0}),
                    ui.ComboBox({"ID": "output", "Weight": 1}),
                ]),
                ui.HGroup([
                    ui.CheckBox({"ID": "textplus", "Text": "Create editable Text+ overlays", "Checked": True, "Weight": 1}),
                    ui.CheckBox({"ID": "srt", "Text": "Create SRT file", "Checked": True, "Weight": 1}),
                ]),
                ui.Label({"Text": "Caption engine: 42 chars/line • 2 lines • punctuation-aware • reading-speed control"}),
                ui.Button({"ID": "generate", "Text": "GENERATE CAPTIONS FROM CURRENT TIMELINE", "MinimumSize": [0, 46]}),
                ui.ProgressBar({"ID": "progress", "Minimum": 0, "Maximum": 100, "Value": 0}),
                ui.Label({"ID": "status", "Text": "Ready."}),
                ui.Label({"Text": "Diagnostics"}),
                ui.TextEdit({"ID": "log", "ReadOnly": True, "MinimumSize": [0, 260]}),
            ]
        ),
    )

    for lang in LANGUAGES:
        win.Find("language").AddItem(lang)
    win.Find("language").CurrentIndex = 0
    win.Find("output").AddItem("Text+ + SRT")
    win.Find("output").AddItem("SRT only")
    win.Find("output").CurrentIndex = 0

    def log(message):
        try:
            current = win.Find("log").PlainText
            win.Find("log").PlainText = current + str(message) + "\n"
        except Exception:
            pass

    def set_status(text, progress=None):
        write_ui(win, ui, "status", text)
        if progress is not None:
            try:
                win.Find("progress").Value = progress
            except Exception:
                pass

    def refresh(ev=None):
        try:
            p, t = project_and_timeline(resolve)
            write_ui(win, ui, "resolveInfo", f"Resolve Studio • Project: {p.GetName()} • Timeline: {t.GetName()}")
            set_status("Ready — current timeline detected.", 0)
        except Exception as exc:
            write_ui(win, ui, "resolveInfo", "Resolve / timeline unavailable")
            set_status(str(exc), 0)

    def generate(ev=None):
        if state["busy"]:
            return
        try:
            p, t = project_and_timeline(resolve)
        except Exception as exc:
            set_status(str(exc), 0)
            return
        state["busy"] = True
        win.Find("generate").Enabled = False
        language = win.Find("language").CurrentText
        do_text = bool(win.Find("textplus").Checked)
        do_srt = bool(win.Find("srt").Checked)
        log(f"Project: {p.GetName()}")
        log(f"Timeline: {t.GetName()}")
        log("No external video/image import is being used.")

        def work():
            try:
                temp = Path(tempfile.gettempdir()) / "MSR_AI_Captions" / (t.GetUniqueId() if hasattr(t, "GetUniqueId") else "current")
                set_status("Rendering timeline audio...", 10)
                wav = render_timeline_audio(p, t, temp, log)
                set_status("Sending timeline audio to Gemini...", 40)
                result = launch_worker(root, wav, language, temp, log)
                set_status("SRT created and caption algorithm complete...", 85)
                if do_text:
                    overlay_result = create_overlays(resolve, result.get("captions", []), log)
                    if overlay_result.get("created", 0) == 0:
                        raise RuntimeError(overlay_result.get("message", "No Text+ overlays were created."))
                if do_srt:
                    log("SRT: " + str(result.get("srt", "")))
                log("Detected language: " + str(result.get("detected_language", "unknown")))
                set_status("DONE — captions were created on the current Resolve timeline.", 100)
            except Exception as exc:
                log("ERROR: " + str(exc))
                set_status("Failed — see Diagnostics.", 0)
            finally:
                state["busy"] = False
                try:
                    win.Find("generate").Enabled = True
                except Exception:
                    pass

        threading.Thread(target=work, daemon=True).start()

    def close(ev=None):
        disp.ExitLoop()

    win.On.generate.Clicked = generate
    win.On.refresh.Clicked = refresh
    win.On.MSRAICaptions.Close = close
    win.Show()
    refresh()
    disp.RunLoop()
    win.Hide()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # A native Resolve message box is preferable to a disappearing CMD.
        try:
            resolve = get_resolve()
            fusion = resolve.Fusion()
            ui = fusion.UIManager
            disp = bmd.UIDispatcher(ui)
            win = disp.AddWindow({"ID": "MSRError", "WindowTitle": "MSR AI Captions Error"}, ui.VGroup([
                ui.Label({"Text": str(exc)}),
                ui.Button({"ID": "ok", "Text": "OK"}),
            ]))
            win.On.ok.Clicked = lambda ev: disp.ExitLoop()
            win.Show()
            disp.RunLoop()
            win.Hide()
        except Exception:
            print("MSR AI Captions ERROR:", exc)
