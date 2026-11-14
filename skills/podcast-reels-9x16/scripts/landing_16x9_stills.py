"""composite stills straight from the written draft: multicam camera per shot, outer scale/position keyframes,
captions + titles (calibrated: px = PIL@60 × size/10 on the 1080-high canvas), b-roll, logo, name card"""
import json, os, sys, io, subprocess, re
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
from PIL import Image, ImageDraw, ImageFont
SP = os.path.dirname(os.path.abspath(__file__)); US = 1e6
NAME = os.environ.get("DRAFT", "0919"); d = capcut.load_draft(NAME); mats = d["materials"]
byid = {m["id"]: m for k, v in mats.items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
drafts = {x["id"]: x["draft"] for x in mats["drafts"]}
FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/")
def font(path, size): return ImageFont.truetype(path, max(int(round(6 * size * 1920 / 1080)), 8))  # 6 px/unit was calibrated on a 1080-wide canvas; this one is 1920 wide
def interp(seg, prop, t_src_us, default):
    g = next((g for g in seg.get("common_keyframes", []) if g["property_type"] == prop), None)
    if not g: return default
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if t_src_us <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if t_src_us >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= t_src_us <= b["time_offset"]:
            f = (t_src_us - a["time_offset"]) / max(1, b["time_offset"] - a["time_offset"]); return a["values"][0] + f * (b["values"][0] - a["values"][0])
DRAFTDIR = str(capcut.DRAFTS_DIR / NAME)
def _resolve(p):
    return re.sub(r"^##_draftpath_placeholder_[^#]*_##", DRAFTDIR, p or "")
def grab(path, t):
    path = _resolve(path)
    for attempt in range(3):                                                # a frame off the external drive occasionally comes back empty; ask again
        out = subprocess.run([str(paths.FFMPEG), "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if out: return Image.open(io.BytesIO(out)).convert("RGBA")
    raise RuntimeError(f"no frame from {path} at {t:.2f}s after 3 attempts")
def place(canvas, im, scale, tx, ty, W=1920, H=1080):
    ar = im.width / im.height; rw = W * scale if ar >= W / H else H * scale * ar; rh = rw / ar
    im = im.resize((max(1, int(rw)), max(1, int(rh)))); cx, cy = W / 2 + tx * W / 2, H / 2 - ty * H / 2
    canvas.alpha_composite(im, (int(cx - rw / 2), int(cy - rh / 2)))
def frame(t):
    canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255)); info = []
    for ti, tr in enumerate(d["tracks"]):
        if tr["type"] not in ("video",): continue
        for s in tr["segments"]:
            a = s["target_timerange"]["start"] / US; b = a + s["target_timerange"]["duration"] / US
            if not (a <= t < b): continue
            m = byid[s["material_id"]]; rel = t - a; src_us = s["source_timerange"]["start"] + rel * US
            sc = interp(s, "KFTypeScaleX", src_us, s["clip"]["scale"]["x"]); px = interp(s, "KFTypePositionX", src_us, s["clip"]["transform"]["x"]); py = interp(s, "KFTypePositionY", src_us, s["clip"]["transform"]["y"])
            dref = next((r for r in s["extra_material_refs"] if r in drafts), None)
            if dref:
                nd = drafts[dref]; cam = m["multi_camera_info"]["cur_camera_track_id"]; nv = {x["id"]: x for x in nd["materials"]["videos"]}
                ntr = next(x for x in nd["tracks"] if x["id"] == cam); ns = ntr["segments"][0]; nm = nv[ns["material_id"]]
                inner = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255)); place(inner, grab(nm["path"], ns["source_timerange"]["start"] / US + src_us / US), ns["clip"]["scale"]["x"], ns["clip"]["transform"]["x"], ns["clip"]["transform"]["y"])
                place(canvas, inner, sc, px, py); info.append(f"cam{'1' if os.path.basename(nm['path']).rstrip('.mp4')[-1]=='1' else '2'} ×{sc:.3f}")
            elif m.get("type") == "photo":
                im = Image.open(m["path"].replace("##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##", str(capcut.DRAFTS_DIR / "0919"))).convert("RGBA") if "##" in m["path"] else Image.open(m["path"]).convert("RGBA")
                if m["width"] == 300: canvas.paste((255, 255, 255, 255), (0, 0, 1920, 1080)); info.append("white card"); continue
                place(canvas, im, sc, px, py); info.append(tr.get("name", ""))
            else:
                place(canvas, grab(m["path"], src_us / US), sc, px, py); info.append(f"{tr.get('name','')} ×{sc:.3f}")
    dr = ImageDraw.Draw(canvas)
    for tr in d["tracks"]:
        if tr["type"] != "text": continue
        for s in tr["segments"]:
            a = s["target_timerange"]["start"] / US; b = a + s["target_timerange"]["duration"] / US
            if not (a <= t < b): continue
            m = byid[s["material_id"]]; c = json.loads(m["content"]); text = c["text"]; sc = interp(s, "KFTypeScaleX", (t - a) * US, s["clip"]["scale"]["x"])
            # draw per style range (RTL: lay out runs right-to-left)
            runs = []
            for st in c["styles"]:
                seg_txt = text[st["range"][0]:st["range"][1]]
                if not seg_txt: continue
                f = font(st["font"]["path"], st["size"] * sc); col = tuple(int(255 * v) for v in st["fill"]["content"]["solid"]["color"]) + (int(255 * m.get("global_alpha", 1.0)),)
                runs.append((seg_txt, f, col))
            total = sum(f.getlength(tx) for tx, f, col in runs); cx = 960 + s["clip"]["transform"]["x"] * 960; cy = 540 - s["clip"]["transform"]["y"] * 540
            x = cx + total / 2
            for tx, f, col in runs:
                w = f.getlength(tx); x -= w; dr.text((x, cy), tx, font=f, fill=col, anchor="lm", stroke_width=max(1, int(f.size * 0.06)), stroke_fill=(0, 0, 0, 255))
            info.append(f"txt[{tr['name']}] {text[:22]!r}")
    dr.text((16, 12), f"{t:.2f}s  " + " | ".join(info), font=ImageFont.truetype(FONTS + "Assistant-Regular.ttf", 26), fill=(255, 255, 0, 255))
    return canvas.convert("RGB")
ts = [float(x) for x in sys.argv[1:]] or [2.8, 8.5, 20.5, 32.5, 61.0, 116.5, 137.0, 208.0, 226.5, 268.0, 306.0, 316.0]
cols = 3; rows = (len(ts) + cols - 1) // cols; sheet = Image.new("RGB", (640 * cols, 360 * rows))
for i, t in enumerate(ts): sheet.paste(frame(t).resize((640, 360)), ((i % cols) * 640, (i // cols) * 360))
OUT = os.path.expanduser(os.environ.get("WORK", SP)); sheet.save(f"{OUT}/{NAME}_stills.png"); print("stills:", ts)
