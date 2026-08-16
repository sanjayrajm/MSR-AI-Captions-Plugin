from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROJECT_ID = os.getenv("GEMINI_PROJECT_ID", "774512798784")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
MAX_CHARS = 42
MAX_WORDS = 9
MIN_DURATION = 0.8
MAX_DURATION = 5.5
MAX_CPS = 20.0
GAP = 0.04


class Segment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str
    speaker: Optional[str] = None


class Transcript(BaseModel):
    detected_language: str
    segments: List[Segment]


def progress(value, text):
    print(f"PROGRESS|{value}|{text}", flush=True)


def get_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    for p in (r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"):
        if Path(p).exists():
            return p
    raise RuntimeError("FFmpeg was not found. Install FFmpeg and add ffmpeg.exe to PATH.")


def extract_audio(src, dst):
    result = subprocess.run([
        get_ffmpeg(), "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError("FFmpeg failed:\n" + result.stderr[-4000:])


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def wrap(text):
    text = clean(text)
    if len(text) <= MAX_CHARS:
        return text
    words = text.split()
    mid = len(words) // 2
    best = None
    score = 10**9
    for i in range(max(1, mid - 3), min(len(words), mid + 4)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if len(a) <= MAX_CHARS and len(b) <= MAX_CHARS:
            s = abs(len(a) - len(b))
            if s < score:
                score, best = s, (a, b)
    if best:
        return best[0] + "\n" + best[1]
    return "\n".join([" ".join(words[:mid]), " ".join(words[mid:])])


def optimize(segments):
    out = []
    for seg in segments:
        text = clean(seg.text)
        if not text:
            continue
        start = max(0.0, float(seg.start))
        end = max(start + MIN_DURATION, float(seg.end))
        duration = max(0.01, end - start)
        words = text.split()
        chunks, current = [], []
        for word in words:
            candidate = " ".join(current + [word])
            punctuation = bool(current) and bool(re.search(r"[.!?।]$", current[-1]))
            if current and (punctuation or len(candidate) > MAX_CHARS * 2 or len(current) >= MAX_WORDS):
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))
        total_words = max(1, len(words))
        cursor = start
        for i, chunk in enumerate(chunks):
            count = max(1, len(chunk.split()))
            piece = max(MIN_DURATION, min(MAX_DURATION, duration * count / total_words))
            piece_start = cursor
            piece_end = min(end, piece_start + max(piece, count / MAX_CPS))
            if i == len(chunks) - 1:
                piece_end = max(piece_start + MIN_DURATION, end)
            out.append({"start": piece_start, "end": piece_end, "text": wrap(chunk), "speaker": seg.speaker})
            cursor = min(end, piece_end + GAP)
    for i in range(1, len(out)):
        if out[i]["start"] < out[i - 1]["end"]:
            midpoint = (out[i]["start"] + out[i - 1]["end"]) / 2
            out[i - 1]["end"] = max(out[i - 1]["start"] + MIN_DURATION, midpoint)
            out[i]["start"] = midpoint
    return out


def srt_time(sec):
    sec = max(0.0, float(sec))
    h, rem = divmod(sec, 3600)
    m, rem = divmod(rem, 60)
    s = int(rem)
    ms = int(round((rem - s) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    if s >= 60:
        s, m = 0, m + 1
    if m >= 60:
        m, h = 0, h + 1
    return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"


def vtt_time(sec):
    return srt_time(sec).replace(",", ".")


def write_srt(captions, path):
    with open(path, "w", encoding="utf-8-sig") as f:
        for i, c in enumerate(captions, 1):
            f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n")


def write_vtt(captions, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for c in captions:
            f.write(f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}\n{c['text']}\n\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--language", required=True)
    args = parser.parse_args()

    src = Path(args.input).resolve()
    if not src.exists():
        raise FileNotFoundError(src)

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add a NEW key to .env.")

    work = src.parent / "_msr_ai_captions"
    work.mkdir(exist_ok=True)
    wav = work / f"{src.stem}_16k.wav"
    srt = work / f"{src.stem}.srt"
    vtt = work / f"{src.stem}.vtt"
    js = work / f"{src.stem}.json"

    progress(10, "Extracting audio...")
    extract_audio(src, wav)
    progress(30, "Connecting to Gemini...")
    client = genai.Client(api_key=key)
    progress(45, "Uploading audio...")
    audio = client.files.upload(file=str(wav))

    target = "Keep the original spoken language and do not translate." if args.language in ("Original", "Auto Detect") else f"Translate into {args.language}; preserve meaning and natural phrasing."
    prompt = f"""
You are the professional transcription engine for MSR AI Captions.
Transcribe the supplied audio accurately.
Detect the spoken language, preserve speech, add punctuation, create timestamped segments in seconds, identify speakers when reasonably possible, never invent words, and {target}
Return only the structured JSON response.
"""
    progress(60, "Transcribing and translating with Gemini...")
    response = client.models.generate_content(
        model=MODEL,
        contents=[audio, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Transcript,
            temperature=0.1,
        ),
    )
    transcript = Transcript.model_validate_json(response.text)
    progress(75, "Running smart caption algorithm...")
    captions = optimize(transcript.segments)
    if not captions:
        raise RuntimeError("Gemini returned no usable caption segments.")
    progress(85, "Writing SRT, VTT and JSON...")
    write_srt(captions, srt)
    write_vtt(captions, vtt)
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"project_id": PROJECT_ID, "model": MODEL, "detected_language": transcript.detected_language, "captions": captions}, f, ensure_ascii=False, indent=2)
    progress(100, "Completed.")
    print("RESULT|" + json.dumps({"srt": str(srt), "vtt": str(vtt), "json": str(js), "detected_language": transcript.detected_language}), flush=True)


if __name__ == "__main__":
    main()
