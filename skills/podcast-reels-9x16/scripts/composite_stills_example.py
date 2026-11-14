import sys, subprocess, json, os
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths
from PIL import Image, ImageDraw, ImageFont
SP = os.path.dirname(os.path.abspath(__file__)); OUT = sys.argv[1]; times = [float(x) for x in sys.argv[2:]]
D = str(capcut.DRAFTS_DIR/"0910"); res = lambda p: os.path.join(D, os.path.basename(p)) if "draftpath_placeholder" in p else p
d = capcut.load_draft("0910"); vm = {m["id"]: m for m in d["materials"]["videos"]}; tm = {m["id"]: m for m in d["materials"]["texts"]}
LAT = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/Heebo-ExtraBold.ttf")
def seg_at(track, T): return next((s for s in track["segments"] if s["target_timerange"]["start"] <= T*1e6 < s["target_timerange"]["start"]+s["target_timerange"]["duration"]), None)
def ease(f): return f*f*(3-2*f)
def kf_val(s, prop, src_t, default):
    g = next((g for g in s.get("common_keyframes", []) if g["property_type"] == prop), None)
    if not g: return default
    ks = sorted(g["keyframe_list"], key=lambda k: k["time_offset"])
    if src_t <= ks[0]["time_offset"]: return ks[0]["values"][0]
    if src_t >= ks[-1]["time_offset"]: return ks[-1]["values"][0]
    for a, b in zip(ks, ks[1:]):
        if a["time_offset"] <= src_t <= b["time_offset"]:
            f = (src_t-a["time_offset"])/(b["time_offset"]-a["time_offset"]); f = ease(f) if a["curveType"] != "Line" else f
            return a["values"][0]+f*(b["values"][0]-a["values"][0])
def frame(T):
    s = seg_at(d["tracks"][0], T); m = vm[s["material_id"]]
    if m.get("type") == "photo": return Image.new("RGB", (1080,1920), "white"), "card"
    src_t = s["source_timerange"]["start"] + (T*1e6 - s["target_timerange"]["start"])
    sc = kf_val(s, "KFTypeScaleX", src_t, s["clip"]["scale"]["x"]); tx = kf_val(s, "KFTypePositionX", src_t, s["clip"]["transform"]["x"])
    out = f"{SP}/src_{T}.png"; subprocess.run([paths.FFMPEG,"-y","-loglevel","error","-ss",f"{src_t/1e6:.3f}","-i",res(m["path"]),"-frames:v","1",out],check=True)
    fr = Image.open(out).convert("RGB"); W = int(1080*sc); H = int(W*fr.height/fr.width); im = fr.resize((W,H))
    canvas = Image.new("RGB",(1080,1920),"black"); canvas.paste(im, (int(540+tx*540-W/2), int(960-H/2)))
    ImageDraw.Draw(canvas).line([(540,0),(540,1920)], fill=(255,255,0), width=2)
    for tr in d["tracks"][1:]:   # a full-frame b-roll overlay replaces the picture
        if tr["type"] != "video": continue
        b = seg_at(tr, T)
        if not b or vm[b["material_id"]].get("type") == "photo": continue
        bm = vm[b["material_id"]]; bt = b["source_timerange"]["start"] + (T*1e6 - b["target_timerange"]["start"])
        bsc = kf_val(b, "KFTypeScaleX", bt, b["clip"]["scale"]["x"]); out = f"{SP}/broll_{T}.png"
        subprocess.run([paths.FFMPEG,"-y","-loglevel","error","-ss",f"{bt/1e6:.3f}","-i",res(bm["path"]),"-frames:v","1",out],check=True)
        bf = Image.open(out).convert("RGB"); cr = bm.get("crop", {}); bf = bf.crop((int(cr.get("upper_left_x",0)*bf.width), int(cr.get("upper_left_y",0)*bf.height), int(cr.get("lower_right_x",1)*bf.width), int(cr.get("lower_right_y",1)*bf.height)))
        bx = kf_val(b, "KFTypePositionX", bt, b["clip"]["transform"]["x"]); by = kf_val(b, "KFTypePositionY", bt, b["clip"]["transform"]["y"])
        BW = int(1080*bsc); BH = int(BW*bf.height/bf.width); canvas.paste(bf.resize((max(1,BW),max(1,BH))), (int(540+bx*540-BW/2), int(960-by*960-BH/2)))
        if bsc > 0.9: return canvas, f"broll x{bsc:.2f}"
        continue
    return canvas, f"x{sc/3.1605:.3f}"
def draw_caption(canvas, T):
    for tr in d["tracks"]:
        if tr["type"] != "text": continue
        s = seg_at(tr, T)
        if not s: continue
        loc = T*1e6 - s["target_timerange"]["start"]
        sc = kf_val(s, "KFTypeScaleX", loc, s["clip"]["scale"]["x"]); y = kf_val(s, "KFTypePositionY", loc, s["clip"]["transform"]["y"]); xx = kf_val(s, "KFTypePositionX", loc, s["clip"]["transform"]["x"])
        c = json.loads(tm[s["material_id"]]["content"]); dr = ImageDraw.Draw(canvas); cy = 960 - y*960
        alpha = int(255 * tm[s["material_id"]].get("global_alpha", 1.0))
        parts = [(c["text"][st["range"][0]:st["range"][1]], ImageFont.truetype(st["font"]["path"], max(4, int(6.0*st["size"]*sc))), tuple(int(v*255) for v in st["fill"]["content"]["solid"]["color"]) + (alpha,)) for st in c["styles"]]
        total = sum(f.getlength(t) for t, f, _ in parts); x = 540 + xx*540 - total/2
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        for t, f, col in parts[::-1]:
            ld.text((x, cy - f.size/2), t, font=f, fill=col, stroke_width=(max(1, int(6*sc)) if tm[s["material_id"]].get("border_width", 0) > 0 else 0), stroke_fill=(0, 0, 0, alpha)); x += f.getlength(t)
        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB"))
def draw_logo(canvas, T):
    for tr in d["tracks"][1:]:
        if tr["type"] != "video": continue
        s = seg_at(tr, T)
        if not s or vm[s["material_id"]].get("type") != "photo": continue
        loc = T*1e6 - s["target_timerange"]["start"]
        sc = kf_val(s, "KFTypeScaleX", loc, s["clip"]["scale"]["x"]); y = kf_val(s, "KFTypePositionY", loc, s["clip"]["transform"]["y"]); x = kf_val(s, "KFTypePositionX", loc, s["clip"]["transform"]["x"])
        im = Image.open(res(vm[s["material_id"]]["path"])).convert("RGBA"); lw = max(1, int(1080*sc)); lh = max(1, int(lw*im.height/im.width))
        im = im.resize((lw, lh)); cx = 540 + x*540; cy = 960 - y*960; canvas.paste(im, (int(cx-lw/2), int(cy-lh/2)), im)
tiles = []
for T in times:
    im, tag = frame(T); draw_caption(im, T); draw_logo(im, T)
    ImageDraw.Draw(im).text((20, 20), f"{T}s {tag}", font=ImageFont.truetype(LAT, 40), fill="yellow"); tiles.append(im.resize((450, 800)))
sheet = Image.new("RGB", (450*len(tiles), 800), "black")
for i, t in enumerate(tiles): sheet.paste(t, (450*i, 0))
sheet.save(OUT); print("stills saved", OUT)
