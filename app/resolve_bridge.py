from __future__ import annotations

import os
import sys
from pathlib import Path

RESOLVE_SCRIPT_API = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
RESOLVE_MODULES = RESOLVE_SCRIPT_API / "Modules"
RESOLVE_SCRIPT_LIB = Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")

for p in (RESOLVE_SCRIPT_API, RESOLVE_MODULES):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
os.environ["RESOLVE_SCRIPT_API"] = str(RESOLVE_SCRIPT_API)
if RESOLVE_SCRIPT_LIB.exists():
    os.environ["RESOLVE_SCRIPT_LIB"] = str(RESOLVE_SCRIPT_LIB)


def _float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


class ResolveBridge:
    def __init__(self):
        self.resolve = None
        self.connected = False
        self.error = None
        self._connect()

    def _connect(self):
        try:
            import DaVinciResolveScript as dvr_script
            self.resolve = dvr_script.scriptapp("Resolve")
            if self.resolve is None:
                raise RuntimeError("DaVinci Resolve scripting API returned None.")
            self.connected = True
        except Exception as exc:
            self.resolve = None
            self.connected = False
            self.error = str(exc)

    def project(self):
        if not self.connected:
            return None
        try:
            return self.resolve.GetProjectManager().GetCurrentProject()
        except Exception:
            return None

    def media_pool(self):
        project = self.project()
        if not project:
            return None
        try:
            return project.GetMediaPool()
        except Exception:
            return None

    def timeline(self):
        project = self.project()
        if not project:
            return None
        try:
            return project.GetCurrentTimeline()
        except Exception:
            return None

    def project_name(self):
        p = self.project()
        try:
            return p.GetName() if p else "No Project"
        except Exception:
            return "Unknown Project"

    def timeline_name(self):
        t = self.timeline()
        try:
            return t.GetName() if t else "No Timeline"
        except Exception:
            return "Unknown Timeline"

    def timeline_fps(self):
        t = self.timeline()
        if not t:
            return 25.0
        try:
            return _float(t.GetSetting("timelineFrameRate"), 25.0)
        except Exception:
            return 25.0

    def timeline_start_frame(self):
        t = self.timeline()
        if not t:
            return 0
        try:
            return int(t.GetStartFrame())
        except Exception:
            return 0

    def video_clips(self):
        t = self.timeline()
        if not t:
            return []
        result = []
        try:
            count = int(t.GetTrackCount("video"))
        except Exception:
            return []
        for track in range(1, count + 1):
            try:
                items = t.GetItemListInTrack("video", track) or []
            except Exception:
                continue
            for item in items:
                try:
                    mpi = item.GetMediaPoolItem()
                    if not mpi:
                        continue
                    props = mpi.GetClipProperty() or {}
                    path = props.get("File Path") or props.get("FilePath") or ""
                    if not path:
                        continue
                    result.append({
                        "track": track,
                        "name": item.GetName() or Path(path).name,
                        "path": path,
                        "timeline_start": _float(item.GetStart()),
                        "timeline_end": _float(item.GetEnd()),
                    })
                except Exception:
                    continue
        return sorted(result, key=lambda x: (x["timeline_start"], x["track"]))

    def subtitle_track_count(self):
        t = self.timeline()
        if not t:
            return 0
        try:
            return int(t.GetTrackCount("subtitle"))
        except Exception:
            return 0

    def ensure_subtitle_track(self):
        t = self.timeline()
        if not t:
            raise RuntimeError("No active Resolve timeline.")
        count = self.subtitle_track_count()
        if count:
            return count
        try:
            ok = t.AddTrack("subtitle")
        except Exception as exc:
            raise RuntimeError(f"Resolve could not create a subtitle track: {exc}") from exc
        if not ok or self.subtitle_track_count() <= 0:
            raise RuntimeError("Resolve did not create a subtitle track.")
        return self.subtitle_track_count()

    def import_srt_to_media_pool(self, srt_path):
        pool = self.media_pool()
        path = Path(srt_path).resolve()
        if not pool:
            raise RuntimeError("Resolve Media Pool is unavailable.")
        if not path.exists():
            raise FileNotFoundError(f"SRT file not found: {path}")
        errors = []
        try:
            result = pool.ImportMedia([str(path)])
            if result:
                return result[0]
        except Exception as exc:
            errors.append(f"ImportMedia: {exc}")
        try:
            result = self.resolve.GetMediaStorage().AddItemListToMediaPool([str(path)])
            if result:
                return result[0]
        except Exception as exc:
            errors.append(f"AddItemListToMediaPool: {exc}")
        # Resolve may import the item without returning it.
        try:
            root = pool.GetRootFolder()
            for item in (root.GetClipList() or []):
                try:
                    if (item.GetName() or "").lower() == path.name.lower():
                        return item
                    props = item.GetClipProperty() or {}
                    fp = props.get("File Path") or props.get("FilePath") or ""
                    if fp and Path(fp).resolve() == path:
                        return item
                except Exception:
                    continue
        except Exception as exc:
            errors.append(f"Media Pool search: {exc}")
        raise RuntimeError("Resolve could not import the generated SRT into the Media Pool.\n\n" + "\n".join(errors))

    def append_subtitle_to_timeline(self, subtitle_item, record_frame):
        pool = self.media_pool()
        timeline = self.timeline()
        if not pool or not timeline:
            raise RuntimeError("Resolve Media Pool or timeline is unavailable.")
        track = self.ensure_subtitle_track()
        end_frame = 1
        try:
            props = subtitle_item.GetClipProperty() or {}
            for key in ("Frames", "Duration", "Frame Count"):
                if props.get(key):
                    n = int(_float(props[key], 1))
                    if n > 1:
                        end_frame = n - 1
                        break
        except Exception:
            pass
        errors = []
        attempts = [
            {"mediaPoolItem": subtitle_item, "startFrame": 0, "endFrame": max(1, end_frame), "trackIndex": track, "recordFrame": int(record_frame)},
            {"mediaPoolItem": subtitle_item, "startFrame": 0, "endFrame": max(1, end_frame), "recordFrame": int(record_frame)},
        ]
        for info in attempts:
            try:
                result = pool.AppendToTimeline([info])
                if result:
                    return {"timeline_items": result, "subtitle_track": track, "record_frame": int(record_frame)}
            except Exception as exc:
                errors.append(str(exc))
        try:
            result = pool.AppendToTimeline([subtitle_item])
            if result:
                return {"timeline_items": result, "subtitle_track": track, "record_frame": int(record_frame)}
        except Exception as exc:
            errors.append(str(exc))
        raise RuntimeError("Resolve imported the SRT but could not place it on the subtitle track.\n\n" + "\n".join(errors))

    def import_and_place_srt(self, srt_path, clip=None):
        if not self.connected:
            return {"success": False, "error": "DaVinci Resolve is not connected."}
        if not self.timeline():
            return {"success": False, "error": "There is no active Resolve timeline."}
        try:
            item = self.import_srt_to_media_pool(srt_path)
            frame = int(_float((clip or {}).get("timeline_start", self.timeline_start_frame())))
            placement = self.append_subtitle_to_timeline(item, frame)
            return {"success": True, "media_pool_item": item, **placement, "error": None}
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def status(self):
        return {
            "connected": self.connected,
            "project": self.project_name() if self.connected else "Not connected",
            "timeline": self.timeline_name() if self.connected else "Not connected",
            "error": self.error,
        }
