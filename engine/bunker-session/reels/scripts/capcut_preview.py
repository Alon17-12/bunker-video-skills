"""what CapCut shows at timeline t (video layers only): split clip, or the camera crop with keyframes evaluated"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
P = os.path.join(os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft"), os.environ["PROJ"])
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
d = json.load(open(P + "/draft_info.json"))
M = {}
for k, v in d["materials"].items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: M[m["id"]] = (k, m)
st = lambda s: s["target_timerange"]["start"]; en = lambda s: st(s) + s["target_timerange"]["duration"]
mat = lambda s: M[s["material_id"]][1]
T = d["tracks"]; vt = [t for t in T if t["type"] == "video"]
def val(s, t):
    kf = {k["property_type"]: k["keyframe_list"] for k in s.get("common_keyframes", [])}
    if not kf: return s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
    src = s["source_timerange"]["start"] + (t - st(s))
    def ev(lst):
        if src <= lst[0]["time_offset"]: return lst[0]["values"][0]
        for a, b in zip(lst, lst[1:]):
            if a["time_offset"] <= src <= b["time_offset"]:
                x = (src - a["time_offset"]) / max(1, b["time_offset"] - a["time_offset"])
                e = x * x * (3 - 2 * x) if a["right_control"]["x"] else 0.0   # ease ≈ smoothstep; hold when no handle
                return a["values"][0] + (b["values"][0] - a["values"][0]) * e
        return lst[-1]["values"][0]
    return ev(kf["KFTypeScaleX"]), ev(kf["KFTypePositionX"]), ev(kf["KFTypePositionY"])
def frame(t):
    t = int(t * 1e6) + 1
    for tr in reversed(vt):           # top track first
        if tr.get("name") in ("לוגו", "גרפיקה") or (tr.get("name") or "").startswith("סגיר"): continue
        for s in tr["segments"]:
            if st(s) <= t < en(s) and s["clip"]["alpha"] > 0.5:
                m = mat(s); path = __import__("re").sub(r"##_draftpath_placeholder_[0-9A-F-]+_##", P, m["path"]); src = (s["source_timerange"]["start"] + (t - st(s))) / 1e6
                if not path.endswith(".mp4"): return Image.new("RGB", (1080, 1920), "white"), "card"
                raw = subprocess.run([FF, "-v", "error", "-ss", f"{src:.4f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
                im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
                if "split" in path or "מסך משולב" in path: return im.resize((1080, 1920)), "split"
                sc, tx, ty = val(s, t)
                W, H = 1080 * sc, 607.5 * sc; cx, cy = 540 + tx * 540, 960 - ty * 960
                im = im.resize((round(W), round(H))); can = Image.new("RGB", (1080, 1920))
                can.paste(im, (round(cx - W / 2), round(cy - H / 2)))
                return can, f"{m['material_name'][3:7]} {sc:.2f}"
    return Image.new("RGB", (1080, 1920)), "-"
if __name__ == "__main__":
    ts = [float(x) for x in sys.argv[2].split(",")]; ims = []
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 60)
    for t in ts:
        im, lab = frame(t); dr = ImageDraw.Draw(im); dr.text((20, 20), f"{t:.2f} {lab}", fill="yellow", font=f, stroke_width=3, stroke_fill="black")
        ims.append(im.resize((270, 480)))
    cols = min(8, len(ims)); rows = (len(ims) + cols - 1) // cols
    sh = Image.new("RGB", (270 * cols, 480 * rows))
    for i, im in enumerate(ims): sh.paste(im, ((i % cols) * 270, (i // cols) * 480))
    sh.save(sys.argv[1], quality=85)
