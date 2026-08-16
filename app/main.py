from __future__ import annotations
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QStackedWidget
)
from resolve_bridge import ResolveBridge
from audio import extract_audio
from gemini_transcriber import GeminiTranscriber
from srt import write_srt

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")

class Worker(QObject):
    progress = Signal(int, str)
    done = Signal(str, object)
    error = Signal(str)

    def __init__(self, bridge, clip, language, output):
        super().__init__()
        self.bridge, self.clip = bridge, clip
        self.language, self.output = language, output

    def run(self):
        try:
            work = ROOT / "work"
            work.mkdir(exist_ok=True)

            self.progress.emit(10, "Extracting audio from the Resolve media...")
            audio = work / "current_clip.wav"
            extract_audio(self.clip["path"], audio)

            self.progress.emit(35, "Sending audio to Gemini...")
            segments = GeminiTranscriber().transcribe(str(audio), self.language)

            fps = self.bridge.timeline_fps()
            timeline_offset = self.clip["timeline_start"] / fps

            adjusted = [
                {
                    "start": s["start"] + timeline_offset,
                    "end": s["end"] + timeline_offset,
                    "text": s["text"],
                }
                for s in segments
            ]

            self.progress.emit(80, "Creating SRT with Resolve timeline timing...")
            srt = write_srt(adjusted, self.output)

            self.progress.emit(100, "Transcript and SRT are ready.")
            self.done.emit(srt, adjusted)

        except Exception as e:
            self.error.emit(str(e))

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSR AI Captions")
        self.resize(1100, 720)
        self.bridge = ResolveBridge()
        self.clips = []
        self._build()
        self.refresh()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)

        side = QVBoxLayout()
        brand = QLabel("MSR\nAI CAPTIONS")
        brand.setStyleSheet("font-size:25px;font-weight:800;")
        side.addWidget(brand)

        for text, index in [
            ("Dashboard", 0),
            ("Generate Captions", 1),
            ("Transcript", 2),
            ("Settings", 3),
        ]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, i=index: self.pages.setCurrentIndex(i))
            side.addWidget(b)

        side.addStretch()
        self.resolve_status = QLabel("Resolve: checking...")
        side.addWidget(self.resolve_status)

        sw = QWidget()
        sw.setLayout(side)
        sw.setFixedWidth(220)
        main.addWidget(sw)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.dashboard())
        self.pages.addWidget(self.caption_page())
        self.pages.addWidget(self.transcript_page())
        self.pages.addWidget(self.settings_page())
        main.addWidget(self.pages, 1)

    def dashboard(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("<h1>MSR AI Captions</h1>"))
        self.project = QLabel()
        self.timeline = QLabel()
        self.media = QLabel()
        l.addWidget(self.project)
        l.addWidget(self.timeline)
        l.addWidget(self.media)
        b = QPushButton("REFRESH RESOLVE")
        b.clicked.connect(self.refresh)
        l.addWidget(b)
        l.addStretch()
        return w

    def caption_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("<h1>Generate Captions</h1>"))
        l.addWidget(QLabel("Video clips detected in the current Resolve timeline:"))

        self.clip_list = QListWidget()
        l.addWidget(self.clip_list)

        self.language = QComboBox()
        self.language.addItems([
            "Auto Detect", "English", "Tamil", "Hindi", "Telugu",
            "Malayalam", "Kannada", "Bengali", "Marathi", "Gujarati",
            "Punjabi", "Urdu", "Spanish", "French", "German",
            "Japanese", "Korean"
        ])
        l.addWidget(self.language)

        row = QHBoxLayout()
        self.output = QLabel(str(ROOT / "output" / "MSR_AI_Captions.srt"))
        choose = QPushButton("Choose SRT")
        choose.clicked.connect(self.choose_output)
        row.addWidget(self.output, 1)
        row.addWidget(choose)
        l.addLayout(row)

        self.generate = QPushButton("GENERATE CAPTIONS")
        self.generate.setMinimumHeight(52)
        self.generate.clicked.connect(self.generate_captions)
        l.addWidget(self.generate)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        l.addWidget(self.progress)

        self.message = QLabel("Ready.")
        l.addWidget(self.message)
        l.addStretch()
        return w

    def transcript_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("<h1>Transcript</h1>"))
        self.transcript = QTextEdit()
        l.addWidget(self.transcript)
        return w

    def settings_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("<h1>Settings</h1>"))
        l.addWidget(QLabel(
            "Gemini is configured through the local .env file.\n"
            "Never commit your API key to GitHub."
        ))
        l.addStretch()
        return w

    def refresh(self):
        self.bridge = ResolveBridge()
        if not self.bridge.connected:
            self.resolve_status.setText("Resolve: OFFLINE")
            self.project.setText("Project: Not connected")
            self.timeline.setText("Timeline: Not connected")
            self.media.setText("Media: Not connected")
            self.clip_list.clear()
            return

        self.resolve_status.setText("Resolve: CONNECTED")
        self.project.setText(f"Project: {self.bridge.project_name()}")
        self.timeline.setText(f"Timeline: {self.bridge.timeline_name()}")

        self.clips = self.bridge.video_clips()
        self.media.setText(f"Video clips detected: {len(self.clips)}")
        self.clip_list.clear()

        for c in self.clips:
            self.clip_list.addItem(
                f"V{c['track']} | {c['name']} | {Path(c['path']).name}"
            )

    def choose_output(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Save SRT", "MSR_AI_Captions.srt", "SRT (*.srt)"
        )
        if p:
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
            QMessageBox.critical(self, "Gemini", "GEMINI_API_KEY is missing from .env.")
            return

        self.generate.setEnabled(False)
        self.worker_thread = QThread()
        self.worker = Worker(
            self.bridge,
            self.clips[row],
            self.language.currentText(),
            self.output.text().strip()
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.error.connect(self.on_error)
        self.worker_thread.start()

    def on_progress(self, value, text):
        self.progress.setValue(value)
        self.message.setText(text)

    def on_done(self, srt_path, segments):
        self.generate.setEnabled(True)
        self.transcript.setPlainText(
            "\n".join(
                f"{s['start']:.2f} → {s['end']:.2f}   {s['text']}"
                for s in segments
            )
        )
        self.message.setText(f"SRT created: {srt_path}")
        self.pages.setCurrentIndex(2)
        self.worker_thread.quit()
        self.worker_thread.wait()
        QMessageBox.information(
            self,
            "MSR AI Captions",
            "Transcript + SRT generation completed.\n\n"
            "The next integration step is to insert that SRT into the "
            "current Resolve timeline automatically."
        )

    def on_error(self, message):
        self.generate.setEnabled(True)
        self.message.setText("Generation failed.")
        self.worker_thread.quit()
        self.worker_thread.wait()
        QMessageBox.critical(self, "MSR AI Captions", message)

STYLE = """
QMainWindow { background:#111318; color:#ECEFF4; }
QWidget { font-family:"Segoe UI"; font-size:14px; }
QPushButton { padding:10px; border-radius:7px; background:#202630; color:#ECEFF4; }
QPushButton:hover { background:#2A3240; }
QListWidget,QTextEdit,QComboBox {
 background:#171C24; color:#ECEFF4; border:1px solid #303846;
 border-radius:7px; padding:8px;
}
QProgressBar { height:10px; border-radius:5px; background:#202630; }
QProgressBar::chunk { border-radius:5px; background:#ECEFF4; }
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = App()
    window.show()
    sys.exit(app.exec())
