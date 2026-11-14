#!/usr/bin/env python3
"""Grade only what the edits use: per camera, one "selects" file of the source windows the cuts read, with the LUT baked in.

    grade_windows.py --cut public/teaser.json --cut public/reel1.json … --cam 1="…/1.mp4" --cam 2="…/2.mp4" \
                     --lut Bunker.cube --out public --margin 1.0 [--extra 2084.0-2086.0]

Every clip of every cut json ({clips:[{at,end,src}]}) becomes a window [src-margin, src+len+margin]; windows are merged,
cut from the FULL-RES source with ffmpeg lut3d, and concatenated into public/cam{N}s.mp4 (keyframe every 0.5 s, so
seeks are instant). public/selects.json maps source time → selects time; src/selects.ts re-exports it for Remotion
(`sel(t)`), so every <Cam startFrom> goes through sel(). Grading a 62-min take took ~70 min and 11 GB (and the
renderer timed out seeking it); the windows of a teaser + 5 reels are a few minutes and grade in under a minute.
"""
import argparse
import json
import subprocess
from pathlib import Path

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", action="append", required=True)
    ap.add_argument("--cam", action="append", required=True, help='N="path"')
    ap.add_argument("--lut")
    ap.add_argument("--out", default="public")
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--extra", action="append", default=[], help="extra source window a-b (a split screen, a cutaway)")
    a = ap.parse_args()
    wins = []
    for f in a.cut:
        for c in json.loads(Path(f).read_text(encoding="utf-8"))["clips"]:
            wins.append([max(0.0, c["src"] - a.margin), c["src"] + (c["end"] - c["at"]) + a.margin])
    for e in a.extra:
        x, y = map(float, e.split("-"))
        wins.append([x - a.margin, y + a.margin])
    wins.sort()
    merged = []
    for w in wins:
        if merged and w[0] <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], w[1])
        else:
            merged.append(list(w))
    durs = None  # real part durations (frame-rounded) — offsets come from these, not from the requested lengths
    out = Path(a.out)
    vf = f"lut3d=file='{a.lut}':interp=tetrahedral" if a.lut else "null"
    for spec in a.cam:
        n, path = spec.split("=", 1)
        parts = []
        for i, (x, y) in enumerate(merged):
            p = out / f".sel{n}_{i:03d}.mp4"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{x:.3f}", "-t", f"{y - x:.3f}", "-i", path, "-vf", vf, "-an",
                            "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-g", "15", "-r", "30", str(p)], check=True)
            parts.append(p)
        if durs is None:
            durs = [float(subprocess.run([str(Path.home() / "ffmpeg-bin" / "ffprobe"), "-v", "error",
                    "-show_entries", "format=duration", "-of", "csv=p=0", str(q)], capture_output=True, text=True).stdout) for q in parts]
        lst = out / f".sel{n}.txt"
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
        subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out / f"cam{n}s.mp4")], check=True)
        for p in parts:
            p.unlink()
        lst.unlink()
        print(f"cam{n}s.mp4: {len(merged)} windows, {sum(durs):.1f}s")
    table, off = [], 0.0
    for (x, y), d in zip(merged, durs):
        table.append({"from": round(x, 3), "to": round(y, 3), "at": round(off, 3)})
        off += d
    (out / "selects.json").write_text(json.dumps(table, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
