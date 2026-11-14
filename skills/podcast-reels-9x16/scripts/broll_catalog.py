# -*- coding: utf-8 -*-
"""Catalogue a folder of raw b-roll (his phone exports, a client drop) so clips can be picked by eye:
duration / size / orientation / shot date per file into catalog.json, one frame per clip at 30 %,
and numbered contact sheets (48 per sheet) to look at before choosing anything.

    python broll_catalog.py "<folder>" --out <workdir> [--per-sheet 48] [--min-dur 0.8]

The number on each tile is the index in catalog.json (`items[i]`). Photos (.heic/.jpg/.png) are listed
with kind "photo" and get a tile too (ffmpeg decodes HEIC here); a video under --min-dur is listed but
gets no tile. Re-running only probes files not yet in catalog.json (the export can still be running).
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import paths
from PIL import Image, ImageDraw, ImageFont
FF = str(paths.FFMPEG)
ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--out", required=True); ap.add_argument("--per-sheet", type=int, default=48); ap.add_argument("--min-dur", type=float, default=0.8)
A = ap.parse_args(); root = Path(A.folder).expanduser(); out = Path(A.out).expanduser(); out.mkdir(parents=True, exist_ok=True); thumbs = out / "thumbs"; thumbs.mkdir(exist_ok=True)
cat_path = out / "catalog.json"; cat = json.loads(cat_path.read_text()) if cat_path.exists() else {"root": str(root), "items": []}
known = {it["path"] for it in cat["items"]}
VID = (".mov", ".mp4", ".m4v"); PHO = (".heic", ".jpg", ".jpeg", ".png")
files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VID + PHO and not p.name.startswith("."))
def probe(p):
    r = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else 0.0
    wh = re.search(r"Video: .*? (\d{2,5})x(\d{2,5})", r); w, h = (int(wh.group(1)), int(wh.group(2))) if wh else (0, 0)
    rot = re.search(r"rotation of (-?[\d.]+)|displaymatrix: rotation of (-?[\d.]+)", r)
    if rot and abs(float(rot.group(1) or rot.group(2))) in (90.0, 270.0): w, h = h, w
    ct = re.search(r"creation_time\s*:\s*(\S+)", r); fps = re.search(r"([\d.]+) fps", r)
    return dur, w, h, (ct.group(1) if ct else ""), (float(fps.group(1)) if fps else 0.0)
new = 0
for p in files:
    rel = str(p.relative_to(root))
    if rel in known: continue
    dur, w, h, ct, fps = probe(p); kind = "video" if p.suffix.lower() in VID else "photo"; i = len(cat["items"])
    it = {"i": i, "path": rel, "album": p.parent.name, "kind": kind, "dur": round(dur, 2), "w": w, "h": h, "orient": "portrait" if h > w else ("landscape" if w > h else "square"), "fps": fps, "shot": ct[:19].replace("T", " "), "size_mb": round(p.stat().st_size / 1e6, 1)}
    tp = thumbs / f"{i:04d}.jpg"
    if kind == "photo" or dur >= A.min_dur:
        args = [FF, "-y", "-loglevel", "error"] + (["-ss", f"{dur * 0.3:.2f}"] if kind == "video" else []) + ["-i", str(p), "-frames:v", "1", "-vf", "scale=360:-2", str(tp)]
        subprocess.run(args, capture_output=True); it["thumb"] = tp.name if tp.exists() else ""
    else: it["thumb"] = ""
    cat["items"].append(it); new += 1
    print(f"  {i:4d} {kind:5} {dur:6.1f}s {w}x{h} {it['shot'][:10]} {rel}")
cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=1))
# contact sheets, rebuilt from scratch (cheap)
for f in out.glob("sheet_*.jpg"): f.unlink()
items = [it for it in cat["items"] if it.get("thumb")]; cols, TW, TH = 6, 360, 300
try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
except Exception: font = ImageFont.load_default()
for s in range(0, len(items), A.per_sheet):
    chunk = items[s:s + A.per_sheet]; rows = (len(chunk) + cols - 1) // cols; sheet = Image.new("RGB", (cols * TW, rows * TH), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
    for k, it in enumerate(chunk):
        x, y = (k % cols) * TW, (k // cols) * TH
        try:
            im = Image.open(thumbs / it["thumb"]).convert("RGB"); im.thumbnail((TW - 8, TH - 44)); sheet.paste(im, (x + 4 + (TW - 8 - im.width) // 2, y + 4))
        except Exception: pass
        lab = f"{it['i']}  {it['dur']:.0f}s {'P' if it['orient']=='portrait' else 'L'} {it['shot'][:7]}" if it["kind"] == "video" else f"{it['i']}  photo {'P' if it['orient']=='portrait' else 'L'}"
        dr.rectangle([x, y + TH - 40, x + TW, y + TH], fill=(0, 0, 0)); dr.text((x + 8, y + TH - 38), lab, fill=(255, 220, 80), font=font)
    sheet.save(out / f"sheet_{s // A.per_sheet:02d}.jpg", quality=82)
vids = [it for it in cat["items"] if it["kind"] == "video"]
print(f"catalog {len(cat['items'])} items (+{new}) | videos {len(vids)} ({sum(1 for v in vids if v['orient']=='portrait')} portrait) | sheets {len(list(out.glob('sheet_*.jpg')))} in {out}")
