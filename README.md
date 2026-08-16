# MSR AI Captions — DaVinci Resolve Studio + Gemini

MSR AI Captions is a Resolve-native Workspace script for Gemini transcription, multilingual caption generation, SRT creation and editable Text+ overlays.

## Important: no media import workflow

You do **not** browse for or import a video into the MSR application.

The script uses the **currently open DaVinci Resolve project and current timeline**:

```text
DaVinci Resolve Studio
        ↓
Workspace > Scripts > Utility > MSR AI Captions
        ↓
Native Resolve/Fusion UIManager interface
        ↓
Current Project + Current Timeline
        ↓
Resolve renders timeline audio only to a temporary WAV
        ↓
Hidden Python worker → Gemini
        ↓
Timestamped transcript
        ↓
Smart caption algorithm
        ↓
SRT + JSON/VTT
        ↓
Editable Text+ overlays on the same Resolve timeline
```

No separate Tkinter Studio window is required. The previous launcher architecture has been replaced by a native Resolve UI so clicking the Workspace script does not intentionally open multiple Command Prompt windows.

## Interface

The native interface shows:

- Current Resolve project
- Current timeline
- Language / auto detection
- Create editable Text+ overlays
- Create SRT
- Progress
- Diagnostics
- Generate captions from the current timeline

The caption text is not presented as a dashboard preview. The final caption text is written into the Resolve timeline as Text+ overlays.

## Timeline workflow

When **GENERATE CAPTIONS FROM CURRENT TIMELINE** is pressed:

1. The script checks that a project and timeline are open.
2. It does not ask the user to browse for media.
3. Resolve's own render engine renders **audio only** from the current timeline to a temporary WAV.
4. A hidden `pythonw.exe` worker sends that WAV to Gemini. No visible Command Prompt is used for the worker.
5. Gemini returns timestamped structured transcription.
6. The local caption algorithm applies line length, word count, timing, punctuation and reading-speed rules.
7. An SRT, VTT and JSON result is written to the temporary MSR output folder.
8. The Resolve script inserts editable `Text+` Fusion titles using the returned timestamps.

Resolve exposes render settings including `ExportVideo=False` / `ExportAudio=True`, and its scripting API provides `SetMarkInOut` and `InsertFusionTitleIntoTimeline` for timeline operations.

## Permission

Because the script is launched from inside Resolve, the primary requirement is that Resolve scripting is enabled. Use DaVinci Resolve Studio and set:

```text
DaVinci Resolve
  → Preferences
  → System
  → General
  → External Scripting Using
  → Local
```

Save and restart Resolve.

The script will show a native error/diagnostic window instead of silently spawning a Command Prompt when setup fails.

## Gemini configuration

No `env.py` file is required.

Create a local `.env` in the repository root if it does not already exist:

```text
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

The real API key must remain local and must never be committed to GitHub.

## Languages

Auto detection plus English, Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, Marathi, Gujarati, Punjabi, Urdu, Spanish, French, German, Italian, Portuguese, Arabic, Japanese, Korean, Chinese and Indonesian.

## Caption algorithm

The Gemini transcript is post-processed locally with deterministic rules:

- 42 maximum characters per line
- 2 lines maximum
- 9 words maximum per caption chunk
- 0.8 second minimum duration
- 5.5 second maximum duration
- punctuation-aware breaks
- natural word boundaries
- reading-speed control
- overlap correction
- small timing gaps

## Repository structure

```text
MSR-AI-Captions-Plugin/
├── Utility/
│   └── MSR_AI_Captions.py       # Native Resolve UI + timeline controller
├── backend/
│   └── msr_gemini_backend.py    # Hidden Gemini transcription worker
├── resolve_overlay.py            # Text+ timeline overlay engine
├── config.py                     # Local configuration helpers
├── MSR_AI_Captions_Studio.py     # Legacy standalone UI kept for compatibility
├── Start_MSR_AI_Captions.pyw     # Legacy launcher kept for compatibility
├── requirements.txt
├── .env.example
├── RESOLVE_SETUP.md
└── README.md
```

## Installation

Install Python dependencies with:

```text
py -m pip install -r requirements.txt
```

FFmpeg is required by the backend and must be available as `ffmpeg.exe`.

## Output

The native timeline workflow creates files under a temporary folder such as:

```text
%TEMP%\MSR_AI_Captions\<timeline-id>\
    msr_timeline_audio.wav
    MSR_AI_Captions.srt
    MSR_AI_Captions.vtt
    MSR_AI_Captions.json
```

The WAV is an internal processing file. The SRT/VTT/JSON are the generated caption artifacts.

## Security

Revoke any Gemini API key that was previously exposed in chat or screenshots. Never commit a real API key to GitHub.
