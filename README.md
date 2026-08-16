# MSR AI Captions

MSR AI Captions is a Windows desktop caption generator for DaVinci Resolve Studio.

> **Project website:** open `index.html` from the repository root, or publish the repository with GitHub Pages. The website provides the installation guide, commands, project files, and source ZIP download.

## Website

The root website is built as a separate GitHub-style UI/UX:

- `index.html` — documentation and download landing page
- `styles.css` — responsive GitHub-inspired design
- `script.js` — copy-to-clipboard interactions

The page includes Features, Installation, Commands, Project Files, Download ZIP and GitHub Repository actions.

## Current workflow

1. Open DaVinci Resolve.
2. Open a project and its active timeline.
3. Open **Workspace → Scripts → MSR AI Captions**.
4. MSR connects to the active Resolve project and timeline.
5. Select a video already present on the timeline.
6. MSR extracts temporary audio from that Resolve media file.
7. Gemini creates a timestamped transcript.
8. MSR writes the SRT to `output/MSR_AI_Captions.srt`.
9. The SRT is imported into the Resolve Media Pool.
10. MSR creates/reuses a subtitle track and places the SRT at the selected video's timeline position.

The source video is not imported into MSR. Resolve remains the source of the project, timeline and media information.

## Requirements

- Windows
- DaVinci Resolve Studio with scripting enabled
- Python 3.12 recommended
- FFmpeg available in PATH
- Gemini API key

## Installation

### 1. Clone the repository

```bat
git clone https://github.com/sanjayrajm/MSR-AI-Captions-Plugin.git
cd MSR-AI-Captions-Plugin
```

Or use **Download ZIP** on the project website/GitHub page.

### 2. Create a virtual environment

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bat
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
```

### 4. Configure Gemini

Copy `.env.example` to `.env` and add your key:

```text
GEMINI_API_KEY=your_key_here
```

Never commit `.env` or an API key.

### 5. Check FFmpeg

```bat
ffmpeg -version
```

FFmpeg must be available in Windows PATH.

### 6. Run the application

```bat
py -3.12 app\main.py
```

## Install into DaVinci Resolve

Keep the repository structure intact so `plugin` and `app` are sibling folders.

Copy the complete `MSR-AI-Captions-Plugin` folder into your DaVinci Resolve Fusion Scripts directory. Then open:

**Workspace → Scripts → MSR AI Captions**

The launcher starts the desktop interface without intentionally opening a command prompt window.

## Build the Windows EXE

```bat
build_exe.bat
```

The generated executable is placed at:

```text
app\MSR_AI_Captions.exe
```

The EXE is intentionally ignored by Git because generated binaries should not be stored in the source repository by default.

## Common commands

```bat
:: Clone
git clone https://github.com/sanjayrajm/MSR-AI-Captions-Plugin.git
cd MSR-AI-Captions-Plugin

:: Environment
py -3.12 -m venv .venv
.venv\Scripts\activate

:: Dependencies
py -3.12 -m pip install -r requirements.txt

:: Run
py -3.12 app\main.py

:: Build
build_exe.bat
```

## Project structure

```text
MSR-AI-Captions-Plugin/
├── index.html                 # Project website
├── styles.css                 # Website UI/UX
├── script.js                  # Website interactions
├── app/
│   ├── main.py                # Desktop UI and workflow
│   ├── resolve_bridge.py      # DaVinci Resolve integration
│   ├── gemini_transcriber.py  # Gemini transcription
│   ├── audio.py               # Temporary audio extraction
│   └── srt.py                 # SRT generation
├── plugin/
│   └── MSR_AI_Captions.py     # Resolve launcher
├── build_exe.bat              # Windows EXE build script
├── requirements.txt            # Python dependencies
├── .env.example               # API key template
├── .gitignore
└── README.md
```

Generated files such as `.env`, `app/work`, `app/output`, Python caches, launcher logs and PyInstaller build artifacts are excluded by `.gitignore`.
