from __future__ import annotations
import os, sys
from pathlib import Path

class ResolveBridge:
    """Connect to the DaVinci Resolve instance already running on this PC."""

    def __init__(self):
        self.resolve = None
        self.connected = False
        self._connect()

    def _connect(self):
        candidates = [
            Path(os.environ.get("RESOLVE_SCRIPT_API", "")),
            Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionsdk"),
            Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting"),
        ]
        for p in candidates:
            if str(p) and p.exists() and str(p) not in sys.path:
                sys.path.insert(0, str(p))
        try:
            import DaVinciResolveScript as dvr_script
            self.resolve = dvr_script.scriptapp("Resolve")
            self.connected = self.resolve is not None
        except Exception:
            self.resolve = None
            self.connected = False

    def project(self):
        if not self.connected:
            return None
        return self.resolve.GetProjectManager().GetCurrentProject()

    def timeline(self):
        p = self.project()
        return p.GetCurrentTimeline() if p else None

    def project_name(self):
        p = self.project()
        return p.GetName() if p else "No Project"

    def timeline_name(self):
        t = self.timeline()
        return t.GetName() if t else "No Timeline"

    def timeline_fps(self):
        t = self.timeline()
        if not t:
            return 25.0
        try:
            return float(t.GetSetting("timelineFrameRate"))
        except Exception:
            return 25.0

    def video_clips(self):
        """Return video clips from the current Resolve timeline with source paths."""
        t = self.timeline()
        if not t:
            return []

        result = []
        for track in range(1, int(t.GetTrackCount("video")) + 1):
            for item in (t.GetItemListInTrack("video", track) or []):
                try:
                    mp = item.GetMediaPoolItem()
                    if not mp:
                        continue
                    props = mp.GetClipProperty()
                    path = props.get("File Path") or props.get("FilePath") or ""
                    if not path:
                        continue
                    start = float(item.GetStart())
                    end = float(item.GetEnd())
                    result.append({
                        "track": track,
                        "name": item.GetName() or Path(path).name,
                        "path": path,
                        "timeline_start": start,
                        "timeline_end": end,
                    })
                except Exception:
                    pass

        return sorted(result, key=lambda x: (x["timeline_start"], x["track"]))
