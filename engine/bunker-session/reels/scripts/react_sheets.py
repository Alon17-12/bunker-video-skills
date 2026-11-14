#!/usr/bin/env python3
"""Reaction sheets: the LISTENER's face every 0.5 s while the other person talks (tsomet-20 reaction_sheets, for Remotion).
    react_sheets.py <session> → <session>/רילס/remotion/out/react_rN.jpg   (label = reel second; pick real reactions by eye)"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
from rpaths import listener_crop_x, session_paths
S, RM, PUB, WORK = session_paths(sys.argv)
(RM / "out").mkdir(parents=True, exist_ok=True)
SEL = json.loads((PUB / "selects.json").read_text())
FACE = json.loads((PUB / "face.json").read_text())
TMP = WORK / ".react"; TMP.mkdir(parents=True, exist_ok=True)       # per session: two sessions never share temp frames
sel = lambda t: next(w["at"] + t - w["from"] for w in SEL if w["from"] - 1e-3 <= t <= w["to"] + 1e-3)
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
for f in sorted(PUB.glob("r[0-9]*.json")):
    cut = json.loads(Path(f).read_text()); n = Path(f).stem
    tiles = []
    t = 0.0
    while t < cut["duration"]:
        ci = next((i for i, c in enumerate(cut["clips"]) if c["at"] <= t < c["end"]), None)
        talk = [w for w in cut["words"] if w["at"] - 0.3 <= t <= w["end"] + 0.3]
        if ci is not None and talk:
            who = talk[0]["who"]; lcam = 1 if who == "guest" else 2
            c = cut["clips"][ci]; src = c["src"] + t - c["at"]
            out = TMP / f"rs_{n}_{t:.1f}.jpg"
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{sel(src):.3f}", "-i", str(PUB / f"cam{lcam}s.mp4"), "-frames:v", "1",
                            "-vf", "crop=760:760:%d:0,scale=190:190" % listener_crop_x(FACE, lcam), str(out)], check=True)
            im = Image.open(out); d = ImageDraw.Draw(im); d.rectangle([0, 0, 70, 26], fill=(0, 0, 0)); d.text((4, 2), f"{t:.1f}", fill=(255, 255, 0) if lcam == 1 else (255, 255, 255), font=font)
            tiles.append(im); out.unlink()
        t += 0.5
    cols = 12; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 190, rows * 190))
    for i, im in enumerate(tiles): sheet.paste(im, ((i % cols) * 190, (i // cols) * 190))
    sheet.save(RM / "out" / f"react_{n}.jpg", quality=80); print(n, len(tiles), "tiles")
