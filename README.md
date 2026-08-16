# MSR AI Captions — DaVinci Resolve Plugin

Gemini-powered transcription and multilingual caption generation for DaVinci Resolve.

## Features

- DaVinci Resolve Workspace > Scripts > Utility integration
- Gemini audio transcription
- Automatic language detection
- Multi-language translation
- Tamil, Hindi, Telugu, Malayalam, Kannada and more
- Smart caption segmentation
- SRT, VTT and JSON export
- Optional subtitle-track import into the current Resolve timeline
- FFmpeg audio extraction

## Installation

Run `install.bat` on Windows. Then restart DaVinci Resolve and open:

`Workspace > Scripts > Utility > MSR AI Captions`

Create `.env` from `.env.example` and add a **new** Gemini API key.

```text
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

Do not commit `.env` or real API keys.

## Architecture

```text
DaVinci Resolve
      -> Resolve Utility Script
      -> Python Gemini Worker
      -> FFmpeg
      -> Gemini
      -> Transcript
      -> Caption Algorithm
      -> SRT / VTT / JSON
      -> Resolve Subtitle Track
```
