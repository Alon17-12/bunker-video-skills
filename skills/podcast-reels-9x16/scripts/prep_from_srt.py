# -*- coding: utf-8 -*-
"""Build an edit-prep CapCut project straight from the client's SRT markings.

This is stage 3+4 of the pipeline when the ask is *"הכן לעריכה"* rather than
"finish it": lay every marked range on the timeline, in order, with a white
separator between blocks, both angles present, and nothing else — no multicam
routing, no captions, no grade. The editor (or a later pass) does the rest.

    prep_from_srt.py --donor "<draft to clone settings from>" --name "<new draft>" \
        --cam1 <file> --cam2 <file> --offset 11.8356 \
        --block "רגעי שיא=<highlights.srt>" \
        --reels "<reels.srt>" --hooks "<hooks.srt>" \
        --extra "סיינטולוגיה=2774:3598" --card 2 --write

**The offset is the whole ballgame.** Client marks are timed to their
convenience file, which is a different recorder with a different start. Measure
it (cross-correlate, three windows) and *verify it against the quoted words*
before running this — a run with the wrong offset produces a project that looks
perfectly built and contains the wrong sentences. `--extra` ranges are given in
SOURCE seconds (already on the angle timeline), because they usually come from a
transcript rather than from the client's marks; everything from an SRT gets
`--offset` added.

Both angles are laid on two stacked tracks over exactly the same windows: the
lower one visible and audible, the upper one at `alpha 0, volume 0`. That is the
house delivery format — the editor flips Opacity to do the multicam himself —
and it costs nothing to prepare now.
"""
import sys, os, re, json, copy, time, shutil, argparse, subprocess
sys.path.insert(0, 'app'); import capcut
sys.path.insert(0, os.path.join(os.getcwd(), 'app'))
import reels as reels_mod

US = 1_000_000
ap = argparse.ArgumentParser()
ap.add_argument("--donor", required=True, help="פרויקט קיים שממנו נלקחות ההגדרות ותבניות המקטעים")
ap.add_argument("--name", required=True)
# --cam1 היא השכבה **הנראית**. ברירת המחדל השימושית היא הדובר הדומיננטי בקטעים
# שנבחרו (כאן האורח, 77% מהחלונות), לא «מצלמה 1» מתוך נאמנות למספור.
ap.add_argument("--cam1", required=True, help="הזווית הנראית (השכבה התחתונה)")
ap.add_argument("--cam2", help="הזווית המוסתרת, alpha 0 — חומר למולטי-קאם ידני")
ap.add_argument("--offset", type=float, default=0.0, help="שניות להוסיף לזמני ה-SRT כדי להגיע לזמן הזווית")
ap.add_argument("--block", action="append", default=[], help="«שם=קובץ.srt» — כל הקיוז כבלוק אחד")
ap.add_argument("--reels", help="SRT שכל קיו בו הוא ריל = בלוק משלו")
ap.add_argument("--hooks", help="SRT של הוקים; כל הוק נשתל לפני הריל שמכיל אותו")
ap.add_argument("--extra", action="append", default=[], help="«שם=start:end» בשניות של המקור (בלי offset)")
ap.add_argument("--card", type=float, default=2.0, help="אורך מקטע החציצה הלבן, שניות")
ap.add_argument("--fps", type=float, default=30.0)
ap.add_argument("--lead-card", action="store_true",
                help="חוצץ גם לפני הבלוק הראשון, לא רק בין בלוקים")
ap.add_argument("--titles", action="store_true",
                help="לכתוב את שם הבלוק על החוצץ שלפניו")
ap.add_argument("--title-donor", help="פרויקט שממנו נלקח סגנון הכותרת (מקטע הטקסט הארוך ביותר בו)")
ap.add_argument("--title-color", default="#16191e", help="צבע הכותרת על החוצץ הלבן")
ap.add_argument("--title-size", type=float, default=0.0,
                help="0 = להתאים אוטומטית כך שהשורה הארוכה תתפוס --title-fill מרוחב הקנבס. "
                     "גודל הטקסט ב-CapCut נמדד מול **גובה** הקנבס (px ≈ 0.0026518·size·H), "
                     "ולכן מספר שנקרא מפרויקט 9:16 מייצר כותרת זעירה על 16:9")
ap.add_argument("--title-fill", type=float, default=0.58, help="חלק מרוחב הקנבס שהשורה הארוכה תתפוס")
ap.add_argument("--carry-audio", action="store_true",
                help="לחתוך גם את רצועות האודיו של הדונור לאותם טווחים (מושתקות)")
ap.add_argument("--carry-adjust", action="store_true",
                help="להעתיק את שכבת ה-adjust של הדונור — על הפוטג\' בלבד, לא על החוצצים")
ap.add_argument("--write", action="store_true")
A = ap.parse_args()

def parse_srt(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r", "")
    out = []
    for b in raw.split("\n\n"):
        L = [x for x in b.split("\n") if x.strip()]
        if len(L) < 2: continue
        m = re.search(r"(\d\d):(\d\d):(\d\d),(\d+)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d+)", "\n".join(L))
        if not m: continue
        f = lambda a, b_, c, d: int(a)*3600 + int(b_)*60 + int(c) + int(d)/1000
        txt = " ".join(x for x in L if "-->" not in x and not x.strip().isdigit()).strip()
        out.append((f(*m.groups()[:4]), f(*m.groups()[4:]), txt))
    return sorted(out)

def merge(rs):
    """מאחדים רק חפיפה אמיתית. שני רגעים צמודים הם עדיין שני רגעים."""
    out = []
    for a, b, t in rs:
        if out and a < out[-1][1]: out[-1] = (out[-1][0], max(out[-1][1], b), out[-1][2])
        else: out.append((a, b, t))
    return out

# ── the blocks, in order ─────────────────────────────────────────────────────
blocks = []          # (label, [(src_start_s, src_end_s), ...])
for spec in A.block:
    label, _, path = spec.partition("=")
    rs = merge(parse_srt(path))
    blocks.append((label, [(a + A.offset, b + A.offset) for a, b, _ in rs], len(rs)))
if A.reels:
    hooks = parse_srt(A.hooks) if A.hooks else []
    for i, (a, b, t) in enumerate(parse_srt(A.reels), 1):
        segs = []
        for ha, hb, _ in hooks:
            if a <= ha < b: segs.append((ha + A.offset, hb + A.offset))
        segs.append((a + A.offset, b + A.offset))
        blocks.append((f"ריל {i} · {t}", segs, len(segs)))
for spec in A.extra:
    label, _, rng = spec.partition("=")
    a, _, b = rng.partition(":")
    blocks.append((label, [(float(a), float(b))], 1))

def title_lines(label, w=26):
    """«ריל 3 · טקסט ארוך» → שורת מספר + הכותרת עטופה לשורות קצרות."""
    out = []
    for part in label.split(" · "):
        cur = ""
        for word in part.split():
            if cur and len(cur) + 1 + len(word) > w: out.append(cur); cur = word
            else: cur = f"{cur} {word}".strip()
        if cur: out.append(cur)
    return out

FR = US / A.fps
# 30fps → 33333.333µs. גם משך וגם התחלה חייבים לשבת על אותה רשת, ו**אסור**
# לעגל התחלה שכבר נבנתה כסכום של משכים מעוגלים: העיגול הכפול מזיז מיקרו-שנייה,
# וזה חור בטראק הראשי — ש-CapCut סוגר בריפל ומזיז את כל הפרויקט בפתיחה.
snap = lambda us: int(round(us / FR) * FR)
print(f"{len(blocks)} בלוקים · חציצה לבנה {A.card}s · offset {A.offset:+.4f}s")
tot = 0
for label, segs, n in blocks:
    d = sum(b - a for a, b in segs)
    tot += d + A.card
    print(f"   {label[:52]:54s} {len(segs)} מקטעים · {d/60:5.2f} דק' · מקור "
          f"{segs[0][0]/60:6.2f}–{segs[-1][1]/60:6.2f} דק'")
print(f"סה\"כ ≈ {tot/60:.2f} דקות")
if not A.write: sys.exit("\n(הרצה יבשה — הוסף --write)")
if capcut._capcut_pid() is not None:
    sys.exit("✗ CapCut פתוח — רישום פרויקט חדש דורש שהוא יהיה סגור")

# ── clone the donor, keep its settings, throw away its timeline ──────────────
src_dir = capcut.DRAFTS_DIR / A.donor
new_name = reels_mod._unique_name(A.name)
dst_dir = capcut.DRAFTS_DIR / new_name
reels_mod._copy_draft_folder(src_dir, dst_dir)
try:
    d = json.loads((dst_dir / "draft_info.json").read_text())
    vt = [t for t in d["tracks"] if t["type"] == "video" and t["segments"]]
    seg_tpl = next(copy.deepcopy(s) for t in vt for s in t["segments"]
                   if (next((m for m in d["materials"]["videos"]
                             if m["id"] == s["material_id"]), {}) or {}).get("type") == "video")
    mat_tpl = copy.deepcopy(next(m for m in d["materials"]["videos"] if m.get("type") == "video"))
    trk_tpl = copy.deepcopy(vt[0]); trk_tpl["segments"] = []

    white = dst_dir / "ccstudio-card.png"
    subprocess.run([os.path.expanduser("~/ffmpeg-bin/ffmpeg"), "-y", "-f", "lavfi",
                    "-i", f"color=white:s={d['canvas_config']['width']}x{d['canvas_config']['height']}",
                    "-frames:v", "1", str(white)], capture_output=True, check=True)
    pmat, pseg, pextras = reels_mod._photo_donor()

    def probe(path):
        r = subprocess.run([os.path.expanduser("~/ffmpeg-bin/ffprobe"), "-v", "error",
                            "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:format=duration", "-of", "json", path],
                           capture_output=True, text=True).stdout
        j = json.loads(r)
        return (int(j["streams"][0]["width"]), int(j["streams"][0]["height"]),
                int(float(j["format"]["duration"]) * US))

    donor_audio  = [t for t in d["tracks"] if t.get("type") == "audio"  and t.get("segments")]
    donor_adjust = [t for t in d["tracks"] if t.get("type") == "adjust" and t.get("segments")]

    d["materials"]["videos"] = []
    for ln in ("audios", "texts", "effects", "canvases", "stickers"):
        if isinstance(d["materials"].get(ln), list) and ln in ("texts",): d["materials"][ln] = []
    cams = {}
    for cam, path in ((1, A.cam1), (2, A.cam2)):
        if not path: continue
        w, h, dur = probe(path)
        m = copy.deepcopy(mat_tpl)
        m.update({"id": capcut._new_id(), "path": path, "width": w, "height": h,
                  "duration": dur, "material_name": os.path.basename(path),
                  "type": "video", "crop_scale": 1.0})
        m["crop"] = {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0,
                     "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0,
                     "lower_right_x": 1.0, "lower_right_y": 1.0}
        d["materials"]["videos"].append(m); cams[cam] = m

    def footage(cam, a_s, b_s, t_us, visible):
        s = copy.deepcopy(seg_tpl)
        s["id"] = capcut._new_id(); s["material_id"] = cams[cam]["id"]
        s["target_timerange"] = {"start": int(t_us), "duration": snap(int((b_s - a_s) * US))}
        s["source_timerange"] = {"start": snap(int(a_s * US)), "duration": s["target_timerange"]["duration"]}
        s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
        s["clip"]["transform"] = {"x": 0.0, "y": 0.0}
        s["clip"]["alpha"] = 1.0 if visible else 0.0
        s["volume"] = 1.0 if visible else 0.0
        s["common_keyframes"] = []; s["keyframe_refs"] = []
        s["extra_material_refs"] = []
        return s

    def card(t_us):
        m = copy.deepcopy(pmat)
        m.update({"id": capcut._new_id(), "path": str(white), "material_name": "ccstudio-card.png",
                  "type": "photo", "width": d["canvas_config"]["width"],
                  "height": d["canvas_config"]["height"]})
        d["materials"]["videos"].append(m)
        s = copy.deepcopy(pseg); s["id"] = capcut._new_id(); s["material_id"] = m["id"]
        s["target_timerange"] = {"start": int(t_us), "duration": snap(int(A.card * US))}
        s["source_timerange"] = {"start": 0, "duration": s["target_timerange"]["duration"]}
        s["clip"]["scale"] = {"x": 1.0, "y": 1.0}; s["clip"]["transform"] = {"x": 0.0, "y": 0.0}
        s["clip"]["alpha"] = 1.0; s["volume"] = 0.0
        s["common_keyframes"] = []; s["keyframe_refs"] = []
        refs = []
        for ex in pextras:
            c = copy.deepcopy(ex["material"]); c["id"] = capcut._new_id()
            d["materials"].setdefault(ex["list"], []).append(c); refs.append(c["id"])
        s["extra_material_refs"] = refs
        return s

    main, over, t = [], [], 0
    cards, spans = [], []          # (start_us, dur_us, label) · (start_us, end_us) של הפוטג\'
    for bi, (label, segs, _) in enumerate(blocks):
        if bi or A.lead_card:
            cards.append((t, snap(int(A.card * US)), label))
            main.append(card(t)); t += snap(int(A.card * US))
        blk0 = t
        for a, b in segs:
            main.append(footage(1, a, b, t, True))
            if 2 in cams: over.append(footage(2, a, b, t, False))
            t += snap(int((b - a) * US))
        spans.append((blk0, t, [(a, b) for a, b in segs]))
    t0 = copy.deepcopy(trk_tpl); t0["id"] = capcut._new_id(); t0["segments"] = main; t0["flag"] = 0
    tracks = [t0]
    if over:
        t1 = copy.deepcopy(trk_tpl); t1["id"] = capcut._new_id(); t1["segments"] = over
        t1["flag"] = 2; t1["attribute"] = 0
        tracks.append(t1)

    def clone_extras(seg):
        """כל מקטע מקבל עותקים משלו של חומרי העזר — שיתוף id בין מקטעים מסוכן."""
        refs = []
        for ref in seg.get("extra_material_refs", []):
            for ln, lst in list(d["materials"].items()):
                if not isinstance(lst, list): continue
                src = next((m for m in lst if isinstance(m, dict) and m.get("id") == ref), None)
                if src is None: continue
                c = copy.deepcopy(src); c["id"] = capcut._new_id()
                d["materials"][ln].append(c); refs.append(c["id"]); break
        return refs

    # ה-adjust של הדונור, מקטע לכל בלוק — החוצצים הלבנים נשארים לבנים
    if A.carry_adjust and donor_adjust:
        atpl = copy.deepcopy(donor_adjust[0]); aseg = copy.deepcopy(atpl["segments"][0])
        atpl["segments"] = []
        for a0, a1, _ in spans:
            s2 = copy.deepcopy(aseg); s2["id"] = capcut._new_id()
            s2["extra_material_refs"] = clone_extras(aseg)
            s2["target_timerange"] = {"start": int(a0), "duration": int(a1 - a0)}
            s2["source_timerange"] = {"start": 0, "duration": int(a1 - a0)}
            atpl["segments"].append(s2)
        atpl["id"] = capcut._new_id()
        tracks.append(atpl)

    # רצועות המיקרופון של הדונור, חתוכות לאותם טווחים ומושתקות
    if A.carry_audio:
        for ai, at in enumerate(donor_audio, 1):
            tpl = copy.deepcopy(at); s0 = copy.deepcopy(tpl["segments"][0]); tpl["segments"] = []
            # ההיסט של הדונור מציר-הזמן שלו, פחות ההיסט של המצלמות = דלתא לזמן המקור
            delta = ((s0["source_timerange"]["start"] - s0["target_timerange"]["start"]) / US) - A.offset
            for a0, a1, rngs in spans:
                tt = a0
                for a, b in rngs:
                    s2 = copy.deepcopy(s0); s2["id"] = capcut._new_id()
                    s2["extra_material_refs"] = clone_extras(s0)
                    dur = snap(int((b - a) * US))
                    s2["target_timerange"] = {"start": int(tt), "duration": dur}
                    s2["source_timerange"] = {"start": max(0, snap(int((a + delta) * US))), "duration": dur}
                    s2["volume"] = 0.0
                    s2["common_keyframes"] = []; s2["keyframe_refs"] = []
                    tpl["segments"].append(s2); tt += dur
            tpl["id"] = capcut._new_id()
            tpl["name"] = f"מיקרופון {ai}"; tpl["is_default_name"] = False
            tracks.append(tpl)

    # כותרת על כל חוצץ
    if A.titles and cards:
        if not A.title_donor: sys.exit("✗ --titles דורש --title-donor")
        dn = json.loads((capcut.DRAFTS_DIR / A.title_donor / "draft_info.json").read_text())
        dmats = {m["id"]: m for m in dn["materials"].get("texts", [])}
        best = None
        for tr in dn["tracks"]:
            if tr.get("type") != "text": continue
            for sg in tr["segments"]:
                if sg["material_id"] in dmats and (best is None or
                        sg["target_timerange"]["duration"] > best[0]["target_timerange"]["duration"]):
                    best = (sg, dmats[sg["material_id"]])
        if best is None: sys.exit("✗ לא נמצא מקטע טקסט בדונור הכותרות")
        tseg_tpl, tmat_tpl = copy.deepcopy(best[0]), copy.deepcopy(best[1])
        rgb = tuple(int(A.title_color[i:i+2], 16) / 255 for i in (1, 3, 5))
        tsize, K = A.title_size, 0.00265181     # px = K · size · canvas_height
        if not tsize:
            try:
                from PIL import ImageFont
                fp = json.loads(tmat_tpl["content"])["styles"][0]["font"]["path"]
                ft = ImageFont.truetype(fp, 100)
                H, W = d["canvas_config"]["height"], d["canvas_config"]["width"]
                longest = max((ft.getlength(l) for _, _, lb in cards
                               for l in title_lines(lb)), default=0) / 100
                tsize = round((A.title_fill * W / longest) / (K * H)) if longest else 20
            except Exception as e:
                tsize = 20; print(f"  (התאמת גודל כותרת נכשלה: {e} — נופל ל-20)")
            print(f"  גודל כותרת אוטומטי: {tsize} (≈{K*tsize*d['canvas_config']['height']:.0f}px)")
        tsegs = []
        for st, du, label in cards:
            m = copy.deepcopy(tmat_tpl); m["id"] = capcut._new_id()
            txt = "\n".join(title_lines(label))
            capcut._set_text(m, txt, None)
            m["text_color"] = A.title_color
            m["font_size"] = round(tsize * 1.1, 1)
            pay = json.loads(m["content"])
            for st_ in pay.get("styles", []):
                st_["size"] = tsize
                st_.setdefault("fill", {}).setdefault("content", {}).setdefault("solid", {})["color"] = list(rgb)
                st_["useLetterColor"] = True
                st_.pop("effectStyle", None)
            m["content"] = json.dumps(pay, ensure_ascii=False)
            m["fixed_width"] = -1.0
            d["materials"].setdefault("texts", []).append(m)
            sg = copy.deepcopy(tseg_tpl); sg["id"] = capcut._new_id(); sg["material_id"] = m["id"]
            sg["extra_material_refs"] = []
            sg["target_timerange"] = {"start": int(st), "duration": int(du)}
            sg["clip"]["transform"] = {"x": 0.0, "y": 0.0}
            sg["clip"]["scale"] = {"x": 1.0, "y": 1.0}
            sg["common_keyframes"] = []; sg["keyframe_refs"] = []
            tsegs.append(sg)
        tracks.append({"attribute": 0, "flag": 0, "id": capcut._new_id(),
                       "is_default_name": False, "name": "כותרות חוצץ",
                       "segments": tsegs, "type": "text"})

    d["tracks"] = tracks
    d["duration"] = t
    d["fps"] = A.fps

    (dst_dir / "draft_info.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    meta_id = capcut._new_id()
    mp = dst_dir / "draft_meta_info.json"
    if mp.exists():
        meta = json.loads(mp.read_text()); now = int(time.time() * US)
        meta.update({"draft_id": meta_id, "draft_name": new_name, "draft_fold_path": str(dst_dir),
                     "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": d["duration"]})
        mp.write_text(json.dumps(meta, ensure_ascii=False))
    reels_mod._registry_add(dst_dir, meta_id, d["duration"], A.donor)
except Exception:
    shutil.rmtree(dst_dir, ignore_errors=True)
    raise
print(f"\n✓ «{new_name}» · {len(main)} מקטעים בטראק הראשי · "
      f"{len(over)} בזווית השנייה (alpha 0) · {d['duration']/1e6/60:.2f} דקות")
