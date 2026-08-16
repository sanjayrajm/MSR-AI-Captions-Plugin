from pathlib import Path

def srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    total = int(seconds)
    ms = int(round((seconds - total) * 1000))
    if ms >= 1000:
        total += 1
        ms = 0
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(segments, path):
    blocks = []
    for i, s in enumerate(segments, 1):
        blocks.append(
            f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n"
        )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(blocks), encoding="utf-8-sig")
    return str(p)
