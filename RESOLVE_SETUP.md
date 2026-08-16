# DaVinci Resolve Setup for MSR AI Captions Studio

## Required Resolve permission

For the standalone MSR AI Captions Studio to control Resolve, use **DaVinci Resolve Studio** and enable external scripting.

1. Open DaVinci Resolve Studio.
2. Open **DaVinci Resolve > Preferences**.
3. Select **System > General**.
4. Find **External Scripting Using**.
5. Set it to **Local** for a tool running on the same PC.
6. Save the preferences.
7. Restart Resolve if requested.
8. Open a project and a timeline.
9. Start MSR AI Captions Studio.
10. Click **Connect / Reconnect**.

Blackmagic's documentation describes this setting as having `None`, `Local`, and `Network` modes. `Local` allows external scripts/applications on the same computer to control Resolve; `Network` is for external machines. The setting is documented as a Resolve Studio feature.

## Local vs Network

### Local — recommended

Use this when MSR AI Captions Studio and Resolve are on the same Windows PC.

Host:

```text
127.0.0.1
```

The Studio app uses Resolve's local scripting connection.

### Network

Use this only when the Resolve scripting endpoint is intentionally exposed for another machine. Enter the Resolve computer's IP address in the app.

Do not expose Resolve scripting to untrusted networks. Prefer Local whenever possible.

## If the app says Resolve is not connected

Check these in order:

- Resolve is running.
- You are using Resolve Studio if external scripting is required by your installed version.
- External Scripting Using is not `None`.
- Use `Local` for same-PC operation.
- A project is open.
- A timeline is open.
- MSR AI Captions Studio is running after Resolve is already open.
- Python 3.10+ is installed and `py --version` works.
- The Resolve scripting module is installed with the Resolve installation.

## If the app says DaVinciResolveScript module was not found

The app automatically checks common Windows Resolve locations. If your Resolve installation is in a custom location, the Resolve scripting module may be elsewhere.

The app can still generate SRT/VTT/JSON through the Gemini backend; only live Resolve control is affected.

## If captions generate but do not appear in Resolve

The generated SRT is stored beside the source media in:

```text
_msr_ai_captions
```

The app attempts to use the Resolve API method:

```python
timeline.CreateSubtitlesFromFile(srt_path)
```

If the installed Resolve scripting API does not expose this method, import the generated SRT through Resolve's normal subtitle import workflow.

## Gemini setup

Create a local `.env` beside `MSR_AI_Captions_Studio.py`:

```text
GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_PROJECT_ID=774512798784
GEMINI_MODEL=gemini-3.6-flash
```

The Gemini API key previously exposed in the screenshot/chat must be revoked. Never commit a real key to GitHub.

## Launch

From Command Prompt:

```text
py MSR_AI_Captions_Studio.py
```

Or double-click:

```text
Start_MSR_AI_Captions.pyw
```

The `.pyw` launcher opens the GUI without a console window.
