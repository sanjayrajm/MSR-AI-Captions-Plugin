# MSR AI Captions — DaVinci Resolve + Gemini

Gemini-powered transcription, multilingual captions, and a standalone control panel for DaVinci Resolve Studio.

## Recommended workflow

Use **MSR AI Captions Studio** as the main application. It gives you a visible interface, Resolve connection status, project/timeline detection, permission checklist, Gemini status, media selection, language selection, progress and diagnostics.

### Start the software

```text
py MSR_AI_Captions_Studio.py
```

Or double-click:

```text
Start_MSR_AI_Captions.pyw
```

The Studio app can:

- Connect to a running DaVinci Resolve instance
- Detect Resolve version
- Detect current project
- Detect current timeline
- Check the Gemini API-key configuration
- Show the Resolve external-scripting permission steps
- Select video/audio media
- Transcribe with Gemini
- Auto-detect the spoken language
- Translate captions into multiple languages
- Apply smart caption timing and line breaking
- Generate SRT, VTT and JSON
- Attempt to import the SRT into the current Resolve timeline

## Resolve permission

For live control from the standalone app, use **DaVinci Resolve Studio** and enable:

```text
DaVinci Resolve
  > Preferences
  > System
  > General
  > External Scripting Using
  > Local
```

Use **Local** when the app and Resolve are on the same computer.

The app contains a **Check Permissions** button with the complete setup checklist.

Blackmagic's documentation describes External Scripting Using as `None`, `Local`, or `Network`; `Local` permits external scripts/applications on the same computer to control Resolve, while `Network` permits network control. The setting is documented as a Resolve Studio feature.

See [RESOLVE_SETUP.md](RESOLVE_SETUP.md) for troubleshooting.

## Gemini configuration

Create a local `.env` beside `MSR_AI_Captions_Studio.py`:

```text
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

The API key previously exposed in the screenshot/chat must be revoked. Never commit a real key to GitHub.

## Features

- DaVinci Resolve Workspace Utility script
- Standalone MSR AI Captions Studio
- Resolve connection diagnostics
- Resolve permission wizard
- Gemini audio transcription
- Automatic language detection
- Multi-language translation
- Tamil, Hindi, Telugu, Malayalam, Kannada and more
- Smart caption segmentation
- SRT, VTT and JSON export
- Optional subtitle-track import into the current Resolve timeline
- FFmpeg audio extraction
- Windows `.pyw` launcher

## Caption algorithm

Gemini supplies semantic transcription and timing. The local Python caption engine then applies deterministic rules:

- Maximum 42 characters per line
- Maximum 2 lines
- Maximum 9 words per caption
- Minimum 0.8 second duration
- Maximum 5.5 second duration
- Punctuation-aware breaks
- Natural word boundaries
- Reading-speed control
- Caption overlap correction
- Small timing gaps

## Files

```text
MSR-AI-Captions-Plugin/
├── MSR_AI_Captions_Studio.py       # Standalone GUI + Resolve connection
├── Start_MSR_AI_Captions.pyw       # Windowed launcher
├── Utility/
│   └── MSR_AI_Captions.py           # Resolve Workspace script
├── backend/
│   └── msr_gemini_backend.py        # Gemini + caption engine
├── requirements.txt
├── .env.example
├── RESOLVE_SETUP.md
└── README.md
```

## Install dependencies

```text
py -m pip install -r requirements.txt
```

FFmpeg must also be installed and available as `ffmpeg.exe`.

## Output

Generated files are stored beside the source media:

```text
_msr_ai_captions/
    video.srt
    video.vtt
    video.json
    video_16k.wav
```

## Security

Never place a real Gemini API key in Python source code, GitHub, screenshots, or public releases. Use a local `.env` file and keep `.env` out of Git.
