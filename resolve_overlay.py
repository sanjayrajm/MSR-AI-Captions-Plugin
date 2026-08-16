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


def iter_tools(tools):
    if hasattr(tools, "items"):
        return [tool for _, tool in tools.items()]
    if isinstance(tools, (list, tuple)):
        return list(tools)
    return [tools]


def set_text_plus(item, text: str) -> bool:
    try:
        comp = item.GetFusionCompByIndex(1)
        tools = iter_tools(comp.GetToolList())
        for tool in tools:
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
        pass
    return False


def set_text_plus_style(item, font="Noto Sans", size=0.055):
    try:
        comp = item.GetFusionCompByIndex(1)
        for tool in iter_tools(comp.GetToolList()):
            for key, value in (
                ("Font", font),
                ("Size", size),
                ("HorizontalJustification", 1),
            ):
                try:
                    tool.SetInput(key, value)
                except Exception:
                    pass
            break
    except Exception:
        pass


def add_text_plus_overlays(resolve, captions: Iterable[dict]) -> dict:
    """Create editable Text+ clips using Gemini caption timing.

    Each caption becomes a real Resolve timeline overlay. SetMarkInOut is
    used before InsertFusionTitleIntoTimeline so the title duration follows
    the caption timing instead of appearing in the MSR dashboard.
    """
    project = resolve.GetProjectManager().GetCurrentProject()
    if not project:
        return {"ok": False, "created": 0, "failed": 0, "message": "No current project."}

    timeline = project.GetCurrentTimeline()
    if not timeline:
        return {"ok": False, "created": 0, "failed": 0, "message": "No current timeline."}

    # Add a dedicated video track where Resolve permits it. The API does not
    # expose a universal 'select active video track' call, so Resolve decides
    # the insertion target for InsertFusionTitleIntoTimeline.
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
    timeline_start = int(timeline.GetStartFrame())
    created = 0
    failed = 0

    for caption in captions:
        text = str(caption.get("text", "")).strip()
        if not text:
            continue

        start = max(0.0, float(caption.get("start", 0.0)))
        end = float(caption.get("end", start + 0.8))
        if end <= start:
            end = start + 0.8

        in_frame = timeline_start + int(math.floor(start * fps))
        out_frame = timeline_start + max(
            int(math.ceil(end * fps)),
            int(math.floor(start * fps)) + 1,
        )

        try:
            mark_ok = timeline.SetMarkInOut(in_frame, out_frame, "video")
            if mark_ok is False:
                failed += 1
                continue

            item = timeline.InsertFusionTitleIntoTimeline("Text+")
            if item is None:
                failed += 1
                continue

            if not set_text_plus(item, text):
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
        "ok": created > 0 and failed == 0,
        "created": created,
        "failed": failed,
        "fps": fps,
        "track": track_count,
        "message": f"Created {created} Text+ overlay captions; {failed} failed.",
    }
