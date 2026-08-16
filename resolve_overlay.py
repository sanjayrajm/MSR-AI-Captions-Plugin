from __future__ import annotations

import math
from typing import Iterable


def timeline_fps(timeline) -> float:
    for key in ("timelineFrameRate", "timelineFrameRateFloat"):
        try:
            value = timeline.GetSetting(key)
            if value:
                return float(value)
        except Exception:
            pass
    return 24.0


def set_text_plus(item, text: str) -> bool:
    try:
        comp = item.GetFusionCompByIndex(1)
        tools = comp.GetToolList()
        if not tools:
            return False

        # Text+ is normally the first/only tool in the inserted title comp.
        for _, tool in tools.items():
            try:
                tool.SetInput("StyledText", text)
                return True
            except Exception:
                try:
                    tool.StyledText = text
                    return True
                except Exception:
                    continue
    except Exception:
        return False
    return False


def set_text_plus_style(item, font="Noto Sans", size=0.055):
    try:
        comp = item.GetFusionCompByIndex(1)
        tools = comp.GetToolList()
        for _, tool in tools.items():
            try:
                tool.SetInput("Font", font)
            except Exception:
                pass
            try:
                tool.SetInput("Size", size)
            except Exception:
                pass
            try:
                tool.SetInput("HorizontalJustification", 1)
            except Exception:
                pass
            break
    except Exception:
        pass


def add_text_plus_overlays(resolve, captions: Iterable[dict]) -> dict:
    """Create real Text+ clips on the Resolve timeline.

    Timing is taken from the Gemini-generated caption JSON. Resolve's
    SetMarkInOut is used before InsertFusionTitleIntoTimeline so each title
    gets the caption's exact duration. This makes the text visible in the
    Edit page viewer as an actual video overlay rather than a dashboard item.
    """
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if not project:
        return {"ok": False, "created": 0, "message": "No current project."}

    timeline = project.GetCurrentTimeline()
    if not timeline:
        return {"ok": False, "created": 0, "message": "No current timeline."}

    try:
        timeline.AddTrack("video")
    except Exception:
        pass

    track_count = 0
    try:
        track_count = int(timeline.GetTrackCount("video"))
        if track_count:
            try:
                timeline.SetTrackName("video", track_count, "MSR AI Captions")
            except Exception:
                pass
    except Exception:
        pass

    fps = timeline_fps(timeline)
    start_frame = int(timeline.GetStartFrame())
    created = 0
    failed = 0

    for caption in captions:
        text = str(caption.get("text", "")).strip()
        if not text:
            continue

        start = float(caption.get("start", 0.0))
        end = float(caption.get("end", start + 1.0))
        if end <= start:
            end = start + 0.8

        in_frame = start_frame + max(0, int(math.floor(start * fps)))
        out_frame = start_frame + max(1, int(math.ceil(end * fps)))

        try:
            if not timeline.SetMarkInOut(in_frame, out_frame, "video"):
                failed += 1
                continue

            item = timeline.InsertFusionTitleIntoTimeline("Text+")
            if item is None:
                failed += 1
                continue

            if not set_text_plus(item, text.replace("\n", " ")):
                failed += 1
                continue

            set_text_plus_style(item)
            created += 1
        except Exception:
            failed += 1
        finally:
            try:
                timeline.ClearMarkInOut("video")
            except Exception:
                pass

    return {
        "ok": created > 0,
        "created": created,
        "failed": failed,
        "fps": fps,
        "track": track_count,
        "message": f"Created {created} Text+ overlay captions; {failed} failed.",
    }
