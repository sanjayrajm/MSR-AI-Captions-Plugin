from pathlib import Path
import subprocess

def extract_audio(video_path: str, output_path: str) -> Path:
    """Extract the audio of a Resolve source clip without importing the clip into MSR."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out
