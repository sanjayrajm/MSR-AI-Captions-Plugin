# MSR AI Captions — Resolve Setup

## What changed

The Resolve menu script is now a **launcher only**. It starts the standalone MSR AI Captions Studio instead of trying to run Tkinter/Gemini inside Resolve's embedded Python.

This fixes the common case where:

```text
Workspace > Scripts > Utility > MSR AI Captions
```

appears in Resolve but clicking it does nothing.

## 1. Resolve permission

For live control from the standalone app, use **DaVinci Resolve Studio** and enable external scripting:

```text
DaVinci Resolve
  > Preferences
  > System
  > General
  > External Scripting Using
  > Local
```

Then save and restart Resolve.

`Local` is the correct choice when MSR AI Captions and Resolve are on the same Windows PC. Blackmagic documents `None`, `Local`, and `Network` for this setting; `Local` allows same-computer external scripts/applications to control Resolve. The setting is a Studio feature.

The MSR application has a **Check Permissions** button and automatically tests the Resolve scripting connection. It cannot silently change Resolve's security preference because that is an application security control.

## 2. Automatic Python setup

The application automatically checks for Python and prefers:

1. Python 3.11
2. Python 3.10
3. Python 3.12
4. Python launcher default
5. `python`

This is intentional because some Resolve scripting environments are most reliable with Python 3.10/3.11.

Click **Repair Setup** in the app to install/update:

```text
google-genai
python-dotenv
pydantic
```

## 3. Automatic `.env` setup

You do not need an `env.py` file.

On first run the app automatically creates:

```text
.env
```

with:

```text
GEMINI_API_KEY=PASTE_NEW_KEY_HERE
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

Click **Configure .env** to open it.

Only the API key needs to be supplied by you. The project number and model are automatically managed by the application.

Never commit `.env`.

## 4. Generate captions directly on the video

The new default output mode is:

```text
Text+ Video Overlay
```

The application does **not** display generated caption text in its dashboard.

Workflow:

```text
Video
  ↓
Gemini transcription
  ↓
Timestamped transcript
  ↓
Smart caption algorithm
  ↓
Caption JSON
  ↓
Resolve Text+ clips
  ↓
Timeline overlay
```

For every caption, the app:

1. Converts Gemini timing to timeline frames.
2. Sets Resolve mark-in/mark-out.
3. Inserts a `Text+` Fusion title.
4. Writes the caption into `StyledText`.
5. Applies basic readable styling.
6. Clears the temporary mark.

The result is an actual editable Text+ video overlay in the Resolve timeline, rather than caption text being shown in the MSR dashboard.

Resolve's scripting API exposes `SetMarkInOut` and `InsertFusionTitleIntoTimeline`; this workflow is used because the public scripting API does not expose a general `SetSubtitleText` method for arbitrary subtitle items. See the Resolve API documentation included with Resolve under Help > Documentation > Developer.

## 5. SRT-only mode

If you do not want Text+ overlays, select:

```text
Output: SRT Only
```

The app will still create:

```text
video.srt
video.vtt
video.json
```

inside:

```text
_msr_ai_captions
```

## 6. Start from Resolve

After installation:

1. Start Resolve Studio.
2. Open a project.
3. Open a timeline.
4. Set External Scripting Using to `Local`.
5. Restart Resolve.
6. Go to:

```text
Workspace > Scripts > Utility > MSR AI Captions
```

7. The menu script launches **MSR AI Captions Studio**.
8. Wait for `Resolve: CONNECTED`.
9. Select your media.
10. Select the caption language.
11. Keep `Text+ Video Overlay` selected.
12. Click **GENERATE & OVERLAY CAPTIONS**.

## 7. If Workspace script still does not open

The Resolve script only launches the standalone application. Test the launcher manually:

```text
py MSR_AI_Captions_Studio.py
```

If that works but Workspace does not, reinstall/copy:

```text
Utility/MSR_AI_Captions.py
```

to the Resolve Utility Scripts directory and restart Resolve.

## 8. Resolve module paths

The app checks common Windows paths including:

```text
C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules
C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Scripting\Modules
C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules
```

If your installation is custom, the **Diagnostics** panel reports that the module was not found.

## 9. Important security note

The API key previously exposed in the screenshot/chat must be revoked.

Create a replacement Gemini API key and put it only in local `.env`.

Do not put a real key in:

- GitHub
- Python source
- screenshots
- ZIP files
- README files

## 10. Why the dashboard does not show captions

The dashboard is now a **control panel only**. It shows connection, configuration, progress and diagnostics.

The generated caption text belongs in the Resolve timeline as Text+ overlays.
