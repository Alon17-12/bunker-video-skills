# -*- coding: utf-8 -*-
"""Three frames (10 / 50 / 90 %) of chosen catalog items on one sheet, to judge motion and framing before cutting.
    python broll_preview.py <catalog_dir> --idx 372,353,363 --out preview.jpg
"""
import argparse, json, subprocess, sys, os
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import paths
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("catalog"); ap.add_argument("--idx", required=True); ap.add_argument("--out", required=True); A = ap.parse_args()
cat = json.loads((Path(A.catalog) / "catalog.json").read_text()); root = Path(cat["root"]); items = {it["i"]: it for it in cat["items"]}
idx = [int(x) for x in A.idx.split(",")]; TW, TH = 240, 430; cols = 3
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
sheet = Image.new("RGB", (cols * TW + 20, len(idx) * TH), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
for r, i in enumerate(idx):
    it = items[i]; p = root / it["path"]
    for c, f in enumerate((0.1, 0.5, 0.9)):
        tp = Path(__import__("tempfile").gettempdir()) / f"pv_{i}_{c}.jpg"
        subprocess.run([str(paths.FFMPEG), "-y", "-loglevel", "error", "-ss", f"{it['dur'] * f:.2f}", "-i", str(p), "-frames:v", "1", "-vf", "scale=240:-2", str(tp)], capture_output=True)
        try: im = Image.open(tp).convert("RGB"); im.thumbnail((TW - 4, TH - 40)); sheet.paste(im, (c * TW + 2, r * TH + 2))
        except Exception: pass
    dr.text((4, r * TH + TH - 34), f"{i}  {it['dur']:.1f}s  {it['w']}x{it['h']}  {it['shot'][:10]}  {it['path'][-28:]}", fill=(255, 220, 80), font=font)
sheet.save(A.out, quality=85); print(A.out)
