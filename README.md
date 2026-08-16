# MSR AI Captions — DaVinci Resolve + Gemini

Gemini-powered transcription, multilingual captions and direct video overlays for DaVinci Resolve.

## Main workflow

```text
DaVinci Resolve
      ↓
Workspace > Scripts > Utility > MSR AI Captions
      ↓
MSR AI Captions Studio
      ↓
Gemini transcription
      ↓
Smart caption algorithm
      ↓
Text+ Video Overlay
      ↓
Captions visible directly on the Resolve timeline/video
```

The Workspace script is now a **launcher only**. It starts the standalone Studio application so Resolve's embedded Python does not need Tkinter, Google SDKs or other third-party packages.

## Studio interface

The application includes:

- Resolve connection status
- Resolve version
- Current project
- Current timeline
- Check Permissions
- Repair Setup
- Automatic `.env` creation
- Gemini configuration status
- Python detection
- Video/audio browser
- Multi-language selection
- Text+ Video Overlay mode
- SRT Only mode
- Progress
- Diagnostics

The dashboard intentionally does **not** display the generated caption text. Caption text is placed on the Resolve timeline.

## Direct video overlay

The default mode is:

```text
Text+ Video Overlay
```

The Gemini transcript is post-processed locally and then converted into editable `Text+` clips. For each caption the overlay engine:

1. Converts seconds to timeline frames.
2. Sets Resolve mark-in/mark-out.
3. Inserts a `Text+` Fusion title.
4. Writes the caption into `StyledText`.
5. Applies basic text styling.
6. Clears the temporary mark.

This makes the captions visible in the Edit page as actual video overlays rather than as dashboard text.

The Resolve scripting API exposes `SetMarkInOut` and `InsertFusionTitleIntoTimeline`, which are used for this workflow.

## Resolve permission

For external application control, use DaVinci Resolve Studio and set:

```text
DaVinci Resolve
  > Preferences
  > System
  > General
  > External Scripting Using
  > Local
```

Then restart Resolve.

`Local` is correct when the application and Resolve run on the same PC. Blackmagic documents `None`, `Local`, and `Network`; `Local` permits same-computer external scripts/applications to control Resolve.

The app cannot silently change this security permission. Instead it automatically checks the connection and provides a permission wizard.

## Automatic setup

No `env.py` configuration is required.

On first run the app automatically creates `.env` if missing.

Configure only:

```text
GEMINI_API_KEY=YOUR_NEW_KEY
```

The app automatically supplies:

```text
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

Click **Repair Setup** to install/update the Python dependencies.

## Supported languages

Auto detection plus:

- English
- Tamil
- Hindi
- Telugu
- Malayalam
- Kannada
- Bengali
- Marathi
- Gujarati
- Punjabi
- Urdu
- Spanish
- French
- German
- Italian
- Portuguese
- Arabic
- Japanese
- Korean
- Chinese
- Indonesian

## Caption algorithm

Gemini supplies semantic transcription and timestamps. Python then applies deterministic caption rules:

- 42 maximum characters per line
- 2 lines maximum
- 9 words maximum per caption
- 0.8 second minimum duration
- 5.5 second maximum duration
- punctuation-aware breaks
- natural word boundaries
- reading-speed control
- overlap correction
- small timing gaps

## Files

```text
MSR-AI-Captions-Plugin/
├── MSR_AI_Captions_Studio.py       # Main standalone control panel
├── Start_MSR_AI_Captions.pyw       # Windowed launcher
├── config.py                        # Automatic env/Python/Resolve detection
├── resolve_overlay.py               # Text+ timeline overlay engine
├── Utility/
│   └── MSR_AI_Captions.py           # Workspace launcher
├── backend/
│   └── msr_gemini_backend.py        # Gemini + caption engine
├── requirements.txt
├── .env.example
├── RESOLVE_SETUP.md
└── README.md
```

## Installation

Install dependencies manually if desired:

```text
py -m pip install -r requirements.txt
```

Or launch the Studio application and click **Repair Setup**.

FFmpeg must also be installed and available as `ffmpeg.exe`.

## Output files

Generated files are stored beside the source media:

```text
_msr_ai_captions/
    video.srt
    video.vtt
    video.json
    video_16k.wav
```

## Security

The Gemini API key previously exposed in chat/screenshot must be revoked.

Never put a real Gemini API key in Python source, GitHub, screenshots or public releases. Use the local `.env` file and keep `.env` out of Git.
