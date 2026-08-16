# MSR AI Captions — Native Resolve Setup

## New architecture

The Workspace script is now the actual MSR AI Captions interface. It does **not** launch a Tkinter window and does **not** ask the user to import a video.

```text
Resolve Workspace > Scripts > Utility > MSR AI Captions
                         ↓
                 Native Resolve UIManager
                         ↓
                Current Project + Timeline
                         ↓
                Resolve audio-only render
                         ↓
              Hidden Gemini Python worker
                         ↓
                  SRT + JSON + VTT
                         ↓
                 Text+ timeline overlays
```

## 1. Resolve permission

For this native Workspace workflow, the script runs **inside Resolve**, so it does not depend on an external `scriptapp("Resolve")` connection to open the UI.

If Resolve's scripting security is set to a restrictive mode and the script reports that scripting is unavailable, use:

```text
DaVinci Resolve
  > Preferences
  > System
  > General
  > External Scripting Using
  > Local
```

Save and restart Resolve.

`Local` is the same-PC external scripting mode documented by Resolve. The native Workspace script itself should normally be able to access the current Resolve context without launching an external Resolve controller.

## 2. Install the Utility script

Copy the repository file:

```text
Utility/MSR_AI_Captions.py
```

to:

```text
%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
```

The final path should be:

```text
%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\MSR_AI_Captions.py
```

Do not place a folder named `MSR_AI_Captions` around the file if you want a direct menu item.

## 3. Keep the repository folder intact

The repository root must contain:

```text
MSR-AI-Captions-Plugin/
├── Utility/MSR_AI_Captions.py
├── backend/msr_gemini_backend.py
├── resolve_overlay.py
├── config.py
├── requirements.txt
└── .env
```

## 4. Python / Gemini worker

The Resolve UI stays inside Resolve. Only the heavy Gemini work is sent to a hidden `pythonw.exe` worker so no Command Prompt window is intentionally opened.

Install dependencies once:

```text
py -3 -m pip install -r requirements.txt
```

Python 3.12 is supported by the worker.

## 5. `.env`

No `env.py` is required.

Create a local `.env` in the repository root:

```text
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

Never commit the real API key.

## 6. Use the current timeline — no video/image import

1. Open DaVinci Resolve Studio.
2. Open your project.
3. Open the timeline containing the video/audio you want to caption.
4. Make sure the timeline is active.
5. Go to:

```text
Workspace > Scripts > Utility > MSR AI Captions
```

6. The native MSR interface opens.
7. Select language or `Auto Detect`.
8. Keep `Create editable Text+ overlays` enabled if you want captions directly over the video.
9. Keep `Create SRT file` enabled if you also want the SRT artifact.
10. Click:

```text
GENERATE CAPTIONS FROM CURRENT TIMELINE
```

The software does **not** ask you to browse for an MP4/MOV/image.

## 7. What happens internally

Resolve renders only the active timeline's audio to a temporary WAV using its own render engine. The video is not imported into MSR and is not re-rendered by MSR.

The hidden worker sends that WAV to Gemini and receives timestamped transcript segments. The local algorithm creates readable caption chunks and an SRT.

The Resolve-side script then uses the current timeline and inserts editable `Text+` Fusion titles at the Gemini timestamps.

## 8. Result

The timeline becomes conceptually:

```text
V2  ── Text+ ── Text+ ── Text+ ── Text+
V1  ───────────── YOUR VIDEO ─────────────
A1  ───────────── YOUR AUDIO ─────────────
```

The caption text is therefore visible in the Resolve Viewer and remains editable in the timeline.

## 9. Troubleshooting

If the MSR menu item opens multiple Command Prompt windows, you are still using the **old** `Utility/MSR_AI_Captions.py`. Replace it with the new repository version and restart Resolve.

If the UI does not appear, open:

```text
Workspace > Console
```

and run the script again. The native version is designed to report the error instead of silently launching and closing several console windows.

If `UIManager` is unavailable, confirm you are running **DaVinci Resolve Studio** and that the Resolve/Fusion scripting support is installed.

## 10. API key security

The Gemini key previously exposed in screenshots/chat must be revoked. Create a replacement key and store it only in local `.env`.
