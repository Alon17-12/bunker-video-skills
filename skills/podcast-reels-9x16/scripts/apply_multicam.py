# -*- coding: utf-8 -*-
"""Route the multicam by opacity on a project whose two angles already cover
every range: the lower track holds one camera at alpha 1 for the whole film and
never flips, the upper track is split at the cuts and each piece is alpha 1 or 0.

    python apply_multicam.py "<project>" --audio ".../… - אודיו" \
        --mic-offset -0.1485                        # dry run
    ... --write

Why this shape and not "lay camera 2 only where camera 2 is shown": Alon asked
for it by name — he opens the project, sees both angles, and fixes any decision
with the Opacity slider. Deleting the losing camera's frames sends him back to
me for every change.

The mics decide, not the cameras: mic n belongs to camera n, and the ratio
between the two channels is what separates "one man talking" from "both mics are
loud", because bleed puts one man at 5–15% of his own level on the other's mic.
"""
import argparse, copy, json, os, re, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
HOP = 0.01

ap = argparse.ArgumentParser(description="alpha-routed multicam from the two mics")
ap.add_argument("project")
ap.add_argument("--audio", required=True, help="folder holding the per-mic wavs")
ap.add_argument("--mic-offset", type=float, default=0.0,
                help="seconds to add to camera source time when reading the mics — "
                     "measure it, the RODECASTER channels are not sample-aligned "
                     "to the cameras")
ap.add_argument("--bottom", type=int, default=0, help="track index of the fallback camera")
ap.add_argument("--top", type=int, default=1, help="track index of the toggling camera")
ap.add_argument("--top-cam", type=int, default=1, help="which camera the upper track holds")
ap.add_argument("--min-shot", type=float, default=1.0)
ap.add_argument("--min-interject", type=float, default=0.40,
                help="a shorter burst on the other mic is not a shot")
ap.add_argument("--owns", type=float, default=1.6, help="mic n louder by this = speaker n")
ap.add_argument("--nudge", type=float, default=0.35, help="hunt for silence within ±this")
ap.add_argument("--from", dest="t_from", type=float, default=None,
                help="שניות בציר — לנתב רק מכאן והלאה. הכרחי כשמוסיפים רילס "
                     "לפרויקט שאלון כבר ניתב ביד: בלי זה הריצה מקפלת את "
                     "החתיכות שלו בחזרה ומחליטה מחדש, כלומר מוחקת את העריכה שלו.")
ap.add_argument("--to", dest="t_to", type=float, default=None)
ap.add_argument("--write", action="store_true")
A = ap.parse_args()

DST = capcut.DRAFTS_DIR / A.project
pid = capcut._capcut_pid()
if A.write and pid and f"{DST}/" in capcut._capcut_open_files(pid):
    sys.exit("✗ CapCut מחזיק את הפרויקט — לצאת למסך הבית ולהריץ שוב")

d = json.loads((DST / "draft_info.json").read_text())
FR = US / d.get("fps", 30.0)
snap = lambda t: int(round(t / FR) * FR)                                   # noqa: E731
vids = {m["id"]: m for m in d["materials"]["videos"]}
idx = capcut._materials_index(d)
bottom, top = d["tracks"][A.bottom], d["tracks"][A.top]
for t in (bottom, top):
    t["segments"].sort(key=lambda s: s["target_timerange"]["start"])
is_card = lambda s: vids[s["material_id"]].get("type") == "photo"          # noqa: E731
LO = int((A.t_from or 0) * US)
HI = int(A.t_to * US) if A.t_to is not None else 1 << 62
in_win = lambda s: LO <= s["target_timerange"]["start"] < HI                # noqa: E731
foot = [s for s in bottom["segments"] if not is_card(s) and in_win(s)]
keep_top = [s for s in top["segments"] if not in_win(s)]   # מחוץ לחלון — לא נוגעים


def collapse(segs):
    """Re-run on an already-routed project: glue the pieces back into the ranges
    they were split from, so a second pass re-decides instead of splitting the
    splits. The seams that matter are the *bottom* track's — two neighbouring
    takes can be continuous in source and still be two different shots."""
    out = []
    for b in foot:
        a = b["target_timerange"]["start"]
        z = a + b["target_timerange"]["duration"]
        inside = [s for s in segs if a <= s["target_timerange"]["start"] < z]
        if not inside:
            return segs
        whole = copy.deepcopy(inside[0])
        whole["target_timerange"] = {"start": a, "duration": z - a}
        whole["source_timerange"] = {"start": inside[0]["source_timerange"]["start"],
                                     "duration": z - a}
        out.append(whole)
    return out


top["segments"] = collapse([s for s in top["segments"] if in_win(s)])
if len(foot) != len(top["segments"]):
    sys.exit(f"✗ {len(foot)} מקטעי צילום למטה מול {len(top['segments'])} למעלה — "
             "השכבות לא מכסות את אותם טווחים")


def mic_paths(folder):
    out = {}
    for f in sorted(os.listdir(folder)):
        if f.startswith("._") or not f.lower().endswith(".wav") or "mix" in f.lower():
            continue
        # ⚠️ הספרה *האחרונה*, לא הראשונה. «03.08.26 - … - אודיו 1.wav» מתחיל
        # ב-0, בדיוק כמו ה-4 של .mp4 שהפיל פעם את זיהוי המצלמות.
        dg = re.findall(r"\d", os.path.splitext(f)[0])
        if dg:
            out.setdefault(int(dg[-1]), os.path.join(folder, f))
    if set(out) != {1, 2}:
        sys.exit(f"✗ ציפיתי לשני ערוצי מיקרופון ממוספרים, מצאתי {sorted(out)}")
    return out


MIC = mic_paths(A.audio)


def env(path, ss, dur):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{max(ss,0):.6f}", "-t", f"{dur:.6f}",
                          "-i", path, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    h = int(8000 * HOP)
    k = max(len(x) // h, 1)
    e = np.sqrt((x[:k * h].reshape(k, h) ** 2).mean(1)) if len(x) >= h else np.zeros(1)
    n = int(round(dur / HOP))
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e), np.float32)])
    return np.convolve(e[:n], np.ones(7) / 7, mode="same")


def route(e1, e2):
    """[(t0, t1, camera)] over one segment."""
    floor = max(np.percentile(np.concatenate([e1, e2]), 25), 1e-5)
    own = np.zeros(len(e1), np.int8)
    live = (e1 > 2.0 * floor) | (e2 > 2.0 * floor)
    own[live & (e1 > A.owns * e2)] = 1
    own[live & (e2 > A.owns * e1)] = 2
    cur = 3 - A.top_cam                       # silence holds the fallback camera
    filled = np.empty(len(own), np.int8)
    for i, v in enumerate(own):
        if v:
            cur = v
        filled[i] = cur
    runs, st = [], 0
    for i in range(1, len(filled) + 1):
        if i == len(filled) or filled[i] != filled[st]:
            runs.append([st * HOP, i * HOP, int(filled[st])])
            st = i
    # A shot under the floor either grows into it or gives way. Growing matters:
    # his 0.4–1.0s interjections are the cuts a minimum-shot pass throws away,
    # and then he is off screen delivering the punchline.
    changed = True
    rounds = 0                                # two short shots lending time to each other forever (24.10.2026, a 7-min take hung 35 min)
    while changed and len(runs) > 1:
        changed = False; rounds += 1
        for i, r in enumerate(runs):
            if r[1] - r[0] >= A.min_shot:
                continue
            if r[2] == A.top_cam and r[1] - r[0] >= A.min_interject and rounds < 200:
                need = A.min_shot - (r[1] - r[0])
                if i > 0 and runs[i - 1][1] - runs[i - 1][0] > need + A.min_shot:
                    runs[i - 1][1] -= need / 2; r[0] -= need / 2
                if i + 1 < len(runs) and runs[i + 1][1] - runs[i + 1][0] > need + A.min_shot:
                    runs[i + 1][0] += need / 2; r[1] += need / 2
                if r[1] - r[0] >= A.min_shot - 1e-6:
                    changed = True
                    continue
            nb = runs[i - 1] if i > 0 else runs[i + 1]
            nb[0] = min(nb[0], r[0]); nb[1] = max(nb[1], r[1])
            runs.pop(i); changed = True
            break
    merged = [runs[0]]
    for r in runs[1:]:
        if r[2] == merged[-1][2]:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def quiet(e1, e2, t):
    i = int(t / HOP)
    lo, hi = max(0, i - int(A.nudge / HOP)), min(len(e1), i + int(A.nudge / HOP) + 1)
    if hi <= lo:
        return t
    return (lo + int(np.argmin(e1[lo:hi] + e2[lo:hi]))) * HOP


def clone_extras(seg):
    refs = []
    for r in seg.get("extra_material_refs", []):
        if r in idx:
            bucket, mm = idx[r]
            cc = copy.deepcopy(mm); cc["id"] = capcut._new_id()
            d["materials"].setdefault(bucket, []).append(cc)
            refs.append(cc["id"])
    return refs


new_top, shots, vis_us, hid_us = [], [], 0, 0
for b, t in zip(foot, top["segments"]):
    S, D = b["target_timerange"]["start"], b["target_timerange"]["duration"]
    SRC = t["source_timerange"]["start"]
    e1 = env(MIC[1], SRC / US + A.mic_offset, D / US)
    e2 = env(MIC[2], SRC / US + A.mic_offset, D / US)
    segs = route(e1, e2)
    # A cut wants the quietest hundredth near it, but not at the price of a shot
    # under the floor, so every nudge is clamped by its neighbours.
    bnds = [0]
    for k in range(1, len(segs)):
        lo = bnds[-1] / US + A.min_shot
        hi = segs[k][1] - A.min_shot
        bnds.append(snap(min(max(quiet(e1, e2, segs[k][0]), lo), max(hi, lo)) * US))
    bnds.append(D)
    pieces = []
    for k, r in enumerate(segs):
        a, bb = bnds[k], bnds[k + 1]
        if pieces and (bb - a < FR or r[2] == pieces[-1][2]):
            pieces[-1][1] = bb
        else:
            pieces.append([a, bb, r[2]])
    pieces[-1][1] = D
    for a, bb, cam in pieces:
        s = copy.deepcopy(t)
        s["id"] = capcut._new_id()
        s["extra_material_refs"] = clone_extras(t)
        s["common_keyframes"] = []; s["keyframe_refs"] = []
        s["target_timerange"] = {"start": S + a, "duration": bb - a}
        s["source_timerange"] = {"start": SRC + a, "duration": bb - a}
        s["clip"] = copy.deepcopy(t["clip"])
        s["clip"]["alpha"] = 1.0 if cam == A.top_cam else 0.0
        new_top.append(s)
        shots.append((bb - a) / US)
        if cam == A.top_cam:
            vis_us += bb - a
        else:
            hid_us += bb - a

for s in bottom["segments"]:
    if in_win(s):
        s["clip"]["alpha"] = 1.0              # the fallback picture never flips

sh = sorted(shots)
print(f"עליונה: {len(new_top)} חתיכות | גלויה {vis_us/US:.1f}s "
      f"({100*vis_us/max(vis_us+hid_us,1):.1f}%) | מוסתרת {hid_us/US:.1f}s")
print(f"אורך שוט: מינימום {sh[0]:.2f}s | חציון {sh[len(sh)//2]:.2f}s | מקסימום {sh[-1]:.2f}s")
prev, holes = None, 0
for s in sorted(new_top, key=lambda s: s["target_timerange"]["start"]):
    a = s["target_timerange"]["start"]
    if prev is not None and a != prev:
        holes += 1
    prev = a + s["target_timerange"]["duration"]
print(f"קפיצות בשכבה העליונה: {holes} (החוצצים לגיטימיים)")
if A.t_from is not None or A.t_to is not None:
    print(f"מחוץ לחלון {LO/US:.2f}–{min(HI,1<<61)/US:.2f}: {len(keep_top)} מקטעים "
          f"בשכבה העליונה נשארו כפי שהם")

if not A.write:
    print("(יבש — בלי --write לא נכתב כלום)")
    sys.exit()

capcut._backup(DST)
top["segments"] = sorted(keep_top + new_top,
                         key=lambda s: s["target_timerange"]["start"])
tmp = DST / "draft_info.json.tmp"
tmp.write_text(json.dumps(d, ensure_ascii=False))
json.loads(tmp.read_text())
tmp.replace(DST / "draft_info.json")
print("✓ נכתב")
