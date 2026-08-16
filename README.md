# MSR AI Captions — Resolve Plugin Software

Flow:
DaVinci Resolve -> Workspace -> Scripts -> MSR AI Captions -> desktop EXE

The app connects to the running Resolve instance, reads the current project/timeline and video clips, extracts audio from the selected timeline clip with FFmpeg, sends that audio to Gemini for timestamped transcription, converts the timestamps to timeline-relative SRT, and displays the transcript.

This first build intentionally stops after creating the SRT. Automatic insertion of the SRT into a subtitle track should be added and tested against the exact Resolve version after the bridge is confirmed working.

Install:
1. Python 3.12
2. FFmpeg available as `ffmpeg`
3. `py -3 -m pip install -r requirements.txt`
4. Copy `.env.example` to `.env`
5. Put a NEW Gemini API key in `.env`
6. Test with `py -3 app/main.py`
7. Run `build_exe.bat`
8. Put `plugin/MSR_AI_Captions.py` in the Resolve Fusion Scripts folder.
