# -*- coding: utf-8 -*-
"""Composite stills of a 9:16 reels draft at given times — the picture as CapCut will lay it out
(both camera layers through their alpha, scale/position keyframes evaluated, white cards, title
and caption text drawn with the real font), tiled into one sheet. A still is not a render; it is
the check that catches a wrong framing, a caption on a chin or an empty card before Alon does.

    python reel_stills.py "<project>" out.png 6.0 12.5 …        # times in timeline seconds
"""
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
from PIL import Image, ImageDraw, ImageFont
NAME, OUT, *TS = sys.argv[1:]; TS = [float(x) for x in TS]; US = 1e6
D = capcut.DRAFTS_DIR / NAME; d = capcut.load_draft(NAME)
vm = {m["id"]: m for m in d["materials"]["videos"]}; tm = {m["id"]: m for m in d["materials"]["texts"]}
res = lambda p: os.path.join(D, os.path.basename(re.sub(r"##_draftpath_placeholder_[^#]+_##/?", "", p))) if "draftpath_placeholder" in p or os.path.exists(os.path.join(D, os.path.basename(p))) else p
def seg_at(tr, T): return next((s for s in tr["segments"] if s["target_timerange"]["start"] <= T * US < s["target_timerange"]["start"] + s["target_timerange"]["duration"]), None)
def ease(f): return f * f * (3 - 2 * f)
def kv(s, prop, src_t, default):
    g = next((g for g in s.get("common_keyframes", []) if g["property_type"] == prop), None)
    if not g or not g["keyframe_list"]: return default
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if src_t <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if src_t >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= src_t <= b["time_offset"]:
            f = (src_t - a["time_offset"]) / (b["time_offset"] - a["time_offset"]); f = ease(f) if a.get("curveType", "Line") != "Line" else f
            return a["values"][0] + f * (b["values"][0] - a["values"][0])
def rtl(text): return " ".join(t if re.search(r"[A-Za-z0-9]", t) else t[::-1] for t in reversed(text.split(" ")))
def grab(path, t):
    out = subprocess.run([str(paths.FFMPEG), "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    import io; im = Image.open(io.BytesIO(out)); return im.convert("RGBA") if im.mode in ("RGBA", "LA") else im.convert("RGB")   # a ProRes 4444 title keeps its alpha (r8)
def place(canvas, im, sc, tx, ty):
    W = int(1080 * sc); H = int(W * im.height / im.width); im2 = im.resize((max(1, W), max(1, H)))
    canvas.paste(im2, (int(540 + tx * 540 - W / 2), int(960 - ty * 960 - H / 2)), im2 if im2.mode == "RGBA" else None)   # a logo PNG keeps its transparency
def frame(T):
    canvas = Image.new("RGB", (1080, 1920), "black"); info = []
    for tr in [t for t in d["tracks"] if t["type"] == "video"]:
        s = seg_at(tr, T)
        if not s: continue
        m = vm[s["material_id"]]; a = (s.get("clip") or {}).get("alpha", 1)
        if a < 0.5: continue
        if m.get("type") == "photo":
            if m.get("width") == 300 or "card" in m.get("path", ""): canvas.paste((255, 255, 255), (0, 0, 1080, 1920)); info.append("card"); continue
            im = Image.open(res(m["path"])); im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB"); place(canvas, im, s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]); info.append("photo"); continue
        src_t = s["source_timerange"]["start"] + (T * US - s["target_timerange"]["start"])
        sc = kv(s, "KFTypeScaleX", src_t, s["clip"]["scale"]["x"]); tx = kv(s, "KFTypePositionX", src_t, s["clip"]["transform"]["x"]); ty = kv(s, "KFTypePositionY", src_t, s["clip"]["transform"]["y"])
        place(canvas, grab(res(m["path"]), src_t / US), sc, tx, ty); info.append(f"{os.path.basename(m['path'])[-9:-4]} ×{sc:.2f}")
    dr = ImageDraw.Draw(canvas)
    for tr in [t for t in d["tracks"] if t["type"] == "text"]:
        s = seg_at(tr, T)
        if not s: continue
        m = tm[s["material_id"]]; c = json.loads(m["content"]); st = c["styles"][0]
        size = st.get("size", 20); fpath = (st.get("font") or {}).get("path") or os.path.expanduser("~/Library/Fonts/bamberger-grunge-bold-fm.ttf")
        col = tuple(int(255 * v) for v in ((st.get("fill") or {}).get("content", {}).get("solid", {}).get("color") or [1, 1, 1]))
        px = max(8, int(6 * size * s["clip"]["scale"]["x"])); font = ImageFont.truetype(fpath, px)
        lines = c["text"].split("\n"); lh = px * 1.15; total = lh * len(lines); y0 = 960 - s["clip"]["transform"]["y"] * 960 - total / 2
        for i, ln in enumerate(lines):
            t = rtl(ln); w = font.getlength(t); x = 540 + s["clip"]["transform"]["x"] * 540 - w / 2
            dr.text((x, y0 + i * lh), t, font=font, fill=col, stroke_width=max(1, px // 12) if col != (18, 18, 18) else 0, stroke_fill=(0, 0, 0))
        info.append("txt:" + c["text"][:16].replace("\n", "/"))
    dr.line([(540, 0), (540, 1920)], fill=(255, 255, 0), width=1)
    dr.text((10, 10), f"{T:.2f}s " + " | ".join(info), fill=(255, 255, 0), font=ImageFont.truetype(os.path.expanduser("~/Library/Fonts/bamberger-grunge-bold-fm.ttf"), 26))
    return canvas
cols = min(4, len(TS)); rows = (len(TS) + cols - 1) // cols; W, H = 540, 960
sheet = Image.new("RGB", (W * cols, H * rows), (30, 30, 30))
for i, T in enumerate(TS): sheet.paste(frame(T).resize((W, H)), ((i % cols) * W, (i // cols) * H))
sheet.save(OUT); print("stills:", OUT, TS)
