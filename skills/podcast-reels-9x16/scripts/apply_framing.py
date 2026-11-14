# -*- coding: utf-8 -*-
"""Copy the framing Alon approved on one reel onto the reels that follow it.

The situation this exists for: he re-cuts the first reel by hand — pulls a
camera back, fills a split half, moves a pan — and says *"תדייק את הבאים
אחריו"*. The numbers are then sitting in the draft, and the job is to read them
per camera and per role and re-anchor the rest to them, keeping each shot's own
push-in.

It reads the *rendered* geometry, not the raw `scale`, because CapCut crops at
the material level and the same number means different things on two angles: on
`0810` camera 2 carries a square crop (0.3486,0.1038)-(0.8283,0.9566), so it
fills the canvas at scale 1.78 while camera 1 needs 3.16. A pass that copied
`scale` across cameras would be nonsense.

    apply_framing.py "<project>" --from 0:127.6 --to 145.8:  [--write]

Roles are read off the geometry: a segment that covers the canvas is `full`, a
segment pushed off-centre and smaller is `split-top` / `split-bottom`. Groups
are (camera, role), and only groups present in BOTH ranges are touched.

Keyframes are re-anchored, not flattened: each key keeps its offset from its
segment's base value, scaled by the same ratio as the base, so the shot's own
push-in survives.
"""
import sys, json, os, re, shutil, argparse, statistics, collections
sys.path.insert(0, 'app'); import capcut

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--from", dest="src", required=True, help="הטווח המאושר, בשניות: A:B")
ap.add_argument("--to", dest="dst", required=True, help="הטווח לתיקון, בשניות: C:D (אפשר להשמיט צד)")
ap.add_argument("--write", action="store_true")
A = ap.parse_args()

def rng(s):
    a, _, b = s.partition(":")
    return (float(a) * 1e6 if a else 0.0, float(b) * 1e6 if b else float("inf"))
SRC, DST = rng(A.src), rng(A.dst)
NAME = A.project; D = capcut.DRAFTS_DIR / NAME; P = D / "draft_info.json"
CW, CH = 1080, 1920

d = json.load(open(P))
vids = {m["id"]: m for m in d["materials"]["videos"]}

def crop_of(m):
    c = m.get("crop") or {}
    x0, y0 = c.get("upper_left_x", 0.0), c.get("upper_left_y", 0.0)
    x1, y1 = c.get("lower_right_x", 1.0), c.get("lower_right_y", 1.0)
    return (0.0, 0.0, 1.0, 1.0) if (x1 <= x0 or y1 <= y0) else (x0, y0, x1, y1)

def rendered(m, s):
    """גודל המלבן על הקנבס. CapCut «מכיל» את המלבן החתוך, ולכן זה תלוי ב-crop."""
    x0, y0, x1, y1 = crop_of(m)
    w = (m.get("width") or 1920) * (x1 - x0); h = (m.get("height") or 1080) * (y1 - y0)
    ar = w / h
    if ar >= CW / CH: rw = CW * s; rh = rw / ar
    else:             rh = CH * s; rw = rh * ar
    return rw, rh

def cam_of(m):
    # בלי הסיומת. «… - 1.mp4» מסתיים בספרה 4 בתוך «mp4», וחיפוש הספרה האחרונה
    # על השם המלא איחד את שתי המצלמות לקבוצה אחת בשם cam4 — ואז ממוצע הפריימינג
    # של שתי הזוויות היה נכתב על שתיהן.
    p = os.path.splitext(os.path.basename(m["path"]))[0]
    mm = re.search(r"cam\s*(\d)", p) or re.search(r"(\d)\s*$", p)
    return f"cam{mm.group(1)}" if mm else p[:14]

def role_of(sg, m):
    s = sg["clip"]["scale"]["x"]; y = sg["clip"]["transform"]["y"]
    rw, rh = rendered(m, s)
    if rw >= CW - 1 and rh >= CH - 1: return "full"
    if y > 0.15:  return "split-top"
    if y < -0.15: return "split-bottom"
    return "other"

segs = []
for tk in d["tracks"]:
    if tk["type"] != "video": continue
    for sg in tk["segments"]:
        m = vids[sg["material_id"]]
        if m.get("type") == "photo" or m["path"].endswith(".image"): continue
        t = sg["target_timerange"]["start"]
        segs.append((t, cam_of(m), role_of(sg, m), sg, m, tk))

def group(lo, hi):
    g = collections.defaultdict(list)
    for t, cam, role, sg, m, tk in segs:
        if lo <= t < hi and role != "other": g[(cam, role)].append(sg)
    return g
G_src, G_dst = group(*SRC), group(*DST)

med = lambda v: round(statistics.median(v), 4)
print(f"=== המאושר {A.src}")
target = {}
for k in sorted(G_src):
    v = G_src[k]
    target[k] = (med([s["clip"]["scale"]["x"] for s in v]),
                 med([s["clip"]["transform"]["x"] for s in v]),
                 med([s["clip"]["transform"]["y"] for s in v]))
    sc = [round(s["clip"]["scale"]["x"], 3) for s in v]
    print(f"  {k[0]:5s} {k[1]:12s} n={len(v):3d}  s={target[k][0]:.4f} x={target[k][1]:+.4f} "
          f"y={target[k][2]:+.4f}   (טווח סקייל {min(sc)}–{max(sc)})")

print(f"\n=== לתיקון {A.dst}")
plan = []
for k in sorted(G_dst):
    v = G_dst[k]
    cur = (med([s["clip"]["scale"]["x"] for s in v]),
           med([s["clip"]["transform"]["x"] for s in v]),
           med([s["clip"]["transform"]["y"] for s in v]))
    if k not in target:
        print(f"  {k[0]:5s} {k[1]:12s} n={len(v):3d}  s={cur[0]:.4f} — אין מקבילה במאושר, לא נוגעים")
        continue
    ns, nx, ny = target[k]
    same = abs(cur[0]-ns) < 1e-4 and abs(cur[1]-nx) < 1e-4 and abs(cur[2]-ny) < 1e-4
    print(f"  {k[0]:5s} {k[1]:12s} n={len(v):3d}  s {cur[0]:.4f}→{ns:.4f}  x {cur[1]:+.4f}→{nx:+.4f}  "
          f"y {cur[2]:+.4f}→{ny:+.4f}" + ("   (זהה, מדלגים)" if same else ""))
    if not same: plan.append((k, v, ns, nx, ny))
if not plan: sys.exit("\nאין מה לשנות.")
if not A.write: sys.exit("\n(הרצה יבשה — הוסף --write)")

pid = capcut._capcut_pid()
if pid is not None and f"{D}/" in capcut._capcut_open_files(pid):
    sys.exit(f"✗ {NAME} פתוח כרגע ב-CapCut — צא למסך הבית")
shutil.copy2(P, P.with_suffix(".json.preframing-backup"))
before = json.load(open(P))

KS = ("KFTypeScaleX", "KFTypeScaleY"); KX = "KFTypePositionX"; KY = "KFTypePositionY"
touched = 0
for k, v, ns, nx, ny in plan:
    for sg in v:
        c = sg["clip"]
        os_, ox, oy = c["scale"]["x"], c["transform"]["x"], c["transform"]["y"]
        r = ns / os_ if os_ else 1.0
        c["scale"]["x"] = c["scale"]["y"] = ns
        c["transform"]["x"], c["transform"]["y"] = nx, ny
        for ck in sg.get("common_keyframes", []):
            p = ck["property_type"]
            for kf in ck["keyframe_list"]:
                val = kf["values"][0]
                # מעגנים מחדש ושומרים על צורת התנועה: ההפרש מהבסיס גדל באותו יחס
                if p in KS:  kf["values"][0] = val * r
                elif p == KX: kf["values"][0] = nx + (val - ox) * r
                elif p == KY: kf["values"][0] = ny + (val - oy) * r
        touched += 1

tmp = P.with_suffix(".json.tmp")
tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
json.loads(tmp.read_text()); tmp.replace(P)

after = json.load(open(P))
def outside(doc):
    out = []
    for tk in doc["tracks"]:
        for sg in tk.get("segments", []):
            t = sg["target_timerange"]["start"]
            if not (DST[0] <= t < DST[1]):
                out.append(json.dumps(sg, sort_keys=True, ensure_ascii=False))
    return out
ok = outside(before) == outside(after)
print(f"\n✓ {touched} מקטעים תוקנו · כל מה שמחוץ לטווח {A.dst} ללא שינוי: {ok}")
if not ok: print("  ⚠ שחזר מ-", P.with_suffix('.json.preframing-backup').name)
