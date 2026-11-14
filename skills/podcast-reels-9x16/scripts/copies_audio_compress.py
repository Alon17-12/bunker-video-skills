# -*- coding: utf-8 -*-
"""Compress the voice in a work copy so the export sits where the references sit (creator-styles.md §9:
−14…−16 LUFS integrated, LRA 1.5–8 — "voice compressed"). A gain-normalised mic is loud on average and
still soft between phrases; the references are flat.

    python copies_audio_compress.py "<draft>" --file ccstudio-bunker-cam1.mp4 [--target -16] [--ratio 3] [--threshold -22] [--write]

Two passes: compress and measure, then compress + trim to the target + limiter, re-mux with `-c:v copy`.
The original audio is kept in ~/Movies/reel-captions-work/<draft>-<name>.pre-compress.m4a. Read-only without --write.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("draft"); ap.add_argument("--file", required=True); ap.add_argument("--target", type=float, default=-16.0); ap.add_argument("--ratio", type=float, default=2.5)
ap.add_argument("--threshold", type=float, default=-18.0); ap.add_argument("--attack", type=float, default=6); ap.add_argument("--release", type=float, default=120); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.draft; mp4 = D / A.file
COMP = f"acompressor=threshold={A.threshold}dB:ratio={A.ratio}:attack={A.attack}:release={A.release}:makeup=0dB"
def measure(af):
    r = subprocess.run([FF, "-hide_banner", "-i", str(mp4), "-vn", "-af", f"{af},ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1])
i0, l0 = measure("anull"); i1, l1 = measure(COMP); trim = A.target - i1
chain = f"{COMP},volume={trim:.2f}dB,alimiter=limit=0.891:attack=5:release=50"
i2, l2 = measure(chain); trim += A.target - i2; chain = f"{COMP},volume={trim:.2f}dB,alimiter=limit=0.891:attack=5:release=50"; i2, l2 = measure(chain)
print(f"{mp4.name}: now {i0:.1f} LUFS / LRA {l0:.1f} → compressed {i1:.1f} / {l1:.1f} → trim {trim:+.1f} dB → {i2:.1f} LUFS / LRA {l2:.1f} (target {A.target})")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
bak = Path(os.path.expanduser("~/Movies/reel-captions-work")) / f"{A.draft}-{mp4.stem}.pre-compress.m4a"   # outside the draft folder: register_media would list it
if not bak.exists(): subprocess.run([FF, "-v", "error", "-y", "-i", str(mp4), "-vn", "-c:a", "copy", str(bak)], check=True)
tmp = mp4.with_suffix(".tmp.mp4")
subprocess.run([FF, "-v", "error", "-y", "-i", str(mp4), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", chain, "-c:a", "aac", "-b:a", "256k", str(tmp)], check=True)
os.replace(tmp, mp4); i3, l3 = measure("anull"); print(f"✓ written: {i3:.1f} LUFS / LRA {l3:.1f} (backup {bak.name})")
