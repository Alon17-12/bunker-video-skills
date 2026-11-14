# -*- coding: utf-8 -*-
"""The sign-off gate for a finished 9:16 podcast reel — thirty checks.

Read-only. Every check prints the number it measured, not a verdict you have to
trust — a check that says "0 problems" without saying what it counted is worth
nothing. Run it after CapCut has saved the project at least once, because CapCut
rewrites the draft on its own terms and the file you wrote is not the file that
renders.

    .venv/bin/python qa25.py "<project>" [--faces faces.json] [--audio-cuts]

`--faces` takes the output of face_scan.py; without it checks 22 and 29 are
skipped rather than guessed. `--audio-cuts` decodes audio at every cut (slow)
for check 16.

Two of these exist because a gate can pass while the reel is visibly wrong, and
did: **28** (both cameras run end to end and the routing is opacity — the
delivery format) and **29** (the face's horizontal position, the axis that once
went unmeasured through four rounds of corrections). A gate that only re-states
the builder's own assumptions is worth nothing; these two compare the project
against what Alon approved.
"""
import json, os, re, sys, argparse, collections, subprocess
sys.path.insert(0, 'app'); import capcut
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--faces", help="face_scan.py output")
ap.add_argument("--audio-cuts", action="store_true")
ap.add_argument("--caption-band", type=float, default=0.046)
ap.add_argument("--zoom-cap", type=float, default=3.55,
                help="התקרה נמדדת לכל פרק — 3.55 היא של אורח G, לא חוק")
ap.add_argument("--pin", choices=("eyes", "top"), default="eyes",
                help="eyes = עיגון לפי העיניים (ברירת המחדל מאז אורח O); top = הנעיצה הישנה לקצה")
ap.add_argument("--zoom-rate", type=float, default=1.5,
                help="קצב הזום המתמשך המרבי, באחוזים לשנייה — מה שהעין שופטת, לא האמפליטודה")
ap.add_argument("--zoom-entry", type=float, default=0.6,
                help="חלון הכניסה אחרי חיתוך שבו אגרוף מהיר הוא סגנון ולא תקלה")
ap.add_argument("--routing-cover", type=float, default=0.8,
                help="הכיסוי המזערי של השכבה השנייה כדי שהניתוב ייחשב שקיפות")
ap.add_argument("--static", type=float, default=2.5,
                help="שוט קצר מזה אמור לעמוד לגמרי במקום")
ap.add_argument("--intro-s", type=float, default=1.0, help="חלון הזום-אאוט של הפתיח (בדיקה 18 לא מודדת בו היפוך)")
ap.add_argument("--face-x", default="0.33,0.38",
                help="חלון היעד למרכז הפנים לרוחב הקנבס (דורש --faces מגרסה שמדווחת face_x)")
A = ap.parse_args()

NAME = A.project; D = capcut.DRAFTS_DIR / NAME; P = D / "draft_info.json"
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
FILL = 3.1604938271604937; PIN = 607.5 / 1920.0
# הרשת נקראת מהפרויקט. דגימה ב-60fps על פרויקט 30fps נוחתת באמצע ראמפ
# וממציאה מאות "פריימים שחורים" שלא קיימים — בדיוק הטעות שהסקיל מזהיר
# ממנה, בתוך הכלי שאמור לתפוס אותה.
FR = 1e6 / float(json.load(open(capcut.DRAFTS_DIR / A.project / "draft_info.json")).get("fps") or 60.0)
F = int(round(FR))
ZOOM_CAP = A.zoom_cap     # tightest crop that still clears the caption band
YELLOW = (0.96, 0.78, 0.06); WHITE = (1.0, 1.0, 1.0)
TITLE_MIN = 3_500_000          # a text segment this long is a headline card

d = json.load(open(P))
vids = {m["id"]: m for m in d["materials"]["videos"]}
texts = {m["id"]: m for m in d["materials"]["texts"]}
vt = [t for t in d["tracks"] if t["type"] == "video"]
# תפקיד הטראק לפי מה שיש בו, לא לפי מיקומו. מאז שהקול של מצלמה 2 יושב
# בשכבה שקופה משלו, vt[1] הוא שכבת הקול ולא השכבה הנראית — וכל בדיקה
# שנשענה על vt[1] נכשלה על פרויקט תקין לגמרי.
def _mostly_photo(tk):
    return tk["segments"] and all(vids[s["material_id"]].get("type") == "photo" for s in tk["segments"])
def _silent_layer(tk):
    return tk["segments"] and all(s["clip"].get("alpha", 1) < 0.5 for s in tk["segments"])
base = vt[0]
def _broll_layer(tk):
    """a b-roll overlay is not a camera: short generated clips (named 'broll', or every piece under 8s with low coverage)"""
    if (tk.get("name") or "").lower().replace("-", "") in ("broll", "brolls"): return True
    segs = tk["segments"]
    return bool(segs) and all(s["target_timerange"]["duration"] < 8e6 for s in segs) and sum(s["target_timerange"]["duration"] for s in segs) < 0.3 * d["duration"]
_cand = [t for t in vt[1:] if not _mostly_photo(t) and not _silent_layer(t) and not _broll_layer(t)]
# אין מצלמה שנייה אמיתית (רק לוגו/סטילס מעל מצלמה אחת) → השכבה העליונה היא
# הבסיס עצמו; אחרת רצועת לוגו נקראת כ"חצי מסך מפוצל" ובדיקות 10/11 נכשלות (0910)
ovl = _cand[0] if _cand else base
# איזו מצלמה יושבת בכל שכבה — נקרא משמות עותקי העבודה. ההנחה שהשכבה
# העליונה היא תמיד מצלמה 1 נכונה באורח G והפוכה באורח O, וכל בדיקה
# שנשענה עליה דיווחה בדיוק ההפך מהמציאות.
def _camera_of(tk):
    # שמות עותקי העבודה משתנים בין פרקים: `-cam1.mp4` אצל אורח N2, `… 1 - …`
    # אצל אורח G, `… -2.mp4` אצל לקוח I. אם אי אפשר לקרוא — מחזירים 0 ואומרים
    # זאת, במקום לנחש ולדווח 0% התאמה על פרויקט תקין.
    n = collections.Counter()
    for s in tk["segments"]:
        p = os.path.basename(vids[s["material_id"]]["path"])
        m = re.search(r"cam\s*(\d)", p) or re.search(r"(?<![\d])(\d)(?![\d])[\s_.-]", p)
        if m: n[int(m.group(1))] += 1
    return n.most_common(1)[0][0] if n else 0
CAM = {id(base): _camera_of(base), id(ovl): _camera_of(ovl)}
if CAM[id(base)] == CAM[id(ovl)]:      # אותו מספר לשתי השכבות = לא זוהה
    CAM = {id(base): 0, id(ovl): 0}
ST = lambda tk: f"cam{CAM.get(id(tk), 0)}"
snd = next((t for t in vt if _silent_layer(t) and not _mostly_photo(t)), None)
res = lambda p: os.path.join(D, os.path.basename(re.sub(r'##_draftpath_placeholder_[^#]+_##', '', p)))
card = lambda s: vids[s["material_id"]]["path"].endswith(".image") or "ccstudio-card" in vids[s["material_id"]]["path"]
km = lambda s: {c["property_type"]: c for c in s.get("common_keyframes", [])}
abst = lambda s, o: s["target_timerange"]["start"] + (o - s["source_timerange"]["start"])

def val(s, p, t, dflt):
    c = km(s).get(p)
    if not c: return dflt
    l = sorted((k["time_offset"], k["values"][0]) for k in c["keyframe_list"])
    if not l: return dflt          # CapCut משאיר לפעמים רשימת קיפריימים ריקה
    o = (s["source_timerange"]["start"] if s.get("source_timerange") else 0) \
        + (t - s["target_timerange"]["start"])
    if o <= l[0][0]: return l[0][1]
    if o >= l[-1][0]: return l[-1][1]
    for (a, va), (b, vb) in zip(l, l[1:]):
        if a <= o <= b: return va + (vb - va) * (o - a) / (b - a) if b > a else va
    return dflt

def rendered(m, s):
    """גודל המלבן על הקנבס, מודע ל-crop של החומר.

    607.5·s נכון רק לחומר 16:9 בלי חיתוך. ב-0810 למצלמה 2 יש crop ריבועי, ולכן
    היא ממלאת את הקנבס כבר ב-1.78 בעוד מצלמה 1 צריכה 3.16 — וכל בדיקה שהניחה
    16:9 דיווחה עליה «סקייל קטן מדי» ו«קנבס לא מכוסה» על פריימים תקינים."""
    c = m.get("crop") or {}
    x0, y0 = c.get("upper_left_x", 0.0), c.get("upper_left_y", 0.0)
    x1, y1 = c.get("lower_right_x", 1.0), c.get("lower_right_y", 1.0)
    if x1 <= x0 or y1 <= y0: x0, y0, x1, y1 = 0.0, 0.0, 1.0, 1.0
    w = (m.get("width") or 1920) * (x1 - x0); h = (m.get("height") or 1080) * (y1 - y0)
    ar = w / h
    if ar >= 1080 / 1920: rw = 1080 * s; rh = rw / ar
    else:                 rh = 1920 * s; rw = rh * ar
    return rw, rh
rend = lambda s, sc: rendered(vids[s["material_id"]], sc)
fill_of = lambda s: 1920.0 / (rend(s, 1.0)[1] or 1.0)      # הסקייל שבו החומר מכסה

def seg_at(tk, t, vis=False):
    for s in tk["segments"]:
        r = s["target_timerange"]
        if r["start"] <= t < r["start"] + r["duration"]:
            return None if (vis and s["clip"].get("alpha", 1) < 0.5) else s
    return None

R = []
def chk(n, title, ok, detail): R.append((n, title, ok, detail))

END = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
          for tk in d["tracks"] if tk["type"] in ("video", "text") for s in tk["segments"])
cards = [(s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"])
         for s in base["segments"] if card(s)]
in_card = lambda t: any(a <= t < b for a, b in cards)
splits = []
for s in ovl["segments"]:
    if s["clip"].get("alpha", 1) < 0.5: continue
    # חצי מסך מזוהה גם כשהוא סטטי: ב-אורח O ה-y של החצי נכתב ב-clip.transform
    # ולא כקיפריים, ובדיקה שהסתכלה רק על הקיפריימים ראתה אפס פיצולים —
    # ואז כל שאר הבדיקות התייחסו לחצאים כאילו הם מסך מלא שיצא משליטה.
    c = km(s).get("KFTypePositionY")
    # רשימת קיפריימים ריקה קיימת בפרויקטים אמיתיים — נופלים חזרה לערך הסטטי
    ys = [k["values"][0] for k in c["keyframe_list"]] if c and c["keyframe_list"] else [s["clip"]["transform"]["y"]]
    cs = km(s).get("KFTypeScaleX")
    scs = ([k["values"][0] for k in cs["keyframe_list"]] if cs and cs["keyframe_list"]
           else [s["clip"]["scale"]["x"]])
    if max(abs(v) for v in ys) > 0.15 and rend(s, min(scs))[1] < 1919.5:
        r = s["target_timerange"]; splits.append((r["start"], r["start"] + r["duration"], s))
in_split = lambda t: any(a <= t < b for a, b, _ in splits)

# ── structure ────────────────────────────────────────────────────────────────
chk(1, "אורך הפרויקט תואם את סוף הטראקים", abs(d["duration"] - END) <= F,
    f"duration {d['duration']/1e6:.2f} | טראקים {END/1e6:.2f}")

gaps = over = 0
for tk in d["tracks"]:
    segs = sorted(tk["segments"], key=lambda s: s["target_timerange"]["start"])
    for a, b in zip(segs, segs[1:]):
        ea = a["target_timerange"]["start"] + a["target_timerange"]["duration"]
        if b["target_timerange"]["start"] < ea - 1: over += 1
        if tk is base and b["target_timerange"]["start"] > ea + 1: gaps += 1
chk(2, "אין חורים או חפיפות בטראקים", gaps == 0 and over == 0, f"חורים {gaps} | חפיפות {over}")

out = sum(1 for tk in vt for s in tk["segments"] for c in s.get("common_keyframes", [])
          for k in c["keyframe_list"]
          if not (s["source_timerange"]["start"] - 1 <= k["time_offset"]
                  <= s["source_timerange"]["start"] + s["source_timerange"]["duration"] + 1))
chk(3, "כל קיפריים בתוך תחום המקור של המקטע", out == 0, f"חורגים {out}")

ids = collections.Counter(); tot = 0
for tk in d["tracks"]:
    for s in tk["segments"]:
        for c in s.get("common_keyframes", []):
            ids[c.get("id")] += 1
            for k in c["keyframe_list"]: ids[k.get("id")] += 1; tot += 1
dup = sum(v - 1 for v in ids.values() if v > 1)
chk(4, "מזהה ייחודי לכל קיפריים", dup == 0, f"{tot} קיפריימים | כפולים {dup}")

# מזהה משותף מסוכן רק כשהאובייקטים שונים — CapCut משכפל חומר משותף למופע אחד
# לכל מקטע ומשאיר את אותו מזהה, וזה בלתי מזיק. מיזוג של אובייקטים *שונים* הוא
# מה שהפך פעם 21 שניות לשחור.
byid = collections.defaultdict(set)
def _walk(o):
    if isinstance(o, dict):
        # אנימציית CapCut (Fade In/Out) נושאת את מזהה המשאב כ-id ומשנה רק start — כך
        # CapCut עצמו כותב אותה, זה לא מיזוג של אובייקטים שונים (0910, ערימות קינטיות)
        if "resource_id" in o and "panel" in o: return
        if isinstance(o.get("id"), str):
            byid[o["id"]].add(json.dumps(o, sort_keys=True, ensure_ascii=False))
        for v in o.values(): _walk(v)
    elif isinstance(o, list):
        for v in o: _walk(v)
_walk(d["materials"]); _walk(d["tracks"])
clash = [k for k, v in byid.items() if len(v) > 1]
shared = sum(1 for v in byid.values() if v)
chk("4b", "אין מזהה משותף לאובייקטים שונים", not clash,
    f"{len(byid)} מזהים | מזהים שחוזרים על עצמו עם תוכן שונה: {len(clash)}")

same = sum(len([k["time_offset"] for k in c["keyframe_list"]]) - len({k["time_offset"] for k in c["keyframe_list"]})
           for tk in vt for s in tk["segments"] for c in s.get("common_keyframes", []))
chk(5, "אין שני קיפריימים על אותה חותמת זמן", same == 0, f"התנגשויות {same}")

# ── the canvas is filled ─────────────────────────────────────────────────────
black = 0; n = 0; t = 0
while t < d["duration"]:
    if not in_card(t):
        spans = []
        for tk in vt:
            s = seg_at(tk, t)
            if s is None or s["clip"].get("alpha", 1) < 0.01: continue
            sc = val(s, "KFTypeScaleX", t, s["clip"]["scale"]["x"])
            y = val(s, "KFTypePositionY", t, s["clip"]["transform"]["y"])
            cy = 960 - y * 960; h = rend(s, sc)[1]
            spans.append((cy - h / 2, cy + h / 2))
        spans.sort(); cov = 0.0; hole = False
        for a, b in spans:
            if a > cov + 0.5: hole = True; break
            cov = max(cov, b)
        if hole or cov < 1919.5: black += 1
    n += 1; t = int(round(n * FR))
chk(6, "אין פריים שבו הקנבס לא מכוסה", black == 0, f"{n} פריימים | שחור ב-{black}")

# ── geometry ─────────────────────────────────────────────────────────────────
full_bad = []; small = []; pin_bad = []; xdrift = []; tracked = 0
# יעד הבית למרכז הפנים לרוחב — אמצע חלון --face-x. בדיקה 9 גוזרת ממנו את
# ההיסט הקבוע של הפאן (2t-1), כי הנוסחה אפינית ב-s ולא פרופורציונלית.
X_TARGET = sum(float(v) for v in A.face_x.split(",")) / 2
# מי למעלה בפיצול נקבע לפי גובה הראש במקור, ומשתנה בין פרקים — ב-אורח G
# עזרא הטראק הראשי הוא העליון וב-אורח O הוא התחתון. קוראים את הסימן מהחומר
# במקום להניח אותו, אחרת כל 28 החצאים נראים "לא נעוצים לתפר".
def _seam_sign(tk):
    vs = []
    for s in tk["segments"]:
        c = km(s).get("KFTypePositionY")
        vs += [k["values"][0] for k in c["keyframe_list"]] if c else [s["clip"]["transform"]["y"]]
    vs = [v for v in vs if abs(v) > 0.15]
    return (1 if sum(vs) >= 0 else -1) if vs else 1
_signs = {id(tk): _seam_sign(tk) for tk in vt}
for ti, tk in enumerate(vt):
    sign = _signs[id(tk)]
    if _broll_layer(tk): continue   # b-roll overlays (full-frame or inset) are not camera framing — checks 7/8/9 skip them
    for s in tk["segments"]:
        if card(s): continue
        # סטילס מעל הצילום (לוגו, חץ CTA עם pop-in) הוא אוברליי, לא מסך מלא — בדיקה 27 מודדת אותו
        if vids.get(s["material_id"], {}).get("type") == "photo": continue
        c = km(s).get("KFTypeScaleX")
        if not c: continue
        for k in sorted(c["keyframe_list"], key=lambda k: k["time_offset"]):
            t = abst(s, k["time_offset"]); sc = k["values"][0]
            y = val(s, "KFTypePositionY", t, s["clip"]["transform"]["y"])
            if any(a - F <= t <= b + F for a, b, _ in splits) and rend(s, sc)[1] < 1919.5:
                pass          # החצאים נמדדים בבדיקה 11 לפי התפר עצמו, לא לפי נוסחה
            elif not any(a - F <= t <= b + F for a, b, _ in splits):
                if A.pin == "top":
                    if abs(y - max(0.0, PIN * sc - 1.0)) > 0.004:   # 0.004 ≈ 4px, absorbs the sub-pixel slack the pin needs
                        full_bad.append((round(t/1e6, 2), round(y, 4), round(PIN*sc-1, 4)))
                else:
                    # עיגון לפי העיניים לא מחייב ערך y מסוים — מה שאסור הוא
                    # שהחומר יפסיק לכסות את הקנבס, וזה מה שהנעיצה מנעה
                    _rh = rend(s, sc)[1]
                    top = 960 - 960*y - _rh/2
                    if top > 0.5 or top + _rh < 1919.5:
                        full_bad.append((round(t/1e6, 2), round(y, 4), round(top, 1)))
                # הגבולות נמדדים ביחס לכיסוי של אותו חומר, לא בסקייל מוחלט
                _f = fill_of(s); _r = sc / _f
                if _r < 1 - 1e-6 or _r > ZOOM_CAP / FILL + 1e-3:
                    small.append((round(t/1e6, 2), round(sc, 4), f"×{_r:.3f} מהכיסוי"))
chk(7, ("מסך מלא נעוץ לקצה העליון (y = 0.3164·s − 1)" if A.pin == "top"
        else "מסך מלא מכסה את הקנבס בכל קיפריים"), not full_bad,
    f"עיגון {A.pin} | חריגות {len(full_bad)} {full_bad[:3]}")
chk(8, f"מסך מלא בין כיסוי מלא ל-×{ZOOM_CAP/FILL:.3f} ממנו", not small,
    f"חריגות {len(small)} {small[:3]}")
# התפר עצמו: בכל מסך מפוצל, האם שני החצאים נפגשים? נוסחת נעיצה אחת ("y = ±0.3164·s")
# נכונה רק לחומר 16:9 ולקומפוזיציה אחת מהשתיים שאלון משתמש בהן. מה שנכון תמיד:
# אסור פער. חפיפה היא בחירה — הוא בעצמו חופף ~78px.
seams = []
for a, b, osg in splits:
    t = (a + b) // 2
    sp = []
    for tk in vt:
        sg = seg_at(tk, t)
        if sg is None or sg["clip"].get("alpha", 1) < 0.5 or card(sg): continue
        sc_ = val(sg, "KFTypeScaleX", t, sg["clip"]["scale"]["x"])
        y_ = val(sg, "KFTypePositionY", t, sg["clip"]["transform"]["y"])
        h_ = rend(sg, sc_)[1]; cy_ = 960 - y_ * 960
        sp.append((cy_ - h_/2, cy_ + h_/2))
    sp.sort()
    if len(sp) < 2: seams.append((round(a/1e6, 2), "רק שכבה אחת")); continue
    gap = sp[1][0] - sp[0][1]
    if gap > 0.5: seams.append((round(a/1e6, 2), f"פער {gap:.0f}px"))
chk(11, "אין פער בתפר בין חצאי המסך המפוצל", not seams,
    f"{len(splits)} מסכים מפוצלים | פערים {len(seams)} {seams[:3]}")

for tk in vt:
    for s in tk["segments"]:
        if card(s): continue
        K = km(s)
        if "KFTypeScaleX" not in K or "KFTypePositionX" not in K: continue
        S = sorted(K["KFTypeScaleX"]["keyframe_list"], key=lambda k: k["time_offset"])
        X = {k["time_offset"]: k["values"][0] for k in K["KFTypePositionX"]["keyframe_list"]}
        # פאן עוקב-פנים (0910): x משתנה עם הדמות ולא רק עם הסקייל — אין יחס קבוע
        # למדוד. הפנים עצמן נמדדות בבדיקה 29 (face_scan), וזה מה שהעין רואה.
        if len(X) > len(S) or len({round(k["values"][0], 5) for k in S}) == 1: tracked += 1; continue   # a pan on a held scale is tracking too
        for a, b in zip(S, S[1:]):
            if b["time_offset"] - a["time_offset"] <= F: continue
            if a["time_offset"] not in X or b["time_offset"] not in X: continue
            # x = 2t-1 - s·(2fx-1)  (framing.md) — כלומר (x-(2t-1))/s קבוע לאורך
            # הדחיפה. הבדיקה הישנה דרשה x/s קבוע, שנכון רק כשהיעד t=0.5 (מרכוז);
            # מאז שהיעד הוא חלון הבית 0.33–0.38 היא פסלה מסגור נכון.
            _off = 2 * X_TARGET - 1
            r1 = (X[a["time_offset"]] - _off) / a["values"][0]
            r2 = (X[b["time_offset"]] - _off) / b["values"][0]
            if abs(r1 - r2) > 0.004:
                xdrift.append((round(abst(s, a["time_offset"])/1e6, 2), round(r1, 4), round(r2, 4)))
chk(9, "הפאן האופקי גדל יחד עם הסקייל", not xdrift, f"חריגות {len(xdrift)} {xdrift[:3]}" + (f" | {tracked} שוטים עם פאן עוקב-פנים נמדדים ב-29" if tracked else ""))

# 10 ו-12 היו כתובים לפי מבנה אחד: שהטראק התחתון ממשיך להיות מסך מלא מתחת
# לפיצול. ב-0810 התחתון *הוא* החצי התחתון, ואז שתי הבדיקות דיווחו 22 חריגות
# על פרויקט תקין. מה שנכון בכל מבנה: לשני החצאים אותו חלון זמן בדיוק, והמעבר
# הוא גבול מקטע (כלומר חיתוך), לא ראמפ של קיפריימים.
pairs = []; win_bad = []; ramp = []
bounds = set()
for tk in vt:
    for sg in tk["segments"]:
        r = sg["target_timerange"]
        bounds |= {r["start"], r["start"] + r["duration"]}
near = lambda t: any(abs(t - x) <= F for x in bounds)
for a, b, osg in splits:
    mate = None
    for tk in vt:
        for sg in tk["segments"]:
            if sg is osg: continue
            r = sg["target_timerange"]
            if sg["clip"].get("alpha", 1) < 0.5 or card(sg): continue
            if abs(r["start"] - a) <= F and abs(r["start"] + r["duration"] - b) <= F:
                mate = sg
    if mate is None: win_bad.append((round(a/1e6, 2), "אין חצי שני באותו חלון"))
    else: pairs.append((a, b, osg, mate))
    if not (near(a) and near(b)): ramp.append(round(a/1e6, 2))
chk(10, "שני החצאים חולקים בדיוק את אותו חלון זמן", not win_bad,
    f"{len(splits)} מסכים מפוצלים | זוגות {len(pairs)} | חריגות {len(win_bad)} {win_bad[:3]}")
chk(12, "כניסה ויציאה מהפיצול בחיתוך, לא בראמפ", not ramp,
    f"חריגות {len(ramp)} {ramp[:3]}")

# ── shots ────────────────────────────────────────────────────────────────────
# Shot boundaries come from the segments themselves, never from sampling — a
# sampled boundary lands a frame or two late and then excludes the very keyframe
# that defines the shot's push-in, which reads as "this shot never moves".
bounds = {0, END}
for tk in (ovl, base):
    for s in tk["segments"]:
        r = s["target_timerange"]
        bounds |= {r["start"], r["start"] + r["duration"]}
bounds = sorted(b for b in bounds if 0 <= b <= END)
shots = []
for a, b in zip(bounds, bounds[1:]):
    if b - a < 1000: continue
    m = (a + b) // 2
    st = ("card" if in_card(m) else "split" if in_split(m)
          else ST(ovl) if seg_at(ovl, m, vis=True) is not None else ST(base))
    if shots and shots[-1][2] == st and shots[-1][1] == a: shots[-1] = (shots[-1][0], b, st)
    else: shots.append((a, b, st))
short = [(round(a/1e6, 2), round((b-a)/1e6, 2), s) for a, b, s in shots if b - a < 1_000_000 and s not in ("split", "card")]
chk(15, "אין שוט קצר מ-1 שניה", not short, f"{len(shots)} שוטים | קצרים {len(short)} {short[:3]}")
# החזקה = רצף על אותה מצלמה שלא נשבר בפיצול. שוט בודד ארוך אינו בעיה
# כשלעצמו — הכלל הוא ש-9 שניות על אותו פנים בלי מסך מפוצל באמצע זה יותר
# מדי. הבדיקה הקודמת מדדה אורך שוט, ולכן קראה החזקה גם למקום שבו הפיצול
# באמת קורה מעל.
runs = []
for a, b, st in shots:
    if st == "card": continue
    if st == "split": runs.append(None); continue
    if runs and runs[-1] and runs[-1][2] == st and runs[-1][1] == a: runs[-1] = (runs[-1][0], b, st)
    else: runs.append((a, b, st))
runs = [r for r in runs if r]
hold = max(runs, key=lambda x: x[1] - x[0]) if runs else (0, 0, "—")
chk(20, "אין החזקה על אותה מצלמה ארוכה מ-9 שניות בלי פיצול",
    (hold[1] - hold[0] <= 9_000_000) if CAM[id(ovl)] else None,
    f"הארוכה ביותר {(hold[1]-hold[0])/1e6:.2f}s ב-{hold[0]/1e6:.2f} ({hold[2]}) | {len(runs)} החזקות"
    + ("" if CAM[id(ovl)] else " — לא נבדק, לא זוהו המצלמות בשכבות"))

# הכלל האמיתי מאז שהקול חי בתוך קבצי המצלמה: **הכיסוי הנשמע של מצלמה 2
# שווה לזה של מצלמה 1**. הניתוב מניח את מצלמה 2 רק היכן שרואים אותה, ואם
# אין שכבת קול מלאה מתחתיה נעלמות בדיוק שניות התגובה — 102 שניות מהאורח
# נמחקו ככה פעם אחת ואיש לא שמע את זה ב-JSON.
foot = sum(s["target_timerange"]["duration"] for s in base["segments"] if not card(s))
cardt = sum(b - a for a, b in cards)
if snd is not None:
    sc_ = sum(s["target_timerange"]["duration"] for s in snd["segments"])
    same = sorted((s["target_timerange"]["start"], s["target_timerange"]["duration"])
                  for s in base["segments"] if not card(s)) == \
           sorted((s["target_timerange"]["start"], s["target_timerange"]["duration"])
                  for s in snd["segments"])
    chk(17, "כיסוי הקול של מצלמה 2 שווה למצלמה 1", abs(foot - sc_) < F and same,
        f"מצלמה1 {foot/1e6:.2f}s | מצלמה2 {sc_/1e6:.2f}s | חלונות זהים {'כן' if same else 'לא'}")
else:
    chk(17, "שכבת הצילום מכסה מקצה לקצה מחוץ לכרטיסים", abs(foot - (END - cardt)) < 50 * F,
        f"אין שכבת קול נפרדת | כיסוי {foot/1e6:.2f} מתוך {(END-cardt)/1e6:.2f}")

# ── הניתוב הוא שקיפות, ושתי המצלמות רצות מקצה לקצה ──────────────────────────
# זו צורת המסירה שאלון ביקש: שתי הזוויות גלויות לו לאורך כל הדרך, והעריכה
# שלי מתוקנת אצלו בסליידר Opacity. בנייה שמניחה מקטע רק היכן שרואים אותו
# מחזירה אותו אליי בשביל כל שינוי — וגם מוחקת את המיקרופון של אותה מצלמה.
uncov = 0; nfoot = 0; vis = 0; holes = 0; wins = []; run = None
t = 0; n = 0
while t < d["duration"]:
    gap = False
    if not in_card(t):
        b_ = seg_at(base, t)
        if b_ is not None:
            nfoot += 1
            o_ = seg_at(ovl, t)
            if o_ is None: uncov += 1; gap = True
            elif o_["clip"].get("alpha", 1) >= 0.5: vis += 1
            if b_["clip"].get("alpha", 1) < 0.5 and not in_split(t): holes += 1
    if gap and run is None: run = t
    if not gap and run is not None: wins.append((round(run/1e6, 1), round(t/1e6, 1))); run = None
    n += 1; t = int(round(n * FR))
if run is not None: wins.append((round(run/1e6, 1), round(t/1e6, 1)))
soft = []
for tk in (base, ovl):
    for s in tk["segments"]:
        a_ = s["clip"].get("alpha", 1)
        if 0.02 < a_ < 0.98: soft.append((round(s["target_timerange"]["start"]/1e6, 2), round(a_, 2)))
        c = km(s).get("KFTypeAlpha")
        if c and c["keyframe_list"]:
            ks = sorted(k["time_offset"] for k in c["keyframe_list"])
            for x, y in zip(ks, ks[1:]):
                if y - x > F and abs(val(s, "KFTypeAlpha", abst(s, x), 1) -
                                     val(s, "KFTypeAlpha", abst(s, y), 1)) > 0.1:
                    soft.append((round(abst(s, x)/1e6, 2), "ramp"))
cover = (nfoot - uncov) / max(nfoot, 1)
routed = any(s["clip"].get("alpha", 1) < 0.5 for s in ovl["segments"])
detail = (f"כיסוי השכבה העליונה {100*cover:.1f}% | גלויה {100*vis/max(nfoot,1):.0f}% מהזמן | "
          f"חורים בשכבה התחתונה {holes} | שקיפות שאינה 0/1: {len(soft)} {soft[:2]}"
          + (f" | לא מכוסה {wins[:3]}" if wins else ""))
if not routed and snd is not None:
    # בנייה ישנה: המקטעים קיימים רק היכן שרואים אותם, והקול חי בשכבה שקופה
    # נפרדת. זו לא תקלה בפרויקט הזה — זה הפורמט שהוחלף, ואומרים את זה במפורש
    # במקום לצבוע פרויקט מאושר באדום.
    chk(28, "שתי המצלמות מקצה לקצה, והניתוב הוא שקיפות", None,
        "ניתוב במקטעים + שכבת קול נפרדת (בנייה ישנה) — " + detail)
else:
    chk(28, "שתי המצלמות מקצה לקצה, והניתוב הוא שקיפות",
        cover >= A.routing_cover and holes == 0 and not soft, detail)

# ── motion, on the visible stretches only ────────────────────────────────────
# A push-in only counts on the stretch where the layer is actually on screen —
# the reset back to 100% is supposed to happen while the other camera covers, so
# measuring across the hidden part reports a "reversal" that nobody ever sees.
nonmono = []; amp_bad = []; flat = []; rate_bad = []
vis_runs = [(a, b, st) for a, b, st in shots if st in ("cam1", "cam2", "split")]
for ti, tk in enumerate(vt):
    for s in tk["segments"]:
        if card(s): continue
        c = km(s).get("KFTypeScaleX")
        if not c: continue
        r = s["target_timerange"]
        if tk not in (base, ovl): continue
        for a, b, st in vis_runs:
            if b <= r["start"] or a >= r["start"] + r["duration"]: continue
            if st == "split": continue
            if st != ST(tk): continue
            lo, hi = max(a, r["start"]), min(b, r["start"] + r["duration"])
            if hi - lo < 500_000: continue
            # The shot's own keyframes. On the base a cut is a pair one frame
            # apart, so the trailing key belongs to the NEXT shot and has to go;
            # on the overlay the segment simply ends and its last key is its own.
            # Interpolating past either samples the cut ramp and reports a
            # "reversal" that is really the reset to the next shot.
            ks = sorted(k["time_offset"] for k in c["keyframe_list"]
                        if lo - F / 2 <= abst(s, k["time_offset"]) <= hi + F / 2)
            pts = [(abst(s, o), val(s, "KFTypeScaleX", abst(s, o), 0)) for o in ks]
            if len(pts) >= 2 and pts[-1][0] - pts[-2][0] <= F: pts = pts[:-1]
            if not pts or pts[0][0] > lo + F: pts = [(lo, val(s, "KFTypeScaleX", lo, 0))] + pts
            v = [x[1] for x in pts]
            if len(v) < 2 or min(v) <= 0: continue
            # הפתיח: מיני זום-אאוט של ~5% בשנייה הראשונה של הסרטון (אלון, 0910) ואז
            # הדחיפה הרגילה — היפוך מכוון, לא רעד. מוציאים את חלון הפתיח מהמדידה.
            if lo <= F and len(pts) > 2: pts = [p for p in pts if p[0] >= A.intro_s * 1e6 - F/2]; v = [x[1] for x in pts]
            # שני סגנונות חיים בסקיל: ריחוף (דחיפה מתמשכת בכיוון אחד) ואגרופים
            # (0910, אלון: "פחות ריחוף, יותר תנועות שתופסות את העין — זום אין/אאוט חד
            # וחלק פעם ב…"). מהלך בין שני קיפריימים הוא *אגרוף* אם הוא קצר (≤0.7s)
            # וגדול (≥2.5%), *החזקה* אם הוא כמעט אפס, ואחרת *ריחוף*. בשוט עם אגרופים
            # היפוך הוא הסגנון עצמו, ו"קפוא" הוא שוט ארוך בלי אגרוף ובלי ריחוף.
            moves = []
            for (t1, v1), (t2, v2) in zip(pts, pts[1:]):
                dt = (t2 - t1) / 1e6; rel = abs(v2 - v1) / v1 if v1 > 0 else 0
                moves.append(("punch" if dt <= 0.7 and rel >= 0.025 else "hold" if rel < 0.004 else "drift", dt, rel, t1))
            punchy = any(m[0] == "punch" for m in moves)
            up = any(v[i+1] > v[i] + 1e-4 for i in range(len(v)-1))
            dn = any(v[i+1] < v[i] - 1e-4 for i in range(len(v)-1))
            if up and dn and not punchy: nonmono.append(round(lo/1e6, 2))
            amp = (max(v) - min(v)) / min(v)
            if amp > 0.13: amp_bad.append((round(lo/1e6, 2), round(amp*100, 1)))
            if amp < 0.004 and hi - lo > A.static * 1e6:
                flat.append((round(lo/1e6, 2), round((hi-lo)/1e6, 2)))
            # אגרוף חד מדי הוא קפיצה, לא תנועה: פחות מ-0.3s נראה כמו חיתוך
            for kind, dt, rel, t1 in moves:
                if kind == "punch" and dt < 0.3 - 1e-6: rate_bad.append((round(t1/1e6, 2), f"אגרוף {dt:.2f}s"))
            # מה שהעין שופטת הוא הקצב, לא האמפליטודה. אבל הסגנון המאושר
            # *כן* מכיל אגרוף מהיר בחצי השנייה הראשונה אחרי החיתוך (3.16→3.56
            # ב-0.5s ב-אורח O, 3.46→3.85 ב-0.47s ב-פרויקט-דוגמה N) ואז דחיפה איטית.
            # לכן מודדים את הקצב **המתמשך**, אחרי חלון הכניסה.
            for (t1, v1), (t2, v2) in zip(pts, pts[1:]):
                dt = (t2 - t1) / 1e6
                if dt < 0.2 or v1 <= 0: continue
                if t1 < lo + A.zoom_entry * 1e6 or t2 > hi - A.zoom_entry * 1e6: continue
                if dt <= 0.7 and abs(v2 - v1) / v1 >= 0.025: continue   # an eye-catching punch, not a drift
                rate = 100 * abs(v2 - v1) / v1 / dt
                if rate > A.zoom_rate + 1e-6:
                    rate_bad.append((round(t1/1e6, 2), round(rate, 2)))
chk(18, "הזום: כיוון אחד (ריחוף) או אגרופים (0910), ולא קפוא, בכל שוט גלוי", not nonmono and not flat,
    f"היפוכים {len(nonmono)} {nonmono[:3]} | שוטים קפואים מעל {A.static}s: {len(flat)} {flat[:3]}")
chk(19, "אמפליטודת הזום עד 13%", not amp_bad, f"חריגות {len(amp_bad)} {amp_bad[:3]}")
chk("19b", f"קצב הזום עד {A.zoom_rate}%/שנייה", not rate_bad,
    f"חריגות {len(rate_bad)} {sorted(rate_bad, key=lambda r: -(r[1] if isinstance(r[1], (int, float)) else 999))[:3]}")   # a too-short punch is reported as a string

cuts = [a for a, b, s in shots][1:]
if A.audio_cuts:
    def rms(t):
        s = seg_at(base, t)
        if s is None or card(s): return None
        src = (s["source_timerange"]["start"] + (t - s["target_timerange"]["start"])) / 1e6
        raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0,src-0.12):.3f}", "-t", "0.24",
                              "-i", res(vids[s["material_id"]]["path"]), "-ac", "1", "-ar", "8000",
                              "-f", "f32le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.float32)
        return float(np.sqrt((a**2).mean())) if len(a) else None
    lv = [(round(c/1e6, 2), rms(c)) for c in cuts]
    loud = [(t, round(v, 4)) for t, v in lv if v is not None and v > 0.035]
    chk(16, "כל חיתוך מצלמה נוחת ברגע שקט", len(loud) <= len(cuts) * 0.15,
        f"{len(cuts)} חיתוכים | רועשים {len(loud)} {loud[:3]}")
else:
    chk(16, "כל חיתוך מצלמה נוחת ברגע שקט", None, "לא נבדק — הרץ עם --audio-cuts")

# ── captions ─────────────────────────────────────────────────────────────────
caps = []
# הכתוביות = רצועת הטקסט הגדולה ביותר; רצועות טקסט נוספות (ערימות כותרת קינטיות
# ב-0910, שורה לכל רצועה) הן אוברליי בגובה משלהן ולא נמדדות בבדיקות 21–23
_text_tracks = [tk for tk in d["tracks"] if tk["type"] == "text" and tk["segments"]]
_cap_track = max(_text_tracks, key=lambda tk: len(tk["segments"])) if _text_tracks else None
_kinetic = sum(len(tk["segments"]) for tk in _text_tracks if tk is not _cap_track)
for tk in d["tracks"]:
    if tk["type"] != "text" or tk is not _cap_track: continue
    for s in tk["segments"]:
        c = json.loads(texts[s["material_id"]]["content"])
        # כותרת מזוהה גם לפי המקום ולא רק לפי האורך: כרטיס הכותרת ב-אורח O
        # הוא 3s בלבד, קצר מ-TITLE_MIN, ואז שמונה כותרות נספרו ככתוביות
        # והפילו את בדיקת הגובה ואת בדיקת הצבע.
        mid = s["target_timerange"]["start"] + s["target_timerange"]["duration"] // 2
        caps.append((s, c, s["target_timerange"]["duration"] >= TITLE_MIN or in_card(mid)))
body = [(s, c) for s, c, ti in caps if not ti]
ys = collections.Counter(round(s["clip"]["transform"]["y"], 4) for s, c in body)
chk(21, "גובה אחד לכל הכתוביות", len(ys) == 1, f"{len(body)} כתוביות | ערכים {dict(ys)}" + (f" | {_kinetic} שורות קינטיות ברצועות נפרדות" if _kinetic else ""))

try:
    from PIL import ImageFont
    FONT = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/bamberger-grunge-bold-fm.ttf")
    f88 = ImageFont.truetype(FONT, 88); lim = 0.82 * 1080
    wide = [(round(s["target_timerange"]["start"]/1e6, 2), c["text"], int(f88.getlength(c["text"])))
            for s, c in body if "\n" not in c["text"] and f88.getlength(c["text"]) > lim]
    chk(23, "כל כתובית נכנסת בשורה אחת", not wide, f"מותר {int(lim)}px | חורגות {len(wide)} {wide[:2]}")
except Exception as e:
    chk(23, "כל כתובית נכנסת בשורה אחת", None, f"לא נבדק: {e}")

noflag = []; badcol = []
for s, c in body:
    for st in c["styles"]:
        if not st.get("useLetterColor"): noflag.append(round(s["target_timerange"]["start"]/1e6, 2))
        col = tuple(round(v, 2) for v in st["fill"]["content"]["solid"]["color"])
        if col not in (YELLOW, WHITE): badcol.append((round(s["target_timerange"]["start"]/1e6, 2), col))
# הצבע הולך אחרי **המיקרופון**, לא אחרי מי שעל המסך. להחזיק על המאזין
# בזמן שהמארח זורק מילה זו החלטה, לא תקלה — ולכן "צהוב בזמן שמצלמה 2 על
# המסך" הוא מספר לדווח עליו, לא כישלון. מה שכן כישלון: צבע שמנוגד למי
# שמחזיק את הקול, וזה נמדד מהאודיו של קבצי המצלמה עצמם.
def _rms(tk, t, dur):
    s = seg_at(tk, t)
    if s is None or card(s) or not s.get("source_timerange"): return None
    # לא לחרוג מהמקטע: מעבר לגבול יושב רגע אחר לגמרי בפרק, ומדידה שגולשת
    # אליו מדווחת שהדובר השני הוא זה שמדבר
    left = (s["target_timerange"]["start"] + s["target_timerange"]["duration"] - t) / 1e6
    dur = min(dur, left)
    if dur < 0.15: return None
    src = (s["source_timerange"]["start"] + (t - s["target_timerange"]["start"])) / 1e6
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(0,src):.3f}", "-t", f"{dur:.3f}",
                          "-i", res(vids[s["material_id"]]["path"]), "-ac", "1", "-ar", "8000",
                          "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    return float((a**2).mean()) if len(a) else None
mic_bad = []; onscreen_agree = 0; ncap = 0
_snd = snd if snd is not None else ovl
for s, c in body:
    yellow = tuple(round(v, 2) for v in c["styles"][0]["fill"]["content"]["solid"]["color"]) == YELLOW
    r = s["target_timerange"]; ncap += 1
    on = sum(1 for t in range(r["start"], r["start"]+r["duration"], max(1, int(FR)*3))
             if seg_at(ovl, t, vis=True) is not None)
    shown = ST(ovl) if on > (r["duration"]/(FR*3)) / 2 else ST(base)
    if shown == f"cam{1 if yellow else 2}": onscreen_agree += 1
    if A.audio_cuts:
        # על טווח המילים עצמן, לא על חלון התצוגה: הכתובית נמתחת קדימה
        # ואחורה כדי שלא ייפתחו מרווחים, והמתיחה הזאת בולעת אודיו של הדובר
        # השני ומדווחת סתירה בכל מקום שבו אחד זורק מילה לתוך דברי השני.
        wi = texts[s["material_id"]].get("words") or {}
        # היסט שלילי הוא תקין: מילה שהתחילה לפני החיתוך והכתובית נצמדה
        # לתחילת הקליפ. למדוד ממנו אחורה זה למדוד את הקליפ הקודם.
        w0 = max(0.0, min(wi.get("start_time") or [0]) / 1000.0)
        w1 = max(wi.get("end_time") or [int(r["duration"]/1000)]) / 1000.0
        t0 = r["start"] + int(w0 * 1e6); d_ = max(0.2, min(w1 - w0, 2.0))
        e_base, e_snd = _rms(base, t0, d_), _rms(_snd, t0, d_)
        if e_base and e_snd:
            loud = CAM[id(base)] if e_base > e_snd else CAM[id(_snd if _snd is ovl else ovl)]
            ratio = 10 * np.log10(max(e_base, 1e-12) / max(e_snd, 1e-12))
            if abs(ratio) > 3 and loud != (1 if yellow else 2):
                mic_bad.append((round(r["start"]/1e6, 2), round(ratio, 1), c["text"][:18]))
pct = 100 * onscreen_agree / max(ncap, 1)
if not (CAM[id(base)] and CAM[id(ovl)]):
    chk(14, "צבע הכתובית הולך אחרי המיקרופון", None,
        "לא נבדק — אי אפשר לקרוא מהשמות איזו מצלמה בכל שכבה")
else:
    chk(14, "צבע הכתובית הולך אחרי המיקרופון", not mic_bad and pct > 50,
        f"תאימות למצלמה שעל המסך {pct:.0f}% (הפרש מכוון) | "
        + (f"סתירות מול המיקרופון {len(mic_bad)} {mic_bad[:3]}" if A.audio_cuts
           else "מול המיקרופון: לא נבדק — הרץ עם --audio-cuts"))
chk(24, "צבע לפי דובר + useLetterColor בכל סגנון", not noflag and not badcol,
    f"בלי useLetterColor {len(noflag)} | צבעים חורגים {len(badcol)} {badcol[:2]}")

sp = collections.Counter(texts[s["material_id"]].get("line_spacing", "—") for s, c in body)
chk(25, "מרווח שורות בערך הבית (-0.18)", set(sp) == {-0.18}, f"ערכים {dict(sp)}")

# ── the caption never touches a face ─────────────────────────────────────────
if A.faces and os.path.exists(A.faces):
    rows = json.load(open(A.faces))
    # face_scan ישן תייג את השכבות «cam1»/«cam2» כשהוא התכוון «עליונה»/«תחתונה»,
    # וזה יצא הפוך בכל פרויקט שבו העליונה היא מצלמה 2. מתרגמים, ולא מניחים.
    LAY = {"cam1": "top", "cam2": "bottom"}
    lay = lambda r: LAY.get(r["layer"], r["layer"])
    cy = (1 - list(ys)[0]) / 2 if len(ys) == 1 else None
    top = cy - A.caption_band / 2; bot = cy + A.caption_band / 2
    hit = []
    for r in rows:
        t = int(r["t"] * 1e6)
        if in_card(t): continue
        vis1 = seg_at(ovl, t, vis=True) is not None
        if in_split(t):
            # the lower half's brow, on the canvas: the half is pinned to the seam
            brow = r.get("browline")
            if brow is None and "fb" in r: brow = (960 + 607.5 * r["sc"] * r["fb"]) / 1920
            if lay(r) == "top" and brow is not None and brow < bot:
                hit.append((r["t"], "מצח תחתון", round(brow, 3)))
        else:
            # מצלמה אחת (ovl הוא הבסיס): כל הדגימות הן "bottom". בלי זה כל שורה
            # נזרקה והבדיקה עברה ריקה — 0 חפיפות מתוך 0 דגימות אמיתיות (0910).
            if lay(r) != ("bottom" if ovl is base else ("top" if vis1 else "bottom")): continue
            if r["chin"] > top: hit.append((r["t"], "סנטר", r["chin"]))
    chk(22, "הכתובית לא נוגעת בפנים באף פריים", not hit,
        f"רצועה {top:.3f}–{bot:.3f} | {len(rows)} דגימות | חפיפות {len(hit)} {hit[:3]}")

    # החצי שנשכח: transform.x = 0 ממרכז את **המקור**, ואיש לא יושב באמצע
    # של צילום שתיים. פעם אחת האורח נחת ב-76%–82% מרוחב הקנבס וכל 41
    # הבדיקות עברו, כי כולן מדדו את הציר האנכי.
    XLO, XHI = (float(v) for v in A.face_x.split(","))
    xs = [(r["t"], r["face_x"]) for r in rows if "face_x" in r
          and not in_card(int(r["t"]*1e6)) and not in_split(int(r["t"]*1e6))
          and lay(r) == ("bottom" if ovl is base else ("top" if seg_at(ovl, int(r["t"]*1e6), vis=True) is not None else "bottom"))]
    if not xs:
        chk(29, "מרכז הפנים לרוחב הקנבס", None,
            "לא נבדק — הרץ face_scan.py מחדש כדי לקבל face_x")
    else:
        far = [(t, round(v, 3)) for t, v in xs if v < XLO - 0.02 or v > XHI + 0.02]
        med = sorted(v for _, v in xs)[len(xs)//2]
        chk(29, f"מרכז הפנים לרוחב הקנבס בטווח {XLO:.2f}–{XHI:.2f}",
            len(far) <= len(xs) * 0.1,
            f"חציון {med:.3f} | {len(xs)} דגימות | מחוץ לטווח {len(far)} "
            f"{sorted(far, key=lambda r: -abs(r[1]-0.5))[:3]}")
else:
    chk(22, "הכתובית לא נוגעת בפנים באף פריים", None, "לא נבדק — חסר --faces")
    chk(29, "מרכז הפנים לרוחב הקנבס", None, "לא נבדק — חסר --faces")

# ── LUT ──────────────────────────────────────────────────────────────────────
lut = None; adjcov = 0
for tk in d["tracks"]:
    if tk["type"] != "adjust": continue
    for s in tk["segments"]:
        adjcov += s["target_timerange"]["duration"]
        for rid in s.get("extra_material_refs", []):
            for e in d["materials"].get("effects", []) or []:
                if e["id"] == rid and e.get("type") == "lut": lut = e
chk(26, "LUT המותג מכסה את כל האורך", lut is not None and abs(adjcov - END) < 50 * F,
    f"{(lut or {}).get('name', '—')} | כיסוי {adjcov/1e6:.2f} מתוך {END/1e6:.2f}")

# ── לוגואים ──────────────────────────────────────────────────────────────────
# אפס לוגואים הוא משלוח לגיטימי (ריל ללקוח של הבונקר), ולכן "אין" אינו כישלון
# אלא דיווח. מה שכן נכשל: לוגו שנוחת על כרטיס לבן, על מסך מפוצל, או שזז
# באמצע — הסלוט הוא מספר אחד לכל הפרויקט.
CW, CH = d["canvas_config"]["width"], d["canvas_config"]["height"]
still = lambda s: vids[s["material_id"]].get("type") == "photo" and not card(s)
# תמונה שתופסת כמעט את כל הרוחב היא אינסרט/כיסוי, לא לוגו — אחרת כל
# צילום מסך שנזרק על הטיימליין מדווח כלוגו שיושב בסלוט הלא נכון
small_still = lambda tk: max(s["clip"]["scale"]["x"] for s in tk["segments"]) < 0.45
logot = [tk for tk in d["tracks"] if tk["type"] == "video" and tk["segments"]
         and tk not in (base, ovl) and all(still(s) for s in tk["segments"]) and small_still(tk)]
if not logot:
    chk(27, "לוגואים", None, "אין לוגואים בפרויקט — ודא שזו הכוונה (ריל ללקוח) ולא השמטה")
else:
    bad = []; slots = []
    for tk in logot:
        # לרוב הטראקים אין שם — מזהים את הלוגו לפי הקובץ, אחרת הדוח אומר «?»
        tk = dict(tk, name=tk.get("name") or os.path.basename(
            vids[tk["segments"][0]["material_id"]]["path"]).replace("ccstudio-logo-", "")[:28])
        geo = {(round(s["clip"]["scale"]["x"], 4), round(s["clip"]["transform"]["x"], 4),
                round(s["clip"]["transform"]["y"], 4)) for s in tk["segments"]}
        if len(geo) > 1: bad.append(f"«{tk.get('name') or '?'}» זז ({len(geo)} מיקומים)")
        sc, tx, ty = sorted(geo)[0]
        slots.append(f"{100*(0.5+tx/2):.0f}%,{100*(0.5-ty/2):.0f}% ({100*sc:.0f}%w)")
        # סובלנות של 3 פריימים: גבול שנע בפריים בעקבות עריכה אינו "לוגו על
        # מסך מפוצל", והדיווח על החפיפה הגדולה ביותר אומר אם זה גבול או באמת
        # לוגו שיושב על פנים
        TOL = 3 * FR; worst = 0
        for s in tk["segments"]:
            a = s["target_timerange"]["start"]; b = a + s["target_timerange"]["duration"]
            for lbl, wins in (("כרטיס", cards), ("מסך מפוצל", [(x, y) for x, y, _ in splits])):
                for x, y in wins:
                    o = min(b, y) - max(a, x)
                    if o > 0: worst = max(worst, o)
                    if o > TOL: bad.append(f"«{tk['name']}» על {lbl} ב-{max(a,x)/1e6:.2f}s ({o/1e6:.2f}s)")
        slots[-1] += f", חפיפה מרבית {worst/1e6:.2f}s"
    chk(27, "לוגואים: על צילום בלבד, מחוץ לפיצולים, סלוט קבוע", not bad,
        f"{len(logot)} לוגואים | {' · '.join(slots)}"
        + (f" | {len(bad)} חריגות {bad[:3]}" if bad else ""))

# 8b. Auto-reframe של CapCut (smart_crop) מתחת למסגור שלנו = זום כפול. על 0910
# אלון הריץ Auto reframe ל-9:16 (חיתוך 0.37–0.69 מרוחב המקור), ומעליו ישב
# fill-scale ×3.16 שלנו — CapCut הראה ×10, רק פה ומיקרופון, וכל בדיקת הסקייל
# עברה כי כולן מודדות את ה-JSON ולא את מה ש-CapCut מרנדר.
_sc_ids = {m["id"] for m in d["materials"].get("smart_crops", [])}
_stacked = []
for tk in vt:
    for s in tk["segments"]:
        m = vids.get(s["material_id"], {})
        if m.get("type") == "photo" or not m.get("path"): continue
        if _sc_ids & set(s.get("extra_material_refs", [])) and s["clip"]["scale"]["x"] > 1.2:
            _stacked.append(round(s["target_timerange"]["start"] / 1e6, 2))
chk("8b", "אין Auto-reframe (smart_crop) של CapCut מתחת למסגור שלנו", not _stacked,
    f"smart_crop materials {len(_sc_ids)} | קטעי צילום עם חיתוך חכם וגם scale>1.2: {len(_stacked)} {_stacked[:4]}")

# מזהה בדיקה יכול להיות "4b" — ממיינים לפי המספר ואז לפי הסיומת, כך שבדיקה
# חדשה שנתלית על קיימת לא מפילה את הריצה כולה על ValueError
def _key(n):
    m = re.match(r"(\d+)(\D*)$", str(n)); return (int(m.group(1)), m.group(2))
R.sort(key=lambda r: _key(r[0]))
w = max(len(t) for _, t, _, _ in R)
for n, title, ok, detail in R:
    # מספר הבדיקה הוא המזהה שלה, לא מקומה בתור — הסקיל מפנה אליהן בשם,
    # וספירה רצה מזיזה את כולן בכל פעם שנוספת בדיקה באמצע.
    mark = "✅" if ok else ("⏭️ " if ok is None else "❌")
    print(f"{mark} {str(n):>3s}. {title:{w}s}  {detail}")
p = sum(1 for r in R if r[2] is True); s = sum(1 for r in R if r[2] is None)
print(f"\nעברו {p}/{len(R)}" + (f" | לא נבדקו {s}" if s else "") + f" | נכשלו {len(R)-p-s}")
sys.exit(1 if len(R) - p - s else 0)
