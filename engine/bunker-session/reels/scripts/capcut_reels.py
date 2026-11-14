#!/usr/bin/env python3
r"""The four Remotion reels as ONE native CapCut project (Alon 18.10.2026: "בוא ננסה לקחת את אותן 4 גרסאות ולבנות אותן
בקאפקאט עם אותם אפקטים והכל" — the small inaccuracies are easier for him to fix himself in CapCut).

    npx tsx scripts/export_capcut.ts "<session>" && node scripts/render_gfx.mjs "<session>"
    ~/bunker-video-engine/.venv/bin/python scripts/capcut_reels.py "<session>" "<project name>"

Built the way he builds his own reels (tsomet-20 reels-capcut.md):
  • a white divider with the reel's title before every reel (the house "חוצצים"), the camera shutter on its first frame
  • multicam: camera 2 on the main track, camera 1 above it, synced; every segment at opacity 0 or 1 — fixing the
    routing = toggling one segment's opacity. The framing is Remotion's (face at 36 % height, wide 1.0 / tight 1.2);
    the opening settle, every keyword push and the slow push over a reaction are CapCut keyframes (FreeCurveInOut,
    time_offset on the SOURCE clock)
  • split screens as rendered clips on their own track (guest on top, host below, 6 px seam), captions on the seam
  • captions: Heebo ExtraBold (the client's site font), host gold / guest white, black outline, one hot word in the
    accent, his Grow in / Mini Zoom out; graphics (pill, counter) as transparent clips on their own track; the Bunker
    logo under the captions, stepping out for splits and the counter; the end card after the last word with Woosh #2
  • audio: the dialogue master per clip at ≈ −14 LUFS, the spec's music bed, his library SFX (click on real camera
    changes, swoosh on a pill, text appear on the counter)
CapCut must be closed while this writes.
"""
import argparse, copy, json, shutil, statistics, subprocess, sys, time
from pathlib import Path
from PIL import Image

APP = Path.home() / "bunker-video-engine/app"
sys.path.insert(0, str(APP))
import capcut  # noqa: E402
import reels  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent          # the reels project (code + shared assets)
FF, FP = str(Path.home() / "ffmpeg-bin/ffmpeg"), str(Path.home() / "ffmpeg-bin/ffprobe")
US, W, H, SRC_W, SRC_H = 1_000_000, 1080, 1920, 1920, 1080
DONOR = "2.7.26 צומת 20 - אורח L טיזר ורילס"    # a 9:16 project of his: caption style + a camera clip to clone
DONOR_TEXT_TRACK = 6
CARD_S = 3.0
XF = 0.04                                                    # dialogue crossfade overlap at each cut (s)
CAP_PX = 92
FACE_Y = 0.36
HEEBO = str(Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/Heebo-ExtraBold.ttf")
# a spec may name a caption font file from CapCut's font folder (לקוח A 20.10: «שיראה יותר מודרני» → Secular One)
FONTS_DIR = Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts"
COL = {"host": (0.965, 0.769, 0.325), "guest": (1.0, 1.0, 1.0), "hot": (1.0, 0.231, 0.180)}   # #F6C453 · white · #FF3B2E
LIB = Path.home() / "Desktop/חומרים לעריכת וידאו/סאונד/SFX"
SFX = {"shutter": ("Cam shutter.wav", 0.55), "click": ("click.wav", 0.5), "swoosh": ("swoosh quick 1.mp3", 0.35),
       "text": ("Text appear SOUND EFFECT.mp3", 0.35), "woosh": ("Woosh #2.WAV", 0.9)}

us = lambda t: int(round(t * US))
probe_s = lambda p: float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def sel(t, table):
    for w in table:
        if w["from"] - 1e-3 <= t <= w["to"] + 1e-3:
            return w["at"] + (t - w["from"])
    raise ValueError(f"source time {t} is outside the graded windows")


def cam_clip(face, z):
    """Remotion's crop → CapCut (scale, x, y): scale 1 = the 16:9 frame fit inside the width; x/y in half-canvas units"""
    s = (H / SRC_H) * z
    w, h = SRC_W * s, SRC_H * s
    left = min(0.0, max(W - w, W / 2 - face["x"] * w))
    top = min(0.0, max(H - h, H * FACE_Y - face["y"] * h))
    return s / (W / SRC_W), (left + w / 2 - W / 2) / (W / 2), -(top + h / 2 - H / 2) / (H / 2)


def loudness(path):
    r = subprocess.run([FF, "-hide_banner", "-i", str(path), "-af", "loudnorm=I=-14:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(json.loads(r[r.rfind("{"):r.rfind("}") + 1])["input_i"])


def ease_in_out(x):
    return x * x * (3 - 2 * x)


def main():
    global W, H, CAP_PX
    from rpaths import reel_dir, session_paths
    SESSION, RM, PUB, WORK = session_paths(sys.argv)
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("name")
    ap.add_argument("--wide", action="store_true", help="16:9 (1920×1080): full-frame cameras, same routing/captions/sound (תוכן הבונקר לממומן, 24.10.2026)")
    a = ap.parse_args()
    if a.wide:
        W, H, CAP_PX = 1920, 1080, 64                    # captions ≈ 64 px tall on a 1080-high frame (lower third)
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    plan = json.loads((WORK / "capcut/plan.json").read_text())
    # hook → reel start: his "flash" (Glare II, 85× in his projects) + a click on the cut (Alon, לקוח A 20.10.2026)
    PLANS = json.loads((PUB / "plans.json").read_text())
    GLARE = {"type": "transition", "name": "Glare II", "effect_id": "4385603", "resource_id": "6952697917563998722", "third_resource_id": "0",
             "source_platform": 0, "path": str(Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Cache/effect/4385603/aafb556352016d087cddd1939ada20f8"),
             "duration": 266666, "is_overlap": False, "platform": "all", "category_id": "100000", "category_name": "", "request_id": "",
             "is_ai_transition": False, "video_path": "", "task_id": ""}
    spec = json.loads((SESSION / "אפיון.json").read_text(encoding="utf-8"))
    # caption colours from the spec when it sets them (לקוח A 20.10: «מצלמה 1 כתוביות צהובות, מצלמה 2 לבנות»)
    hexrgb = lambda h: tuple(int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    for sp in spec.get("speakers", []):
        if sp.get("color"):
            COL["host" if sp.get("mic") == 1 else "guest"] = hexrgb(sp["color"])
    # no logo in the spec (reels.logo off / no logo file) → no logo track and no end card (the end card IS the logo)
    CAP_FONT = str(FONTS_DIR / spec["reels"]["font_file"]) if spec.get("reels", {}).get("font_file") else HEEBO
    # לקוח A סבב 3 (Alon): «הרבה יותר מדיי הצללה» → caption_shadow false; «אפקט כניסה ויציאה מיותר» → caption_anim
    # false; «פחות תנועה של קי פריימים, יותר עדין» → motion < 1 scales every push/settle and slows its ramps
    RS = spec.get("reels", {})
    CAP_SHADOW, CAP_ANIM, MOTION = RS.get("caption_shadow", True), RS.get("caption_anim", True), float(RS.get("motion", 1.0))
    SLOW = 1.0 + (1.0 - MOTION) * 0.8
    # תוכן הבונקר לממומן (Alon 24.10.2026): «למה הפרדת את הקטע קול הזה מציר הזמן» → reels.xf 0 = the dialogue stays on ONE
    # lane (fades only, no overlap); «הקליקים רובם מיותרים» → reels.clicks false; «הפונט קטן» → reels.cap_px
    XF_ = float(RS.get("xf", XF)); CLICKS = RS.get("clicks", True) is not False
    # אלון+אייל+דולב v6 (25.10.2026, the teaser's rules carried to the reels): the key word keeps its speaker's colour
    # (reels.hot_color "speaker" — red hot words clashed with Dolev's red), captions and logo sit left of the platforms'
    # right-hand buttons (reels.cap_x, px centre) and the logo ends above the bottom UI strip (reels.logo.w / .bottom)
    HOT_SPK = RS.get("hot_color") == "speaker"
    CAP_X = ((float(RS["cap_x"]) - W / 2) / (W / 2)) if RS.get("cap_x") and H > W else 0.0
    if RS.get("cap_px"):
        CAP_PX = float(RS["cap_px"]) * (0.7 if W > H else 1.0)
    LOGO = (PUB / "logo.png").exists() and spec.get("reels", {}).get("logo", {}).get("on", True) is not False
    face = plan["face"]
    # the speaker's face centred in every shot, not one median per camera (לקוח A 20.10: «שהפנים של הדובר יהיו
    # תמיד ממורכזות — הרבה פעמים הן היו ימינה מדיי»): face_track.py samples the face twice a second on the source clock
    FT = json.loads((PUB / "face_track.json").read_text()) if (PUB / "face_track.json").exists() else {}

    # ONE framing per camera for the whole project — never per shot, per run or per split piece (לקוח A 20.10, after
    # per-shot centring: «הזזת את המיקום על ציר X סתם ככה בלי שום סיבה וזה נראה זוועה» · «במסך מפוצל הכנסת תזוזות»).
    # The face is the median over every sample of that camera (face_track.json), so it is centred AND it never moves.
    def _global(c):
        base = face[str(c)]
        pts = [p for p in FT.get(str(c), []) if abs(p[1] - base["x"]) < 0.22 and abs(p[2] - base["y"]) < 0.22]
        return {"x": statistics.median(p[1] for p in pts), "y": statistics.median(p[2] for p in pts)} if pts else base
    FACE_FIXED = {c: _global(c) for c in (1, 2)}
    # a third person (3 speakers on 2 cameras, אלון+אייל+דולב 21.10.2026): face["3"] = {x, y, cam?} — cam 2 = that person sits in
    # camera 2's file (no extra media), otherwise cam3s.mp4; only ever a reaction, on the camera-1 track, opacity 1
    F3 = face.get("3")
    if F3:
        FACE_FIXED[3] = {"x": F3["x"], "y": F3["y"]}

    def face_at(c, a=None, b=None):
        return FACE_FIXED[int(c)]
    table = json.loads((PUB / "selects.json").read_text())

    # ---- donors (cloned from his real drafts) ----
    donor = capcut.load_draft(DONOR)
    didx = capcut._materials_index(donor)
    vmats = {m["id"]: m for m in donor["materials"]["videos"]}
    vseg = next(s for t in donor["tracks"] if t["type"] == "video" for s in t["segments"] if (vmats.get(s["material_id"]) or {}).get("width") == 1920)
    vmat = vmats[vseg["material_id"]]
    vextras = [{"list": didx[r][0], "material": didx[r][1]} for r in vseg["extra_material_refs"] if r in didx]
    vextras = [e for e in vextras if e["list"] not in ("effects", "smart_crops", "transitions")]
    pmat, pseg, pextras = reels._photo_donor()
    amat, aseg, aextras_all = capcut._audio_donor()
    aextras = [e for e in aextras_all if e["list"] not in ("audio_fades", "beats")]
    fade_tpl = next((e for e in aextras_all if e["list"] == "audio_fades"), None)
    style = capcut.extract_style(DONOR, DONOR_TEXT_TRACK)
    ran = capcut.extract_style("אורח F 9x16", 1)                     # his Grow in / Mini Zoom out
    style["extra_materials"] = [e for e in style.get("extra_materials", []) if e["list"] != "material_animations"] + \
        [e for e in ran.get("extra_materials", []) if e["list"] == "material_animations"]

    # ---- a fresh project folder ----
    name = reels._unique_name(a.name)
    dst = capcut.DRAFTS_DIR / name
    reels._copy_draft_folder(capcut.DRAFTS_DIR / DONOR, dst)
    for junk in list(dst.iterdir()):
        if junk.name.startswith(("draft_info.json.", "ccstudio-", "template", "draft_info.ccstudio-backup")) or \
                junk.name in ("subdraft", "matting", "smart_crop", "adjust_mask", "qr_upload"):
            shutil.rmtree(junk) if junk.is_dir() else junk.unlink()
    (dst / "draft_virtual_store.json").write_text(json.dumps({"draft_materials": [], "draft_virtual_store": []}))
    (dst / "key_value.json").write_text("{}")
    draft = json.loads(capcut._draft_file(dst).read_text())
    draft["tracks"] = []
    for k, v in draft["materials"].items():
        if isinstance(v, list):
            draft["materials"][k] = []
    if isinstance(draft.get("keyframes"), dict):
        draft["keyframes"] = {k: [] if isinstance(v, list) else v for k, v in draft["keyframes"].items()}
    draft["canvas_config"] = {"ratio": "16:9" if W > H else "9:16", "width": W, "height": H, "background": None}
    mats = draft["materials"]
    media = dst / "ccstudio-media"
    media.mkdir(exist_ok=True)

    def clone_extras(extras):
        refs = []
        for e in extras:
            c = copy.deepcopy(e["material"]); c["id"] = capcut._new_id()
            mats.setdefault(e["list"], []).append(c); refs.append(c["id"])
        return refs

    vcache = {}

    def vmaterial(path, kind="video"):
        if str(path) in vcache:
            return vcache[str(path)]
        if kind == "photo":
            iw, ih = Image.open(path).size
            m = copy.deepcopy(pmat); m.update({"id": capcut._new_id(), "path": str(path), "width": iw, "height": ih, "material_name": path.name})
        else:
            wh = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True).stdout.strip().split(",")
            m = copy.deepcopy(vmat)
            m.update({"id": capcut._new_id(), "path": str(path), "width": int(wh[0]), "height": int(wh[1]), "type": "video",
                      "duration": us(probe_s(path)), "material_name": path.name, "has_audio": False})
            if "local_material_id" in m:
                m["local_material_id"] = ""
        mats.setdefault("videos", []).append(m); vcache[str(path)] = m
        return m

    def vsegment(mat, start, dur, src_start=0, scale=1.0, tx=0.0, ty=0.0, alpha=1.0, photo=False, keyframes=()):
        # on the 30 fps grid (21.10.2026: a clip edge between two frames lets CapCut show one frame of the layer under it)
        g0, g1 = int(round(round(start * 30 / 1e6) * 1e6 / 30)), int(round(round((start + dur) * 30 / 1e6) * 1e6 / 30))
        src_start, start, dur = max(0, src_start + g0 - start), g0, g1 - g0
        s = copy.deepcopy(pseg if photo else vseg)
        s.update({"id": capcut._new_id(), "material_id": mat["id"], "extra_material_refs": clone_extras(pextras if photo else vextras),
                  "target_timerange": {"start": start, "duration": dur}, "source_timerange": {"start": src_start, "duration": dur},
                  "volume": 0.0, "last_nonzero_volume": 1.0, "speed": 1.0, "enable_lut": False, "common_keyframes": list(keyframes),
                  "keyframe_refs": [], "visible": True, "uniform_scale": {"on": True, "value": 1.0}})
        s["clip"] = {"scale": {"x": scale, "y": scale}, "rotation": 0.0, "transform": {"x": tx, "y": ty},
                     "flip": {"vertical": False, "horizontal": False}, "alpha": alpha}
        return s

    acache = {}

    def asegment(path, start, dur, src_start, vol, fade_out=0.0, fade_in=0.0):
        if str(path) not in acache:
            m = copy.deepcopy(amat)
            m.update({"id": capcut._new_id(), "path": str(path), "name": path.stem, "material_name": path.stem, "duration": us(probe_s(path)), "type": "extract_music"})
            mats.setdefault("audios", []).append(m); acache[str(path)] = m
        s = copy.deepcopy(aseg)
        refs = clone_extras(aextras)
        if (fade_out or fade_in) and fade_tpl:
            f = copy.deepcopy(fade_tpl["material"]); f.update({"id": capcut._new_id(), "fade_in_duration": us(fade_in), "fade_out_duration": us(fade_out)})
            mats.setdefault("audio_fades", []).append(f); refs.append(f["id"])
        s.update({"id": capcut._new_id(), "material_id": acache[str(path)]["id"], "extra_material_refs": refs, "volume": vol,
                  "last_nonzero_volume": vol, "speed": 1.0, "common_keyframes": [], "keyframe_refs": [],
                  "target_timerange": {"start": start, "duration": dur}, "source_timerange": {"start": src_start, "duration": dur}})
        return s

    cap_scale = (CAP_PX / (6.0 * W / 1080)) / float(style["material_template"].get("font_size") or 11)   # CapCut sizes text off the canvas WIDTH

    def text_segment(rows, start, dur, y, who="guest", card=False):
        """rows: [[{text, hot}]] — one colour per speaker, the hot word in the accent (its own style range)"""
        st_ = reels._card_style(style) if card else style
        mat = copy.deepcopy(st_["material_template"]); mat["id"] = capcut._new_id()
        text = "\n".join(" ".join(w["text"] for w in r) for r in rows)
        capcut._set_text(mat, text, None)
        pl = json.loads(mat["content"])
        base = pl["styles"][0]
        spans, i = [], 0
        for ri, r in enumerate(rows):
            for wi, w in enumerate(r):
                spans.append((i, i + len(w["text"]), "hot" if w.get("hot") and not card and not HOT_SPK else who))
                i += len(w["text"]) + (1 if wi < len(r) - 1 else 0)
            i += 1 if ri < len(rows) - 1 else 0
        styles, cur = [], 0
        def add(a_, b_, key):
            if b_ <= a_:
                return
            x = copy.deepcopy(base); x["range"] = [a_, b_]; x["font"] = {"path": CAP_FONT, "id": ""}
            if not card and not CAP_SHADOW:
                x["shadows"] = []; x.pop("shadow", None)
            elif not card and CAP_FONT != HEEBO:                         # modern look: soft shadow instead of the hard offset one
                SH = RS.get("caption_shadow_soft") or {}                 # אלון+אייל+דולב 25.10: «הצל של הכתוביות… לעדן»
                x["shadows"] = [{"diffuse": SH.get("diffuse", 0.35), "angle": -90, "content": {"solid": {"color": [0, 0, 0]}, "render_type": "solid"}, "distance": SH.get("distance", 3), "alpha": SH.get("alpha", 0.55)}]
            c = (0.0, 0.0, 0.0) if card else COL[key]
            x["fill"] = {"content": {"solid": {"color": list(c)}, "render_type": "solid"}}
            styles.append(x)
        for a_, b_, key in spans:
            add(cur, a_, who)          # the space / newline before a word takes the speaker colour
            add(a_, b_, key)
            cur = b_
        add(cur, len(text), who)
        merged = []                                                     # one range per colour run (easier to edit)
        for x in styles:
            if merged and merged[-1]["fill"] == x["fill"] and merged[-1]["range"][1] == x["range"][0]:
                merged[-1]["range"][1] = x["range"][1]
            else:
                merged.append(x)
        pl["styles"] = merged
        mat["content"] = json.dumps(pl, ensure_ascii=False)
        if not card:
            mat["font_path"] = CAP_FONT
            if "line_spacing" in RS:                                    # «יותר מרווח בין השורות» (CapCut default here −0.18)
                mat["line_spacing"] = float(RS["line_spacing"])
            if not CAP_SHADOW:
                mat["has_shadow"] = False
            elif RS.get("caption_shadow_soft"):                          # the material-level shadow (template: alpha 0.9, distance 7) too
                SH = RS["caption_shadow_soft"]
                mat.update({"shadow_alpha": SH.get("alpha", 0.55), "shadow_distance": SH.get("distance", 3) * 1.0, "shadow_smoothing": min(1.0, SH.get("diffuse", 0.35) + 0.3)})
        mats.setdefault("texts", []).append(mat)
        seg = copy.deepcopy(st_["segment_template"])
        ex = st_.get("extra_materials", [])
        if not card and not CAP_ANIM:
            ex = [e for e in ex if e["list"] != "material_animations"]
        seg.update({"id": capcut._new_id(), "material_id": mat["id"], "extra_material_refs": clone_extras(ex),
                    "target_timerange": {"start": start, "duration": dur}})
        ids = set(seg["extra_material_refs"])                         # Mini Zoom out at the caption's own end
        for ma in mats.get("material_animations", []):
            if ma.get("id") not in ids:
                continue
            an = ma.get("animations", [])
            din = next((x.get("duration", 0) for x in an if x.get("type") == "in"), 0)
            dout = next((x.get("duration", 0) for x in an if x.get("type") == "out"), 0)
            k = min(1.0, dur / max(1, din + dout))
            for x in an:
                if x.get("type") == "in":
                    x["duration"] = int(din * k); x["start"] = 0
                elif x.get("type") == "out":
                    x["duration"] = int(dout * k); x["start"] = max(0, dur - int(dout * k))
        sc = 0.85 if card else cap_scale
        seg["clip"] = {"scale": {"x": sc, "y": sc}, "rotation": 0.0, "transform": {"x": 0.0 if card else CAP_X, "y": -(y - H / 2) / (H / 2)},
                       "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
        return seg

    def kfs(seg, knots):
        """knots [(t on the timeline µs, (scale, x, y), ramp_to_next)] → CapCut keyframes (time_offset = SOURCE time)"""
        base = seg["source_timerange"]["start"] - seg["target_timerange"]["start"]
        def lst(i):
            out = []
            for j, (t, V, ramp) in enumerate(knots):
                d_in = t - knots[j - 1][0] if j and knots[j - 1][2] else 0
                d_out = knots[j + 1][0] - t if ramp and j + 1 < len(knots) else 0
                out.append({"id": capcut._new_id(), "curveType": "FreeCurveInOut", "time_offset": int(base + t),
                            "left_control": {"x": -0.42 * d_in, "y": 0.0}, "right_control": {"x": 0.42 * d_out, "y": 0.0},
                            "values": [float(V[i]) if i is not None else 0.0], "string_value": "", "graphID": ""})
            return out
        return [{"id": capcut._new_id(), "material_id": "", "property_type": p, "keyframe_list": lst(i)}
                for p, i in (("KFTypePositionX", 1), ("KFTypePositionY", 2), ("KFTypeScaleX", 0), ("KFTypeRotation", None))]

    # ---- shared media, all inside the draft folder (no CapCut sandbox relink) ----
    print("== media", flush=True)
    # CAPCUT_REUSE=<an earlier build's ccstudio-media>: move its camera + dialogue files in instead of copying 5 GB again
    # (a rebuild on a nearly full disk, לקוח A 20.10.2026) — only when the camera file is the same size as the source
    import os, filecmp
    reuse = Path(os.environ["CAPCUT_REUSE"]) if os.environ.get("CAPCUT_REUSE") else None
    for c in (1, 2):
        old = reuse / f"cam{c}.mp4" if reuse else None
        if old and old.exists() and old.stat().st_size == (PUB / f"cam{c}s.mp4").stat().st_size:
            os.link(old, media / f"cam{c}.mp4")                         # hard link: no space, the earlier project keeps its file
        elif c == 2 and filecmp.cmp(PUB / "cam1s.mp4", PUB / "cam2s.mp4", shallow=False):
            os.link(media / "cam1.mp4", media / "cam2.mp4")              # two speakers on one camera (אלון + אייל, 21.10.2026): one file
        else:
            shutil.copy2(PUB / f"cam{c}s.mp4", media / f"cam{c}.mp4")
    if face.get("3") and face["3"].get("cam", 3) == 3:
        old = reuse / "cam3.mp4" if reuse else None
        if old and old.exists() and old.stat().st_size == (PUB / "cam3s.mp4").stat().st_size:
            os.link(old, media / "cam3.mp4")
        else:
            shutil.copy2(PUB / "cam3s.mp4", media / "cam3.mp4")
    dlg = media / "dialogue.wav"
    # the dialogue is re-made when the master changes (G, 21.10.2026) — reuse it only when asked for explicitly
    if reuse and (reuse / "dialogue.wav").exists() and os.environ.get("CAPCUT_REUSE_DIALOGUE") == "1":
        os.link(reuse / "dialogue.wav", dlg)
    else:
        subprocess.run([FF, "-v", "error", "-y", "-i", str(SESSION / "פרק/דיאלוג.wav"), "-ar", "48000", "-ac", "2", str(dlg)], check=True)
    music = media / "music.mp3"; shutil.copy2(PUB / "music.mp3", music)
    # a different rhythmic track per reel (לקוח A 20.10: «המוזיקה לא טובה — צריך משהו קצבי, שלא תהיה אותה מוזיקה
    # בכל סרטון»): spec reels.music.tracks {"r1": "<file in bunker-brand-music/master>"}, each levelled to music.lufs
    MLIB = Path.home() / "VideoAssets/music"
    MTRACKS = spec.get("reels", {}).get("music", {}).get("tracks", {})
    MLUFS = float(spec.get("reels", {}).get("music", {}).get("lufs", -32.0))
    logo = media / "logo.png"
    if LOGO: shutil.copy2(PUB / "logo.png", logo)
    card_png = media / "divider.png"
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=white:s={W}x{H}", "-frames:v", "1", str(card_png)], check=True)
    outro = media / "outro.mp4"
    if LOGO: shutil.copy2(WORK / "capcut/gfx/outro.mp4", outro)
    sfx = {}
    for k, (f, v) in SFX.items():
        src = LIB / f if (LIB / f).exists() else PUB / "sfx" / f
        if k == "click":
            src = PUB / "sfx/click.wav"
        p = media / src.name; shutil.copy2(src, p); sfx[k] = (p, v)

    def split_clip(sid, i, A, B, shots):
        """guest on top, host below — the same crop as Remotion's split (×1.3, faces at 46 % of each half), 6 px seam"""
        out = media / f"{sid} מסך משולב {i + 1}.mp4"
        parts = []
        for j, s in enumerate([s for s in shots if s["kind"] == "split" and s["at"] < B - 1e-3 and s["end"] > A + 1e-3]):
            x0, x1 = max(A, s["at"]), min(B, s["end"])
            src = s["src"] + (x0 - s["at"])
            def crop(c, fy=0.46):
                z, bw, bh = 1.3, 1080, 957
                sc = (bh / SRC_H) * z; w, h = SRC_W * sc, SRC_H * sc
                fc_ = face_at(c, src, src + (x1 - x0))
                left = min(0.0, max(bw - w, bw / 2 - fc_["x"] * w)); top = min(0.0, max(bh - h, bh * fy - fc_["y"] * h))
                return f"scale={round(w)}:{round(h)},crop={bw}:{bh}:{round(-left)}:{round(-top)}"
            p = media / f".split_{sid}_{i}_{j}.mp4"
            fc = f"[0:v]{crop(2)}[t];[1:v]{crop(1)}[b];[t]pad=1080:963:0:0:black[tp];[tp][b]vstack,fps=30,format=yuv420p[v]"
            nfr = round(x1 * 30) - round(x0 * 30)
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{sel(src, table):.4f}", "-i", str(PUB / "cam2s.mp4"), "-ss", f"{sel(src, table):.4f}",
                            "-i", str(PUB / "cam1s.mp4"), "-filter_complex", fc, "-map", "[v]", "-frames:v", str(nfr),
                            "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-g", "15", "-an", str(p)], check=True)
            parts.append(p)
        lst = media / f".split_{sid}_{i}.txt"; lst.write_text("".join(f"file '{q}'\n" for q in parts))
        subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
        for q in parts + [lst]:
            q.unlink()
        return out

    main_segs, top_segs, split_segs, gfx_segs, logo_segs, caps, titles = [], [], [], [], [], [], []
    dialogue, music_segs, sfx_segs = [], [], []
    T = 0.0
    picks = json.loads((SESSION / "רילס/רילס.json").read_text(encoding="utf-8"))
    layout = []                                              # where each reel sits in the one export (bsession deliver splits it)
    for ri, R in enumerate(plan["reels"]):
        sid, D, OUT = R["id"], R["duration"], (R["outro"] if LOGO else 0.0)
        print(f"== {sid} {R['title']}", flush=True)
        # divider (a real clip on the main track — CapCut ripple-closes gaps there)
        main_segs.append(vsegment(vmaterial(card_png, "photo"), us(T), us(CARD_S), photo=True))
        words = R["title"].split()
        rows = [[{"text": " ".join(words)}]]
        if len(R["title"]) > 18:
            k = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
            rows = [[{"text": " ".join(words[:k])}], [{"text": " ".join(words[k:])}]]
        titles.append(text_segment(rows, us(T + 0.2), us(CARD_S - 0.4), H / 2, card=True))
        T += CARD_S
        T0 = T

        # loudness: this reel's dialogue to ≈ −14 LUFS
        cat = media / f".{sid}_cut.wav"
        cf = "".join(f"[0:a]atrim={c['src']:.4f}:{c['src'] + c['end'] - c['at']:.4f},asetpts=PTS-STARTPTS[a{i}];" for i, c in enumerate(R["clips"]))
        cf += "".join(f"[a{i}]" for i in range(len(R["clips"]))) + f"concat=n={len(R['clips'])}:v=0:a=1[o]"
        subprocess.run([FF, "-v", "error", "-y", "-i", str(dlg), "-filter_complex", cf, "-map", "[o]", str(cat)], check=True)
        vol = min(10 ** ((-14.0 - loudness(cat)) / 20), 6.0)
        cat.unlink()

        # camera shots: cam2 on the main track, cam1 above it (opacity 1 where camera 1 is on screen), framing + keyframes
        pushes = R["pushes"]
        # drift control (Alon 20.10: «בגדול קבוע, אבל יש סיכוי שזה יזוז קצת — צריך בקרה ותמיד למרכז את האדם»): a camera keeps
        # its framing through every jump cut; it is re-centred ONLY where the move cannot be seen — when it comes back on
        # screen after the other camera / a split / the reel start — and only if the face drifted > DRIFT from it
        DRIFT = 0.035
        # no camera flashes (Alon, אלון+אייל+דולב 21.10.2026: «קפיצה של הפריים בצורה לא נקייה וחדה»): a run of one camera
        # shorter than FLASH between two runs of the other camera — or between a split and the other camera — takes the
        # camera around it (r7: 8 frames of camera 2; r9: 7 frames of camera 2 right after the split)
        FLASH = 0.5
        R["shots"] = [dict(s) for s in R["shots"]]
        changed = True
        while changed:
            changed = False
            runs_ = []
            for s in R["shots"]:
                v = None if s["kind"] == "split" else s["cam"]
                if runs_ and runs_[-1][0] == v:
                    runs_[-1][1].append(s)
                else:
                    runs_.append([v, [s]])
            for i, (v, ss) in enumerate(runs_):
                if v is None or ss[-1]["end"] - ss[0]["at"] >= FLASH:
                    continue
                p = runs_[i - 1][0] if i else None
                n = runs_[i + 1][0] if i + 1 < len(runs_) else None
                take = p if p is not None and (p == n or n is None) else (n if p is None and n is not None else None)
                if take is not None and take != v:
                    for s in ss:
                        s["cam"] = take
                    print(f"   flash {v}→{take} at {ss[0]['at']:.2f} ({ss[-1]['end'] - ss[0]['at']:.2f}s)", flush=True)
                    changed = True
                    break
        cur = dict(FACE_FIXED); plan_face, prev_view = [], None
        shots_ = R["shots"]
        for k, s in enumerate(shots_):
            view = None if s["kind"] == "split" else s["cam"]
            if view and view != prev_view:
                run = [shots_[k]]
                for q in shots_[k + 1:]:
                    if q["kind"] == "split" or q["cam"] != view: break
                    run.append(q)
                pts = [p for p in FT.get(str(view), []) for q in run if q["src"] - 0.25 <= p[0] <= q["src"] + (q["end"] - q["at"]) + 0.25
                       and abs(p[1] - FACE_FIXED[view]["x"]) < 0.22 and abs(p[2] - FACE_FIXED[view]["y"]) < 0.22]
                if pts:
                    f = {"x": statistics.median(p[1] for p in pts), "y": statistics.median(p[2] for p in pts)}
                    if abs(f["x"] - cur[view]["x"]) > DRIFT or abs(f["y"] - cur[view]["y"]) > DRIFT:
                        cur[view] = f
            plan_face.append(dict(cur))
            prev_view = view
        for k, s in enumerate(R["shots"]):
            last = k == len(R["shots"]) - 1
            a0, a1 = us(T0 + s["at"]), us(T0 + s["end"])
            dur = a1 - a0
            src = us(sel(s["src"], table))
            z = s["z"]
            for c, lst in ((2, main_segs), (1, top_segs)):
                third = c == 1 and s["cam"] == 3
                visible = s["kind"] != "split" and (s["cam"] == c or third)
                fshot = plan_face[k][3 if third else c]
                sc, x, y = cam_clip(fshot, z)
                mfile = media / (f"cam{F3.get('cam', 3)}.mp4" if third else f"cam{c}.mp4")
                seg = vsegment(vmaterial(mfile), a0, dur, src, sc, x, y, alpha=1.0 if (c == 2 or visible) else 0.0)
                if visible:
                    V = lambda zz, ff=fshot: cam_clip(ff, zz)
                    knots = []
                    if k == 0:                                              # his opening: the frame settles in, 0.83 s
                        knots += [(a0, V(z + 0.22 * MOTION), True), (a0 + us(0.83 * SLOW), V(z), False)]
                    # a cutaway and the shots around it hold still (לקוח A סבב 5: «קי פריים אחרי קי פריים ברצף — לא נעים בעין»)
                    calm = any(x["kind"] == "react" and x["at"] - 1.5 < s["end"] and x["end"] + 1.5 > s["at"] for x in R["shots"])
                    for p in pushes:                                        # eased push landing on the keyword
                        t_land = us(T0 + p)
                        kk = (0.07 if z > 1.1 else 0.14) * MOTION
                        t_in, t_hold, t_out = t_land - us(0.7 * SLOW), t_land + us(1.1), t_land + us(1.1 + 0.9 * SLOW)
                        if s["kind"] != "main" or t_in < a0 - 50_000 or t_in >= a1 or (knots and t_in < knots[-1][0]):
                            continue
                        knots += [(max(a0, t_in), V(z), True), (min(t_land, a1), V(z + kk), False)]
                        if t_hold < a1:
                            knots += [(t_hold, V(z + kk), True), (min(t_out, a1), V(z), False)]
                    if knots and not calm:
                        seg["common_keyframes"] = kfs(seg, knots)
                if c == 2 and s["kind"] != "split" and s["cam"] == 1:
                    pass                                                    # main stays opaque underneath camera 1
                lst.append(seg)
        hook = PLANS.get(sid, {}).get("hook")
        if hook:
            hb = us(T0 + hook)
            for lst in (main_segs, top_segs):
                seg = next((x for x in lst if abs(x["target_timerange"]["start"] + x["target_timerange"]["duration"] - hb) < 40_000), None)
                if seg is not None:
                    m = dict(GLARE, id=capcut._new_id()); mats.setdefault("transitions", []).append(m)
                    seg["extra_material_refs"].append(m["id"])
            sfx_segs.append(asegment(sfx["click"][0], hb - us(0.03), us(min(0.6, probe_s(sfx["click"][0]))), 0, 0.3 * vol))
        # end card after the last word, on the main track
        if LOGO: main_segs.append(vsegment(vmaterial(outro), us(T0 + D), us(OUT)))
        # splits on their own track
        if W > H and R["splits"]:
            raise SystemExit(f"{sid}: מסך משולב ב-16:9 עוד לא נתמך (צד-לצד) — להוריד את ה-split מהתוכנית לגרסה הרחבה")
        for i, (A, B) in enumerate(R["splits"]):
            p = split_clip(sid, i, A, B, R["shots"])
            split_segs.append(vsegment(vmaterial(p), us(T0 + A), min(us(B - A), us(probe_s(p)))))
        # graphics (transparent clips) and their sounds
        for i, g in enumerate(R["pills"]):
            p = media / f"{sid} תווית.mov"; shutil.copy2(WORK / f"capcut/gfx/{sid}_pill{i}.mov", p)
            gfx_segs.append(vsegment(vmaterial(p), us(T0 + g["at"]), min(us(probe_s(p)), us(g["until"] - g["at"] + 0.3))))
            sfx_segs.append(asegment(sfx["swoosh"][0], us(T0 + g["at"]), us(min(1.0, probe_s(sfx["swoosh"][0]))), 0, sfx["swoosh"][1] * vol))
        if R["counter"]:
            g = R["counter"]; p = media / f"{sid} מונה.mov"; shutil.copy2(WORK / f"capcut/gfx/{sid}_counter.mov", p)
            gfx_segs.append(vsegment(vmaterial(p), us(T0 + g["at"]), min(us(probe_s(p)), us(g["until"] - g["at"] + 0.3))))
            sfx_segs.append(asegment(sfx["text"][0], us(T0 + g["at"]), us(min(1.5, probe_s(sfx["text"][0]))), 0, sfx["text"][1] * vol))
        # the logo under the captions, out for splits and the counter
        iw, ih = Image.open(logo).size if LOGO else (1, 1)
        LG = RS.get("logo", {}) if isinstance(RS.get("logo"), dict) else {}
        lw = float(LG.get("w", 300))
        lsc = lw / (iw * min(W / iw, H / ih))
        lcy = (float(LG["bottom"]) - lw * ih / iw / 2) if LG.get("bottom") else 1475 + lw * ih / iw / 2
        cuts = sorted([(max(0, x - 0.1), y + 0.1) for x, y in R["logoHide"]])
        t = 0.0
        for x, y in cuts + [(D, D)]:
            if LOGO and x - t > 0.3:
                logo_segs.append(vsegment(vmaterial(logo, "photo"), us(T0 + t), us(x - t), 0, lsc, CAP_X, -(lcy - H / 2) / (H / 2), photo=True))
            t = max(t, y)
        # captions (on the seam inside a split)
        # a card that runs across a split-screen edge is cut there: on the seam inside the split, low outside it — otherwise
        # it sits on the host's face in the lower half, or on a chin once the split ends (לקוח A 20.10: «טקסט על הפנים?»)
        for c in R["cards"]:
            cuts = sorted({c["from"], c["to"]} | {x for A, B in R["splits"] for x in (A, B) if c["from"] < x < c["to"]})
            pc = [[p_, q_] for p_, q_ in zip(cuts, cuts[1:])]
            if len(pc) > 1:                                         # a sliver under 0.1 s is trimmed, never shown in the wrong place
                pc = [x for x in pc if x[1] - x[0] >= 0.1] or pc
            for p_, q_ in pc:
                y = 960 if any(A - 0.01 <= (p_ + q_) / 2 < B for A, B in R["splits"]) else (0.84 * H if W > H else float(RS.get("cap_y", 1290)))
                caps.append(text_segment(c["rows"], us(T0 + p_), us(q_) - us(p_), y, who=c["who"]))
        # sound
        for c in R["clips"]:
            # a 40 ms overlap each side with 50 ms fades: every cut is a crossfade, the room tone never steps (Alon 21.10.2026:
            # «קאטים חדים ולא נעימים שיוצרים קפיצה באוזן»); overlapping clips go onto a second lane by themselves
            xf = XF_ if c is not R["clips"][0] else 0.0
            xo = XF_ if c is not R["clips"][-1] else 0.0
            dialogue.append(asegment(dlg, us(T0 + c["at"] - xf), us(c["end"] + xo) - us(c["at"] - xf), us(c["src"] - xf), vol,
                                     fade_out=0.05 if xo else 0.02, fade_in=0.05 if xf else 0.015))
        if sid in MTRACKS:
            mfile = media / f"music {sid} - {MTRACKS[sid]}"; shutil.copy2(MLIB / MTRACKS[sid], mfile)
            cutm = media / f".{sid}_music.wav"
            subprocess.run([FF, "-v", "error", "-y", "-i", str(mfile), "-t", f"{D + OUT:.2f}", str(cutm)], check=True)
            mvol = min(10 ** ((MLUFS - loudness(cutm)) / 20), 2.0); cutm.unlink()
            music_segs.append(asegment(mfile, us(T0), us(D + OUT), 0, mvol, fade_out=1.2))
        elif spec.get("reels", {}).get("music", {}).get("on", True) is not False:   # reels.music.on=false → no bed (תוכן ממומן, 24.10.2026)
            music_segs.append(asegment(music, us(T0), us(D + OUT), 0, 0.085 * vol, fade_out=1.2))
        if CLICKS:
            sfx_segs.append(asegment(sfx["shutter"][0], us(T0), us(min(1.0, probe_s(sfx["shutter"][0]))), 0, sfx["shutter"][1] * vol))
        def view(t):
            sh = next((x for x in R["shots"] if x["at"] - 1e-3 <= t < x["end"]), None)
            return None if sh is None else ("split" if sh["kind"] == "split" else sh["cam"])
        keep, last = [], -9.0
        for c in sorted(R["clicks"]):
            if hook and abs(c - hook) < 1.0: continue                  # the hook cut has its own click
            if view(c - 0.05) == view(c + 0.05) or c - last < 4.0: continue   # a framing jump is not a camera switch
            if any(x["kind"] == "react" and (abs(x["at"] - c) < 0.05 or abs(x["end"] - c) < 0.05) for x in R["shots"]): continue  # a cutaway is silent
            keep.append(c); last = c
        for t_ in (keep if CLICKS else []):
            sfx_segs.append(asegment(sfx["click"][0], us(T0 + t_), us(min(0.6, probe_s(sfx["click"][0]))), 0, 0.2 * vol))
        if LOGO: sfx_segs.append(asegment(sfx["woosh"][0], us(T0 + D - 0.32), us(min(1.2, probe_s(sfx["woosh"][0]))), 0, sfx["woosh"][1] * vol))
        layout.append({"id": sid, "dir": reel_dir(picks, sid), "start": round(T0, 6), "end": round(T0 + D + OUT, 6)})
        T = T0 + D + OUT

    def track(kind, segs, nm=""):
        if not segs:
            return
        segs.sort(key=lambda s: s["target_timerange"]["start"])
        lanes = []
        for s in segs:                                                     # overlapping clips go on extra lanes
            a_, b_ = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
            for ln in lanes:
                if ln[-1]["target_timerange"]["start"] + ln[-1]["target_timerange"]["duration"] <= a_:
                    ln.append(s); break
            else:
                lanes.append([s])
        for ln in lanes:
            draft["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": not nm, "name": nm, "segments": ln, "type": kind})

    track("video", main_segs)
    track("video", top_segs, "מצלמה 1 (שקיפות 0/1 = ניתוב)")
    track("video", split_segs, "מסך משולב")
    track("video", gfx_segs, "גרפיקה")
    track("video", logo_segs, "לוגו")
    track("audio", dialogue, "דיבור")
    track("audio", music_segs, "מוזיקה")
    track("audio", sfx_segs, "SFX")
    track("text", titles, "כותרות")
    track("text", caps, "כתוביות")

    (SESSION / "רילס/capcut-layout.json").write_text(json.dumps({"project": name, "reels": layout}, ensure_ascii=False, indent=1), encoding="utf-8")
    total = us(T)
    draft["duration"] = total
    draft["id"] = capcut._new_id()
    capcut._atomic_write(dst, draft)
    subprocess.run([FF, "-v", "error", "-y", "-ss", "4", "-i", str(next(iter(sorted((RM / "out").glob("r1-v*.mp4"))), RM / "out/none.mp4")), "-frames:v", "1", "-vf", "scale=540:960", str(dst / "draft_cover.jpg")], check=False)
    meta_id = capcut._new_id(); meta_path = dst / "draft_meta_info.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        for grp in meta.get("draft_materials") or []:
            if isinstance(grp, dict) and isinstance(grp.get("value"), list):
                grp["value"] = []
        now = int(time.time() * US)
        meta.update({"draft_id": meta_id, "draft_name": name, "draft_fold_path": str(dst), "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": total})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta_id, total, DONOR)
    if RS.get("color_from"):           # «את ה-LUT לא הכנסת» (24.10.2026): the Bunker grade as an adjust layer + LUT, like his projects
        capcut.apply_color(name, capcut.extract_color(RS["color_from"]))   # the camera windows are then graded WITHOUT the LUT baked in
    write_cover(dst)
    size = subprocess.run(["du", "-sh", str(dst)], capture_output=True, text=True).stdout.split()[0]
    print(json.dumps({"name": name, "duration_s": round(T, 1), "tracks": len(draft["tracks"]), "shots": len(top_segs), "captions": len(caps),
                      "splits": len(split_segs), "gfx": len(gfx_segs), "sfx": len(sfx_segs), "size": size}, ensure_ascii=False))


def write_cover(dst):
    """draft_cover.jpg = this project's first camera frame. The folder is copied from DONOR, so without this CapCut's project
    list shows the donor's cover (25.10.2026: «למה הקאברים בקאפקאט הם מסרטונים שונים»)."""
    d = json.loads(capcut._draft_file(dst).read_text())
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    t0 = min(s["target_timerange"]["start"] for t in d["tracks"] if t["type"] == "video" for s in t["segments"]
             if (vids.get(s["material_id"]) or {}).get("type") == "video" and s["clip"]["alpha"] > 0.5) / US + 0.5
    W, H = d["canvas_config"]["width"], d["canvas_config"]["height"]
    tmp = dst / ".cover.jpg"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / "skill/scripts/draft_frame.py"), dst.name, str(tmp), f"{t0:.2f}",
                    "--scale", f"{(405 if W > H else 720) / H:.4f}", "--no-text"], check=True, capture_output=True)
    tmp.replace(dst / "draft_cover.jpg")


if __name__ == "__main__":
    main()
