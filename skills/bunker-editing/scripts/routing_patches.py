#!/usr/bin/env python3
"""Routing misses (routing_audit.py) → exact patches for build_session_episode.py --patches.

    routing_patches.py <session> --keep 1,3,4,5,13,20,21,22,23 [--out <session>/פרק/תיקוני-ניתוב.json]

--keep: miss numbers that stay as they are (a real reaction — a laugh — or the listener starting to talk), chosen by
eye from the frames of every miss. For the rest, each edge snaps to the «מקור» cut nearby (10 fps frame-difference
peak within 0.6 s); an edge with no cut (the speaker started mid-shot) goes to the speaker's first word − 0.1 s.
Writes [[cam, from_s, to_s], …] — cam = the speaker's camera (--mic-cam 1=1,2=2,3=2 when two speakers share a camera).
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg")


def cut_near(src, t, lo, hi):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0, t + lo):.3f}", "-t", f"{hi - lo:.3f}", "-i", src, "-vf", "fps=10,scale=96:54,format=gray",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE, check=True).stdout
    x = np.frombuffer(raw, dtype=np.uint8).astype(np.float32).reshape(-1, 54 * 96)
    if len(x) < 3:
        return None
    d = np.abs(np.diff(x, axis=0)).mean(1)
    k = int(np.argmax(d))
    return round(max(0, t + lo) + (k + 1) / 10, 2) if d[k] > 4 * (np.median(d) + 1) and d[k] > 12 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--keep", default=""); ap.add_argument("--out"); ap.add_argument("--mic-cam", default="")
    o = ap.parse_args()
    S = Path(o.session)
    ing = json.loads((S / "ingest.json").read_text())
    misses = json.loads((S / "פרק/ניתוב.json").read_text())["misses"]
    words = json.loads((S / "תמלול/transcript.json").read_text())["words"]
    keep = {int(k) for k in o.keep.split(",") if k.strip()}
    cam_of = {int(k): int(v) for k, v in (kv.split("=") for kv in o.mic_cam.split(",") if kv)}
    out = []
    for i, m in enumerate(misses):
        if i in keep:
            continue
        a = cut_near(ing["source"], m["from"], -0.6, 0.1)
        if a is None:
            w = next((w for w in words if w["mic"] == m["speaker"] and m["from"] - 0.6 <= w["start_s"] <= m["to"]), None)
            a = round((w["start_s"] if w else m["from"]) - 0.1, 2)
        b = cut_near(ing["source"], m["to"], -0.6, 0.2) or round(m["to"] - 0.25, 2)
        if b - a >= 0.8:
            cam = cam_of.get(m["speaker"], m["speaker"])
            out.append([cam, a, b])
            print(f"#{i:2d}  cam{cam}  {a:7.2f}–{b:7.2f}  (audit {m['from']}–{m['to']})")
    p = Path(o.out) if o.out else S / "פרק" / "תיקוני-ניתוב.json"
    p.write_text(json.dumps(out))
    print(f"{len(out)} patches → {p}")


if __name__ == "__main__":
    main()
