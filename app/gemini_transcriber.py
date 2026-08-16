from __future__ import annotations
import json, os, re
from google import genai

class GeminiTranscriber:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing from .env")
        self.client = genai.Client(api_key=key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    def transcribe(self, audio_path: str, language: str):
        uploaded = self.client.files.upload(file=audio_path)

        lang = (
            "Detect the spoken language automatically."
            if language == "Auto Detect"
            else f"Transcribe the speech in {language}."
        )

        prompt = f"""
You are the timestamped speech-to-text engine for MSR AI Captions.

{lang}

Return ONLY valid JSON:
{{
  "segments": [
    {{
      "start": 0.0,
      "end": 2.5,
      "text": "spoken words"
    }}
  ]
}}

Rules:
- start and end are seconds from the beginning of the supplied audio.
- Do not invent speech.
- Preserve punctuation.
- Prefer natural caption boundaries.
- Keep most segments between 1 and 6 seconds.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt, uploaded],
        )

        text = (response.text or "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError("Gemini returned invalid transcript JSON.") from e

        result = []
        for s in data.get("segments", []):
            try:
                start = float(s["start"])
                end = float(s["end"])
                caption = str(s["text"]).strip()
                if caption and end > start:
                    result.append({"start": start, "end": end, "text": caption})
            except (KeyError, TypeError, ValueError):
                pass

        if not result:
            raise RuntimeError("Gemini returned no usable transcript segments.")
        return result
