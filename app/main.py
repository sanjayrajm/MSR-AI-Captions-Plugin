from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import QObject, QThread, Signal, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QStackedWidget, QFrame
)

from resolve_bridge import ResolveBridge
from audio import extract_audio
from gemini_transcriber import GeminiTranscriber
from srt import write_srt

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
ENV_FILE = PROJECT_ROOT / ".env"
OUTPUT_DIR = PROJECT_ROOT / "output"
WORK_DIR = ROOT / "work"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(ENV_FILE)


class Worker(QObject):
    progress = Signal(int, str)
    done = Signal(str, object, object)
    error = Signal(str)

    def __init__(self, bridge, clip, language, output):
        super().__init__()
        self.bridge = bridge
        self.clip = clip
        self.language = language
        self.output = output

    def run(self):
        try:
            source = Path(self.clip["path"])
            if not source.exists():
                raise FileNotFoundError(f"Resolve media file was not found:\n{source}")

            self.progress.emit(10, "Extracting audio from the Resolve video...")
            audio = WORK_DIR / "current_clip.wav"
            if audio.exists():
                try:
                    audio.unlink()
                except Exception:
                    pass
            extract_audio(str(source), audio)
            if not audio.exists():
                raise RuntimeError("Audio extraction completed but WAV was not created.")

            self.progress.emit(30, "Transcribing audio with Gemini...")
            segments = GeminiTranscriber().transcribe(str(audio), self.language)
            if not segments:
                raise RuntimeError("Gemini returned an empty transcript.")

            clean = []
            for s in segments:
                try:
                    start = max(0.0, float(s.get("start", 0)))
                    end = max(start, float(s.get("end", start)))
                    text = str(s.get("text", "")).strip()
                    if text:
                        clean.append({"start": start, "end": end, "text": text})
                except Exception:
                    continue
            if not clean:
                raise RuntimeError("No valid transcript segments were returned.")

            self.progress.emit(65, "Writing timestamped SRT...")
            output = Path(self.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            srt_path = str(Path(write_srt(clean, output)).resolve())
            if not Path(srt_path).exists():
                raise RuntimeError(f"SRT was not created:\n{srt_path}")

            self.progress.emit(82, "Importing SRT into Resolve Media Pool...")
            placement = self.bridge.import_and_place_srt(srt_path, self.clip)
            if not placement.get("success"):
                raise RuntimeError(
                    "SRT was generated, but Resolve could not place it on the timeline.\n\n"
                    + placement.get("error", "Unknown Resolve error.")
                )

            self.progress.emit(100, "SRT imported and captions added to the Resolve timeline.")
            self.done.emit(srt_path, clean, placement)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}")


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSR AI Captions 2.1")
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.bridge = ResolveBridge()
        self.clips = []
        self.worker_thread = None
        self.worker = None
        self.build_ui()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_silent)
        self.timer.start(3000)

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        side_frame = QFrame()
        side_frame.setObjectName("Sidebar")
        side_frame.setFixedWidth(240)
        side = QVBoxLayout(side_frame)
        side.setContentsMargins(20, 25, 20, 20)

        brand = QLabel("MSR")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        sub = QLabel("AI CAPTIONS")
        sub.setObjectName("BrandSub")
        side.addWidget(sub)
        ver = QLabel("Version 2.1")
        ver.setObjectName("Version")
        side.addWidget(ver)
        side.addSpacing(25)

        self.nav = []
        for text, index in [("Dashboard", 0), ("Generate Captions", 1), ("Transcript", 2), ("Settings", 3)]:
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.clicked.connect(lambda _, i=index: self.navigate(i))
            side.addWidget(b)
            self.nav.append(b)
        side.addStretch()
        self.resolve_status = QLabel("● RESOLVE CHECKING")
        self.resolve_status.setObjectName("ResolveStatus")
        side.addWidget(self.resolve_status)
        main.addWidget(side_frame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 25, 30, 25)
        self.title = QLabel("MSR AI Captions")
        self.title.setObjectName("HeaderTitle")
        content_layout.addWidget(self.title)
        self.subtitle = QLabel("AI-powered captions directly from your DaVinci Resolve timeline")
        self.subtitle.setObjectName("HeaderSubtitle")
        content_layout.addWidget(self.subtitle)
        content_layout.addSpacing(18)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.dashboard_page())
        self.pages.addWidget(self.generate_page())
        self.pages.addWidget(self.transcript_page())
        self.pages.addWidget(self.settings_page())
        content_layout.addWidget(self.pages, 1)
        main.addWidget(content, 1)
        self.navigate(0)

    def dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        card = QFrame(); card.setObjectName("Card")
        cl = QVBoxLayout(card)
        self.resolve_card = QLabel("DaVinci Resolve: Checking...")
        self.resolve_card.setObjectName("CardTitle")
        cl.addWidget(self.resolve_card)
        layout.addWidget(card)

        row = QHBoxLayout()
        self.project_card = self.info_card("PROJECT", "Not connected")
        self.timeline_card = self.info_card("TIMELINE", "Not connected")
        self.media_card = self.info_card("MEDIA", "0 clips")
        row.addWidget(self.project_card); row.addWidget(self.timeline_card); row.addWidget(self.media_card)
        layout.addLayout(row)

        go = QPushButton("GENERATE CAPTIONS")
        go.setObjectName("Primary")
        go.setMinimumHeight(52)
        go.clicked.connect(lambda: self.navigate(1))
        layout.addWidget(go)

        refresh = QPushButton("REFRESH RESOLVE")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)

        workflow = QFrame(); workflow.setObjectName("Card")
        wl = QVBoxLayout(workflow)
        t = QLabel("CAPTION WORKFLOW"); t.setObjectName("Section")
        wl.addWidget(t)
        for s in [
            "1. Read active Resolve project and timeline",
            "2. Detect video already present in the timeline",
            "3. Extract audio without importing video into MSR",
            "4. Transcribe with Gemini",
            "5. Generate timestamped SRT in output/",
            "6. Import SRT into Resolve Media Pool",
            "7. Create/reuse subtitle track",
            "8. Place captions at the selected video's timeline position",
        ]:
            wl.addWidget(QLabel(s))
        layout.addWidget(workflow)
        layout.addStretch()
        return page

    def info_card(self, title, value):
        card = QFrame(); card.setObjectName("Card")
        l = QVBoxLayout(card)
        a = QLabel(title); a.setObjectName("InfoTitle")
        b = QLabel(value); b.setObjectName("InfoValue"); b.setWordWrap(True)
        l.addWidget(a); l.addWidget(b)
        card.value_label = b
        return card

    def generate_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        h = QLabel("Generate Captions"); h.setObjectName("PageTitle"); layout.addWidget(h)
        layout.addWidget(QLabel("Select a video already present in your current DaVinci Resolve timeline."))
        self.clip_list = QListWidget(); self.clip_list.setMinimumHeight(150); layout.addWidget(self.clip_list)

        label = QLabel("Caption Language"); label.setObjectName("FieldLabel"); layout.addWidget(label)
        self.language = QComboBox()
        self.language.addItems(["Auto Detect", "English", "Tamil", "Hindi", "Telugu", "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Spanish", "French", "German", "Japanese", "Korean"])
        layout.addWidget(self.language)

        label = QLabel("SRT Output"); label.setObjectName("FieldLabel"); layout.addWidget(label)
        row = QHBoxLayout()
        self.output = QLabel(str(OUTPUT_DIR / "MSR_AI_Captions.srt")); self.output.setObjectName("Output")
        choose = QPushButton("Choose SRT"); choose.clicked.connect(self.choose_output)
        row.addWidget(self.output, 1); row.addWidget(choose); layout.addLayout(row)

        self.generate = QPushButton("GENERATE CAPTIONS")
        self.generate.setObjectName("Primary")
        self.generate.setMinimumHeight(55)
        self.generate.clicked.connect(self.generate_captions)
        layout.addWidget(self.generate)
        self.progress = QProgressBar(); self.progress.setValue(0); layout.addWidget(self.progress)
        self.message = QLabel("Ready."); self.message.setObjectName("Message"); self.message.setWordWrap(True); layout.addWidget(self.message)
        layout.addStretch()
        return page

    def transcript_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        h = QLabel("Transcript"); h.setObjectName("PageTitle"); layout.addWidget(h)
        self.transcript = QTextEdit(); self.transcript.setReadOnly(True); layout.addWidget(self.transcript)
        return page

    def settings_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        h = QLabel("Settings"); h.setObjectName("PageTitle"); layout.addWidget(h)
        self.gemini_info = QLabel(); self.gemini_info.setWordWrap(True); layout.addWidget(self.gemini_info)
        layout.addWidget(QLabel(f"Environment file:\n{ENV_FILE}\n\nOutput folder:\n{OUTPUT_DIR}"))
        layout.addWidget(QLabel("MSR uses the active Resolve timeline. Videos are not imported into MSR. Audio is extracted temporarily only for transcription."))
        layout.addStretch()
        return page

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setProperty("active", i == index)
            b.style().unpolish(b); b.style().polish(b)

    def refresh(self):
        self.message.setText("Connecting to DaVinci Resolve...")
        self.refresh_silent()

    def refresh_silent(self):
        try:
            self.bridge = ResolveBridge()
            if not self.bridge.connected:
                self.offline()
                return
            project = self.bridge.project_name()
            timeline = self.bridge.timeline_name()
            self.clips = self.bridge.video_clips()
            self.resolve_status.setText("● RESOLVE CONNECTED")
            self.resolve_card.setText("DaVinci Resolve: CONNECTED")
            self.project_card.value_label.setText(project)
            self.timeline_card.value_label.setText(timeline)
            self.media_card.value_label.setText(f"{len(self.clips)} video clip(s)")
            current = self.clip_list.currentRow()
            self.clip_list.clear()
            for c in self.clips:
                self.clip_list.addItem(f"V{c['track']} | {c['name']} | {Path(c['path']).name}")
            if self.clips:
                self.clip_list.setCurrentRow(current if 0 <= current < len(self.clips) else 0)
            self.gemini_info.setText("Gemini API: READY" if os.getenv("GEMINI_API_KEY") else "Gemini API: MISSING GEMINI_API_KEY in .env")
        except Exception as exc:
            self.offline(str(exc))

    def offline(self, error=None):
        self.resolve_status.setText("● RESOLVE OFFLINE")
        self.resolve_card.setText("DaVinci Resolve: OFFLINE")
        self.project_card.value_label.setText("Not connected")
        self.timeline_card.value_label.setText("Not connected")
        self.media_card.value_label.setText("0 clips")
        self.clips = []
        self.clip_list.clear()
        if error:
            self.message.setText(f"Resolve connection error: {error}")

    def choose_output(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save SRT", str(OUTPUT_DIR / "MSR_AI_Captions.srt"), "SRT (*.srt)")
        if p:
            if not p.lower().endswith(".srt"):
                p += ".srt"
            self.output.setText(p)

    def generate_captions(self):
        if not self.bridge.connected:
            QMessageBox.warning(self, "Resolve", "DaVinci Resolve is not connected.")
            return
        row = self.clip_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "MSR AI Captions", "Select a video clip.")
            return
        if not os.getenv("GEMINI_API_KEY"):
            QMessageBox.critical(self, "Gemini", f"GEMINI_API_KEY is missing from:\n{ENV_FILE}")
            return
        self.generate.setEnabled(False)
        self.progress.setValue(0)
        self.message.setText("Starting caption generation...")
        self.worker_thread = QThread(self)
        self.worker = Worker(self.bridge, self.clips[row], self.language.currentText(), self.output.text().strip())
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.error.connect(self.on_error)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def on_progress(self, value, text):
        self.progress.setValue(value); self.message.setText(text)

    def on_done(self, srt_path, segments, placement):
        self.generate.setEnabled(True)
        self.progress.setValue(100)
        self.transcript.setPlainText("\n\n".join(f"{self.ts(s['start'])} → {self.ts(s['end'])}\n{s['text']}" for s in segments))
        self.message.setText(f"SRT created and added to Resolve:\n{srt_path}")
        self.stop_worker()
        self.navigate(2)
        QMessageBox.information(self, "MSR AI Captions", "Caption generation completed.\n\n✓ SRT generated\n✓ SRT imported into Media Pool\n✓ Subtitle track created/reused\n✓ Captions added to the Resolve timeline")

    def on_error(self, message):
        self.generate.setEnabled(True)
        self.progress.setValue(0)
        self.message.setText("Generation failed.")
        self.stop_worker()
        QMessageBox.critical(self, "MSR AI Captions Error", message)

    def stop_worker(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()

    @staticmethod
    def ts(seconds):
        ms = int(round(float(seconds) * 1000))
        h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def closeEvent(self, event):
        try: self.timer.stop()
        except Exception: pass
        self.stop_worker()
        event.accept()


STYLE = """
QMainWindow,QWidget{background:#0d1117;color:#f0f6fc;font-family:'Segoe UI';font-size:14px;}
QFrame#Sidebar{background:#010409;border-right:1px solid #30363d;}
QLabel#Brand{font-size:32px;font-weight:900;color:#fff;} QLabel#BrandSub{font-size:20px;font-weight:800;color:#58a6ff;} QLabel#Version{color:#8b949e;font-size:12px;}
QPushButton#NavButton{padding:12px;text-align:left;background:transparent;color:#8b949e;border:1px solid transparent;border-radius:8px;} QPushButton#NavButton:hover{background:#161b22;color:#fff;} QPushButton#NavButton[active='true']{background:#21262d;color:#fff;border-color:#30363d;}
QLabel#ResolveStatus{padding:12px;background:#161b22;color:#58a6ff;border-radius:8px;font-weight:700;}
QLabel#HeaderTitle{font-size:28px;font-weight:800;color:#fff;} QLabel#HeaderSubtitle{color:#8b949e;} QLabel#PageTitle{font-size:27px;font-weight:800;color:#fff;} QLabel#FieldLabel,QLabel#Section{font-weight:800;color:#58a6ff;}
QFrame#Card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:5px;} QLabel#CardTitle{font-size:18px;font-weight:800;color:#fff;} QLabel#InfoTitle{font-size:11px;font-weight:800;color:#8b949e;} QLabel#InfoValue{font-size:17px;font-weight:700;color:#fff;}
QPushButton{background:#21262d;color:#f0f6fc;border:1px solid #30363d;border-radius:8px;padding:10px 15px;font-weight:600;} QPushButton:hover{background:#30363d;} QPushButton#Primary{background:#238636;color:#fff;border:none;font-weight:800;} QPushButton#Primary:hover{background:#2ea043;}
QListWidget,QTextEdit,QComboBox{background:#161b22;color:#f0f6fc;border:1px solid #30363d;border-radius:8px;padding:8px;} QListWidget::item{padding:12px;border-radius:7px;} QListWidget::item:selected{background:#1f6feb;color:#fff;}
QLabel#Output,QLabel#Message{background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:8px;padding:11px;}
QProgressBar{background:#161b22;color:#fff;border:1px solid #30363d;border-radius:7px;height:18px;text-align:center;} QProgressBar::chunk{background:#238636;border-radius:6px;}
"""


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("MSR AI Captions")
    app.setStyleSheet(STYLE)
    window = App()
    window.show()
    sys.exit(app.exec())
