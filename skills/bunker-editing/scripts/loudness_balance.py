#!/usr/bin/env python3
"""Even loudness across a project (תוכן הבונקר לממומן, 25.10.2026: «ודא שהסאונד מאוזן לאורך הפרק»).

    loudness_balance.py "<project>" --target -16 [--track דיבור] [--write]

The dialogue track's segments are grouped into videos (a gap > 1.5 s starts a new one); each video is rendered as it plays
(source ranges × segment volume) and measured (EBU R128 integrated); every segment of that video gets the gain that brings
it to --target. Pops/SFX are reported against the dialogue (short-term peak). CapCut must be closed for --write.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402
import numpy as np

FF = str(Path.home() / "ffmpeg-bin/ffmpeg"); US = 1_000_000; SR = 48000


def lufs(x):
    p = Path(__import__("tempfile").gettempdir()) / "_lufs.f32"
    x.astype(np.float32).tofile(p)
    r = subprocess.run([FF, "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return float(i[-1]) if i else -70.0, float(pk[-1]) if pk else -70.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--target", type=float, default=-16.0); ap.add_argument("--track", default="דיבור")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    mats = {m["id"]: m for m in d["materials"].get("audios", [])}
    st = lambda s: s["target_timerange"]["start"]; en = lambda s: st(s) + s["target_timerange"]["duration"]
    segs = sorted([s for t in d["tracks"] if t["type"] == "audio" and t.get("name") == a.track for s in t["segments"]], key=st)
    groups, cur = [], []
    for s in segs:
        if cur and st(s) - en(cur[-1]) > 1.5 * US:
            groups.append(cur); cur = []
        cur.append(s)
    if cur:
        groups.append(cur)
    cache = {}
    def read(path, a0, du):
        raw = subprocess.run([FF, "-v", "error", "-ss", f"{a0:.4f}", "-t", f"{du:.4f}", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        return np.frombuffer(raw, np.float32)
    report = []
    for g in groups:
        x = np.concatenate([read(re.sub(r"##_draftpath_placeholder_[0-9A-F-]+_##", str(P), mats[s["material_id"]]["path"]),
                                 s["source_timerange"]["start"] / US, s["source_timerange"]["duration"] / US) * s.get("volume", 1.0) for s in g])
        L, pk = lufs(x)
        gain = 10 ** ((a.target - L) / 20)
        gain = min(gain, 10 ** ((-1.5 - pk) / 20)) if pk + 20 * np.log10(gain) > -1.5 else gain   # never above −1.5 dBFS peak
        report.append({"start": round(st(g[0]) / US, 1), "lufs": round(L, 1), "gain_db": round(20 * np.log10(gain), 1)})
        for s in g:
            s["volume"] = round(s.get("volume", 1.0) * gain, 4)
    print(json.dumps(report, ensure_ascii=False))
    if a.write:
        if capcut.capcut_running():
            raise SystemExit("⛔ CapCut פתוח")
        capcut._backup(P); capcut._atomic_write(P, d); print("✓ נכתב")


if __name__ == "__main__":
    main()
