# -*- coding: utf-8 -*-
"""Where is the face — vertically AND horizontally — on the finished 9:16 canvas?

The caption has one y for the whole project, so the only honest way to place it
is to find where faces actually END on the finished canvas, which depends on the
shot's scale and pan and not on the source framing. Detect the face in the
source frame, then map its box through the same geometry CapCut renders with.

It reports the horizontal too, and that half is not optional: `transform.x = 0`
centres the *source*, and nobody sits in the middle of a two-shot. A whole build
once shipped with the guest at 76–82% of canvas width — pressed into the right
edge — because every check measured only the chin.

    .venv/bin/python face_scan.py "<project>" --every 1

Output rows carry `layer` ("bottom"/"top"), `cam` (1/2 where the work-copy names
allow it), `chin`, `browline`, `face_x` and `scale` — all as fractions of the
finished canvas. `qa25.py --faces` reads them.
"""
import sys, os, re, json, subprocess, collections
import numpy as np, cv2
sys.path.insert(0, 'app'); import capcut
import argparse
ap = argparse.ArgumentParser(description="where do faces land on the finished 9:16 canvas?")
ap.add_argument("project")
ap.add_argument("--every", type=float, default=1.0, help="sample interval, seconds")
ap.add_argument("--caption-height", type=float, default=0.046,
                help="rendered caption band as a fraction of frame height")
ap.add_argument("--margin", type=float, default=0.011, help="clearance below the lowest chin")
ap.add_argument("--face-x", default="0.33,0.38",
                help="the house horizontal window for the face centre, as fractions of canvas width")
ap.add_argument("--out", default="faces.json")
args = ap.parse_args()
NAME = args.project; D = capcut.DRAFTS_DIR / NAME
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
YUNET = os.path.expanduser("~/bunker-video-engine/models/face_detection_yunet_2023mar.onnx")
CW, CH = 1080, 1920
XLO, XHI = (float(v) for v in args.face_x.split(","))
d = capcut.load_draft(NAME); vm = {m["id"]: m for m in d["materials"]["videos"]}

# איזה טראק הוא איזה — נקרא מהתוכן, לא מהמיקום. tracks[0]/tracks[1] נכון
# בפרויקט אחד והפוך בשני, ואז כל דוח יוצא הפוך בלי להתלונן.
vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
photo = lambda tk: all(vm[s["material_id"]].get("type") == "photo" for s in tk["segments"])
hidden = lambda tk: all(s["clip"].get("alpha", 1) < 0.5 for s in tk["segments"])
foot = [tk for tk in vt if not photo(tk)]
base = foot[0]
over = next((tk for tk in foot[1:] if not hidden(tk)), None)
def camera_of(tk):
    n = collections.Counter()
    for s in tk["segments"]:
        p = os.path.basename(vm[s["material_id"]]["path"])
        m = re.search(r"cam\s*(\d)", p) or re.search(r"(?<![\d])(\d)(?![\d])[\s_.-]", p)
        if m: n[int(m.group(1))] += 1
    return n.most_common(1)[0][0] if n else 0
CAM = {"bottom": camera_of(base), "top": camera_of(over) if over is not None else 0}
if CAM["bottom"] == CAM["top"]: CAM = {"bottom": 0, "top": 0}
bots = sorted(base["segments"], key=lambda s: s["target_timerange"]["start"])
top = sorted(over["segments"], key=lambda s: s["target_timerange"]["start"]) if over is not None else []
def res(p):
    """נתיב המדיה: קודם עותק העבודה בתוך תיקיית הדראפט, ואם אין — הקובץ המקורי.
    פרויקט שעובד ישירות מול קבצי הפרק (בלי עותקי עבודה) החזיר כאן 0 פנים,
    כי הבסיס הישן תמיד חיפש בתוך התיקייה."""
    raw = re.sub(r'##_draftpath_placeholder_[^#]+_##', '', p)
    local = os.path.join(D, os.path.basename(raw))
    return local if os.path.exists(local) else raw

def geom(m, sc):
    """גודל המלבן המרונדר ומלבן ה-crop, בשברי המקור.

    CapCut חותך ברמת החומר ואז «מכיל» את המלבן החתוך בקנבס. בלי זה כל מיפוי
    פנים→קנבס שגוי בדיוק בפרויקטים שבהם הזוויות נחתכות מראש — למשל מצלמה 2
    כאן, שה-crop שלה ריבועי (0.3486,0.1038)-(0.8283,0.9566)."""
    c = m.get("crop") or {}
    x0, y0 = c.get("upper_left_x", 0.0), c.get("upper_left_y", 0.0)
    x1, y1 = c.get("lower_right_x", 1.0), c.get("lower_right_y", 1.0)
    if x1 <= x0 or y1 <= y0: x0, y0, x1, y1 = 0.0, 0.0, 1.0, 1.0
    w = (m.get("width") or 1920) * (x1 - x0); h = (m.get("height") or 1080) * (y1 - y0)
    ar = w / h
    if ar >= CW / CH: rw = CW * sc; rh = rw / ar          # contain by width
    else:             rh = CH * sc; rw = rh * ar          # contain by height
    return rw, rh, (x0, y0, x1, y1)

def val(seg, prop, t_local, default):
    ck = next((c for c in seg.get("common_keyframes", []) if c["property_type"] == prop), None)
    if not ck or not ck["keyframe_list"]: return default
    s0 = seg["source_timerange"]["start"]
    pts = sorted(((k["time_offset"] - s0) / 1e6, k["values"][0]) for k in ck["keyframe_list"])
    if t_local <= pts[0][0]: return pts[0][1]
    if t_local >= pts[-1][0]: return pts[-1][1]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if a <= t_local <= b:
            return va if b == a else va + (vb - va) * (t_local - a) / (b - a)
    return default

det = cv2.FaceDetectorYN.create(YUNET, "", (640, 360), 0.7)
rows = []
T = 0.30
while T < d["duration"] / 1e6:
    bot = next((s for s in bots if s["target_timerange"]["start"] <= T*1e6 <
                s["target_timerange"]["start"] + s["target_timerange"]["duration"]), None)
    if bot is None: T += args.every; continue
    if vm[bot["material_id"]]["path"].endswith(".image"): T += args.every; continue
    tp = next((s for s in top if s["target_timerange"]["start"] <= T*1e6 <
               s["target_timerange"]["start"] + s["target_timerange"]["duration"]
               and s["clip"].get("alpha", 1) > 0.5), None)
    layers = [("bottom", bot)] + ([("top", tp)] if tp is not None else [])
    for tag, seg in layers:
        tl = T - seg["target_timerange"]["start"] / 1e6
        sc = val(seg, "KFTypeScaleX", tl, seg["clip"]["scale"]["x"])
        tx = val(seg, "KFTypePositionX", tl, seg["clip"]["transform"]["x"])
        ty = val(seg, "KFTypePositionY", tl, seg["clip"]["transform"]["y"])
        src = seg["source_timerange"]["start"] / 1e6 + tl
        raw = subprocess.run([FF, "-v", "error", "-ss", f"{src:.3f}", "-i", res(vm[seg["material_id"]]["path"]),
            "-frames:v", "1", "-vf", "scale=640:360", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
            capture_output=True).stdout
        if len(raw) != 640*360*3: continue
        img = np.frombuffer(raw, np.uint8).reshape(360, 640, 3)
        det.setInputSize((640, 360))
        _, faces = det.detect(img)
        if faces is None: continue
        rw, rh, (cx0, cy0, cx1, cy1) = geom(vm[seg["material_id"]], sc)
        cx, cy = CW/2 + tx*(CW/2), CH/2 - ty*(CH/2)
        for f in faces:
            x, y, w, h = f[:4]
            # הפנים נמדדות בפריים המלא; המיפוי לקנבס עובר דרך מלבן ה-crop
            fy0 = ((y)/360 - cy0)/(cy1-cy0); fy1 = ((y+h)/360 - cy0)/(cy1-cy0)
            fx = ((x + w/2)/640 - cx0)/(cx1-cx0)
            fw = (w/640)/(cx1-cx0)
            top_c = cy + (fy0-0.5)*rh; bot_c = cy + (fy1-0.5)*rh
            # אותה מתמטיקה בדיוק, על הציר השני: מרכז הפנים כשבר מרוחב הקנבס
            x_c = cx + (fx-0.5)*rw
            if not (-0.2*CH < bot_c < 1.2*CH): continue
            if not (-0.3 < fx < 1.3): continue          # פנים מחוץ למלבן החתוך
            rows.append({"t": round(T, 2), "layer": tag, "cam": CAM[tag],
                         "chin": round(float(bot_c)/CH, 4),
                         "browline": round(float(top_c)/CH, 4),
                         "face_x": round(float(x_c)/CW, 4),
                         "head_w": round(float(fw*rw)/CW, 4),
                         "scale": round(float(sc), 3)})
    T += args.every
json.dump(rows, open(args.out, "w"))
if not rows: sys.exit("לא נמצאו פנים בכלל — בדוק את בחירת הטראקים ואת נתיבי עותקי העבודה")
ch = np.array([r["chin"] for r in rows])
print(f"שכבות: תחתונה = מצלמה {CAM['bottom'] or '?'} | עליונה = מצלמה {CAM['top'] or '?'}")
print(f"פריימים עם פנים: {len(rows)}")
print(f"סנטר (חלק מגובה הפריים) — חציון {np.median(ch):.3f} | 90% {np.percentile(ch,90):.3f} | מקסימום {ch.max():.3f}")
for q in (50, 75, 90, 95, 99):
    print(f"   אחוזון {q}: {np.percentile(ch,q):.3f}")
low = sorted(rows, key=lambda r: -r["chin"])[:8]
print("הסנטרים הנמוכים ביותר:", [(r["t"], r["layer"], r["chin"]) for r in low])

# ── האופק: איפה הפנים לרוחב הקנבס ─────────────────────────────────────────────
# זה החצי שנשכח פעם אחת ועלה סבב שלם — transform.x = 0 אינו "ממורכז".
print(f"\nמרכז הפנים לרוחב (חלק מרוחב הקנבס) — היעד {XLO:.2f}–{XHI:.2f}")
for tag in ("bottom", "top"):
    xs = np.array([r["face_x"] for r in rows if r["layer"] == tag])
    if not len(xs): continue
    out = int(((xs < XLO - 0.02) | (xs > XHI + 0.02)).sum())
    print(f"   {tag:6s} (מצלמה {CAM[tag] or '?'}): חציון {np.median(xs):.3f} | "
          f"טווח {xs.min():.3f}–{xs.max():.3f} | מחוץ ליעד {out}/{len(xs)}")
    if out > len(xs) * 0.1:
        need = float(np.median(xs)) - (XLO + XHI) / 2
        print(f"      ⚠ הזז את הפריים: transform.x צריך לקטון בערך ב-{2*need:+.3f} "
              f"(x ביחידות חצי-קנבס), אחרת הפנים נצמדות לקצה")
hw = np.array([r["head_w"] for r in rows])
print(f"רוחב ראש: חציון {np.median(hw):.3f} מרוחב הקנבס")

# split screens have a second face low in the frame; the caption has to clear the
# full-frame chins and still stop short of that lower face's forehead
def is_split(seg):
    ck = next((c for c in seg.get("common_keyframes", []) if c["property_type"] == "KFTypePositionY"), None)
    ys = [k["values"][0] for k in ck["keyframe_list"]] if ck and ck["keyframe_list"] else [seg["clip"]["transform"]["y"]]
    sc = seg["clip"]["scale"]["x"]
    ck2 = next((c for c in seg.get("common_keyframes", []) if c["property_type"] == "KFTypeScaleX"), None)
    if ck2 and ck2["keyframe_list"]: sc = min(k["values"][0] for k in ck2["keyframe_list"])
    return max(abs(v) for v in ys) > 0.15 and sc < 2.4
sp = [(s["target_timerange"]["start"]/1e6,
       (s["target_timerange"]["start"]+s["target_timerange"]["duration"])/1e6)
      for s in top if s["clip"].get("alpha", 1) > 0.5 and is_split(s)]
inside = lambda t: any(a <= t < b for a, b in sp)
full = [r for r in rows if not inside(r["t"])]
lower = [r for r in rows if inside(r["t"]) and r["layer"] == "top"]
chin = max(r["chin"] for r in full) if full else 0.55
brow = min(r["browline"] for r in lower) if lower else 1.0
top_edge = chin + args.margin
centre = top_edge + args.caption_height/2
print(f"\nמסך מלא: הסנטר הנמוך ביותר {chin:.3f}")
if lower: print(f"מסך מפוצל: המצח של הפנים התחתונות {brow:.3f}")
print(f"-> קצה עליון של הכתובית {top_edge:.3f} | מרכז {centre:.3f} | "
      f"transform.y = {1-2*centre:.4f}")
if centre + args.caption_height/2 > brow:
    print(f"   ⚠ הקצה התחתון {centre+args.caption_height/2:.3f} חודר לפנים התחתונות "
          f"במסך המפוצל — הקטן את --margin או קצר את הכתוביות")
if centre + args.caption_height/2 > 0.86:
    print("   ⚠ נמוך מדי — האזור הבטוח של הפלטפורמה מתחיל בערך ב-0.86")
