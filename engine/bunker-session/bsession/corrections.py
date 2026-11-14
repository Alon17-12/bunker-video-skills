"""The corrections prompt the Bunker copies out of the delivery's «תיקונים» tab (spec 2026-10-18, part ג׳) → a work list:
every note with its video, its time on the reel / episode clock, the «מקור» time and the words said there."""
import json, re
from pathlib import Path

ROUND = re.compile(r"סבב:\s*(.+?)\s*$", re.M)
HEAD = re.compile(r"^##\s+(.+?)\s*$")
REEL = re.compile(r"ריל\s+(\d+)\s*(?:[—–-]\s*(.*))?$")
ITEM = re.compile(r"^-\s*(?:(\d+(?::\d\d){0,2}(?:\.\d+)?)|כללי)\s*[—–-]\s*(.+?)\s*$")


def _secs(t: str) -> float:
    v = 0.0
    for part in t.split(":"):
        v = v * 60 + float(part)
    return v


def parse_prompt(text: str) -> dict:
    """Line by line, so nothing is dropped: a line under a note that is not a new note continues it (a client's
    multi-line note); a "- …" line that is not a readable note stops with the line itself (never a silent drop)."""
    videos, item = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if h := HEAD.match(line):
            m = REEL.match(h.group(1))
            if not m and h.group(1).strip() != "הפרק השלם":
                raise ValueError(f"כותרת {n} לא מוכרת: «{h.group(1)}» — צריך «הפרק השלם» או «ריל NN — כותרת»")
            target, title = (f"r{int(m.group(1))}", (m.group(2) or "").strip()) if m else ("episode", "הפרק השלם")
            videos.append({"target": target, "title": title, "items": []})
            item = None
            continue
        if not videos or not line:
            continue                                  # the header block before the first video, blank lines
        if m := ITEM.match(line):
            item = {"t": _secs(m.group(1)) if m.group(1) else None, "text": m.group(2)}
            videos[-1]["items"].append(item)
        elif line.startswith("-") or item is None:
            raise ValueError(f"שורה {n} בפרומפט התיקונים לא נקראת כהערה (צריך «- 0:24 — טקסט» או «- כללי — טקסט»): {line}")
        else:
            item["text"] += "\n" + line
    if not videos:
        raise ValueError("לא נמצאו סרטונים בפרומפט התיקונים (כותרות ##)")
    r = ROUND.search(text)
    return {"round": r.group(1) if r else "תיקונים", "videos": videos}


def _said(words, t, key_at, key_end, span=2.0):
    return " ".join(w["text"] for w in words if w[key_end] >= t - span and w[key_at] <= t + span)


def locate(session: Path, parsed: dict) -> list[dict]:
    s = Path(session)
    picks = {p["n"]: p for p in json.loads((s / "רילס/רילס.json").read_text(encoding="utf-8"))}
    rows = []
    for v in parsed["videos"]:
        for it in v["items"]:
            t = it["t"]
            if v["target"] == "episode":   # the exported episode starts at the trim: + trim_in → the «מקור» clock
                trim = json.loads((s / "פרק/פרויקט.json").read_text(encoding="utf-8"))["trim_in"]
                words = json.loads((s / "תמלול/transcript.json").read_text(encoding="utf-8"))["words"]
                src = None if t is None else round(t + trim, 3)
                said = "" if src is None else _said(words, src, "start_s", "end_s")
                rows.append({"target": "episode", "dir": "פרק", "t": t, "src": src, "said": said, "text": it["text"]})
                continue
            n = int(v["target"][1:])          # a delivered reel starts at the reel's first frame = the cut's clock
            p = picks.get(n, {"title": v["title"]})
            cut = json.loads((s / "רילס/remotion/public" / f"r{n}.json").read_text(encoding="utf-8"))
            src = None
            if t is not None:
                c = next((c for c in cut["clips"] if c["at"] <= t < c["end"]), cut["clips"][-1])
                src = round(c["src"] + (t - c["at"]), 3)
            said = "" if t is None else _said(cut["words"], t, "at", "end")
            rows.append({"target": v["target"], "dir": f"{n:02d} - {p['title']}", "t": t, "src": src, "said": said, "text": it["text"]})
    return rows
