# MSR AI Captions

MSR AI Captions is a Windows desktop caption generator for DaVinci Resolve Studio.

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

Install Python packages:

```bat
py -3.12 -m pip install -r requirements.txt
```

Create `.env` from `.env.example` and set:

```text
GEMINI_API_KEY=your_key_here
```

Never commit `.env` or an API key.

## Run the desktop app

```bat
py -3.12 app\main.py
```

## Build the Windows EXE

Run:

```bat
build_exe.bat
```

The generated executable is placed at:

```text
app\MSR_AI_Captions.exe
```

## Resolve script installation

Copy the complete `MSR-AI-Captions-Plugin` folder into the DaVinci Resolve Fusion Scripts directory so the `plugin` and `app` folders remain siblings.

Then open:

**Workspace → Scripts → MSR AI Captions**

The launcher starts the desktop interface without intentionally opening a command prompt window.

## Project structure

```text
MSR-AI-Captions-Plugin/
├── app/
│   ├── main.py
│   ├── resolve_bridge.py
│   ├── gemini_transcriber.py
│   ├── audio.py
│   └── srt.py
├── plugin/
│   └── MSR_AI_Captions.py
├── build_exe.bat
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Generated files such as `.env`, `app/work`, `app/output`, Python caches and PyInstaller build folders are excluded by `.gitignore`.
