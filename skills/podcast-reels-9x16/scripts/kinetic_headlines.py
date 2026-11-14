"""0910 round 8 — kinetic stacks v3 (Alon's six notes on v2):
1. the logo runs the whole video (every camera run), stacks live ABOVE it (zone 950–1245px);
2. lines don't all stay: 'roll' keeps only what fits the zone (older lines fade out),
   'replace' shows one line at a time, 'words' builds a sentence word by word;
3. a date is one card in one colour (the split «ב-27 | בספטמבר …» card is merged);
4. more entrance/exit kinds (slide-right, drop, tilt + the cached presets);
5. the translucent style = a clean sans (Assistant) in italic, NO outline / effect, alpha 0.62
   — not the thin brand font;
6. word-by-word rows with a 'click' on each word (cut from 'Text appear SOUND EFFECT').
Calibration (from Alon's CapCut screenshots): canvas px = PIL@60 width × size / 10;
line pitch = 6.6 × size px; CapCut wraps a one-row line at ≈770 px."""
import sys, os, json, copy, shutil, re
DRY = bool(os.environ.get("DRY"))
from pathlib import Path
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
from PIL import ImageFont
SP = Path(__file__).parent; NAME = "0910"; US = 1_000_000
WORDS = json.load(open(os.path.expanduser("~/Movies/reel-captions-work/0910-words.json")))
AN = json.load(open(SP.parent / "references" / "text_anim_donors.json"))
FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/")
BOLD, LIGHT = FONTS + "bamberger-grunge-bold-fm.ttf", FONTS + "Assistant-Regular.ttf"
YELLOW = [0.96, 0.78, 0.06]; WHITE = [1.0, 1.0, 1.0]
SIZES = {"s": 15.0, "m": 18.0, "b": 25.0, "l": 15.0}; WSIZES = {"s": 16.0, "m": 18.0, "b": 25.0}   # word rows: never below 16 (Alon: 14 reads small on a phone)
STOP = {"של", "מה", "את", "אין", "לא", "כל", "עם", "על", "גם"}   # function words never get a click unless highlighted
LIGHT_ALPHA = 0.62; LIGHT_ITALIC = 10; LIGHT_ALPHA = 0.62; LIGHT_ITALIC = 10
K = 6.0                     # canvas px per size unit (measured: «אנשים» size 25 = 278 px wide, «שלישית» 349 px)
WRAP_PX = 770.0             # one-row limit (385 PIL@60 for size 20, converted)
ZONE_TOP, ZONE_BOT, Y_CENTER, GAP = 948, 1245, 1100, 8   # logo top edge is at 1265 px (y −0.40, 158 px tall)
POP_T, SHIFT_T, TAIL, FADE_IN, FADE_OUT = 0.36, 0.30, 0.35, 0.20, 0.25
CTA = [16.44, 44.08, 77.21, 106.30, 134.31, 162.24, 192.94, 218.47]
SFX = os.path.expanduser("~/VideoAssets/סאונד/SFX/")
SWOOSH, SWOOSH_VOL = SFX + "swoosh quick 1.mp3", 0.35
CLICK, CLICK_VOL = str(SP.parent / "references" / "click.wav"), 0.8   # 0.36s cut of "Text appear SOUND EFFECT.mp3" @0.33s
ENTRANCES = ["pop", "slide_up", "zoom_out", "grow", "slide_right", "showing", "drop", "tilt"]
EXITS = ["fade", "shrink", "rise_out"]
# ---- the stacks. mode: roll (keep what fits, older lines leave) | replace (one line at a time) | words (word by word + click)
# roll/replace lines: (word_from, word_to, style, highlight, text)
# words rows: list of rows, row = (style, [(word_from, word_to, text, highlighted?), ...])
STACKS = [
 ("roll",    [(0,1,"l",None,"עורכי וידאו"),(2,4,"s",None,"כמה קורסים דיגיטליים"),(5,6,"b","השנה?","ערכתם השנה?")]),
 ("words",   [("b",[(25,25,"אלפי",True),(26,26,"שקלים",True)]), ("m",[(27,27,"מדי",False),(28,28,"חודש",False)])]),
 ("replace", [(37,39,"l",None,"מנהלות סושיאל ומשווקים"),(40,41,"b","נגמר","הריטיינר נגמר")]),
 ("roll",    [(59,61,"m",None,"ממשיכים להכניס כסף"),(62,65,"s",None,"גם אחרי שהריטיינר ייגמר"),(66,67,"b","כל חודש","כל חודש")]),
 ("roll",    [(75,78,"l",None,"על סטארט-אפ ישראלי"),(79,81,"s",None,"שומעים אחרי האקזיט"),(82,84,"m",None,"הפעם אתם שומעים"),(85,85,"b","לפני","לפני")]),
 ("words",   [("s",[(113,113,"לא",False),(114,114,"משרה",False)]), ("s",[(115,115,"לא",False),(116,116,"השקעה",False)]), ("m",[(117,117,"משהו",False),(118,118,"שלישי",True)])]),
 ("roll",    [(132,135,"l",None,"לסטארט-אפ יש עובדים"),(136,137,"s",None,"ויש משקיעים"),(138,139,"m",None,"אנחנו פותחים"),(140,141,"b","שלישית","קטגוריה שלישית")]),
 ("replace", [(155,157,"b","מוזר","זה נשמע מוזר")]),
 ("replace", [(181,185,"l",None,"אני לא אוהב את המילה"),(186,187,"b","הכנסה פסיבית","הכנסה פסיבית")]),
 ("words",   [("s",[(207,207,"עובדים",False),(208,208,"פעם",False),(209,209,"אחת",False)]), ("s",[(210,210,"הכסף",False),(211,211,"ממשיך",False),(212,212,"להגיע",False)]), ("m",[(213,213,"כל",True),(214,214,"חודש",True)])]),
 ("roll",    [(230,231,"l",None,"עורכים, צלמים"),(232,234,"s",None,"מתי בפעם האחרונה"),(235,236,"b","לחופש","יצאתם לחופש")]),
 ("replace", [(242,243,"l",None,"ככה זה"),(244,245,"m",None,"כשמשלמים לכם"),(246,247,"b","על הזמן","על הזמן")]),
 ("words",   [("m",[(276,276,"זאת",False),(277,277,"לא",True),(278,278,"מודעה",False)]), ("m",[(279,279,"אין",False),(280,280,"מה",False),(281,281,"לקנות",False)])]),
 ("roll",    [(282,283,"m",None,"אין קורס"),(284,286,"b","997","ב-997 שקלים"),(287,289,"m",None,"אלא שעה אחת")]),
 ("roll",    [(329,330,"l",None,"בעוד שנה"),(331,333,"b","שני סוגים","יהיו שני סוגים"),(334,335,"m",None,"של אנשים"),(336,339,"s",None,"שראו את הסרטון הזה")]),
 ("words",   [("m",[(364,364,"ההבדל",True)]), ("s",[(365,365,"שתי",False),(366,366,"דקות",False),(367,367,"של",False),(368,368,"הרשמה",False)]), ("s",[(369,369,"ושעה",False),(370,370,"אחת",False),(371,371,"של",False),(372,372,"צפייה",False)])]),
 ("replace", [(377,379,"b","הראשון","תהיו מהסוג הראשון")]),
]
pid = None if DRY else capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if not DRY and capcut.capcut_running(): raise SystemExit("CapCut running")
D = capcut.DRAFTS_DIR / NAME; d = capcut.load_draft(NAME); mats = d["materials"]
# ---- tear down previous kinetic / sfx tracks (idempotent)
def drop_tracks(pred):
    gone = [t for t in d["tracks"] if pred(t)]
    ids = {s["material_id"] for t in gone for s in t["segments"]}; refs = {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
    mats["texts"] = [m for m in mats["texts"] if m["id"] not in ids]; mats["audios"] = [m for m in mats["audios"] if m["id"] not in ids]
    mats["material_animations"] = [m for m in mats.get("material_animations", []) if m["id"] not in refs]
    d["tracks"] = [t for t in d["tracks"] if t not in gone]
drop_tracks(lambda t: t["type"] == "text" and (t.get("name") or "").startswith("kinetic"))
drop_tracks(lambda t: (t.get("name") or "").startswith(("sfx text", "sfx click")))
tm = {m["id"]: m for m in mats["texts"]}; vm = {m["id"]: m for m in mats["videos"]}
cap_track = next(t for t in d["tracks"] if t.get("name") == "כתוביות"); cap_segs = sorted(cap_track["segments"], key=lambda s: s["target_timerange"]["start"])
donor_seg = cap_segs[0]; donor_mat = tm[donor_seg["material_id"]]
def kf(t, v, curve="Line"):
    return {"id": capcut._new_id(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": capcut._new_id(), "material_id": "", "property_type": prop, "keyframe_list": keys}
def y_tr(py): return (960 - py) / 960
def x_tr(px): return (px - 540) / 540
def font_of(style): return LIGHT if style == "l" else BOLD
def width_px(text, style, size): return ImageFont.truetype(font_of(style), 60).getlength(text) * size / 10
def pitch(size, tight=False): return (6.0 if tight else 6.6) * size   # word rows never shift, so they can sit tighter
def clean(w): return re.sub(r"[.,]+$", "", w)
def fit(text, style):
    size = SIZES[style]
    while size > 13 and width_px(text, style, size) > WRAP_PX: size -= 1
    if width_px(text, style, size) <= WRAP_PX: return [(text, size)]
    toks = text.split(" "); k = max(1, len(toks) // 2)
    return [(" ".join(toks[:k]), size), (" ".join(toks[k:]), size)]
def layout(sizes, tight=False, gap=GAP):
    tot = sum(pitch(s, tight) for s in sizes) + gap * (len(sizes) - 1)
    yc = min(max(Y_CENTER, ZONE_TOP + tot / 2), ZONE_BOT - tot / 2); top = yc - tot / 2; out = []
    for s in sizes: out.append(top + pitch(s, tight) / 2); top += pitch(s, tight) + gap
    return out
def visible_from(sizes, k, max_visible):
    m = k; tot = pitch(sizes[k])
    while m > 0 and (k - m + 1) < max_visible and tot + GAP + pitch(sizes[m - 1]) <= ZONE_BOT - ZONE_TOP: m -= 1; tot += GAP + pitch(sizes[m])
    return m
def new_text_material(text, size, hl_ranges, style):
    m = copy.deepcopy(donor_mat); m["id"] = capcut._new_id(); m["fixed_width"] = -1.0; m["font_size"] = size; m["font_path"] = font_of(style)
    c = json.loads(m["content"]); base = c["styles"][0]; base["size"] = size; base["font"] = {"path": m["font_path"], "id": ""}
    if style == "l":   # the translucent look: clean sans, italic, no outline, no text effect, partial alpha
        m["global_alpha"] = LIGHT_ALPHA; m["italic_degree"] = LIGHT_ITALIC; m["border_width"] = 0.0; m["has_shadow"] = False; base.pop("effectStyle", None)
    else: m["global_alpha"] = 1.0; m["italic_degree"] = 0
    cuts = sorted({0, len(text)} | {x for a, b in hl_ranges for x in (a, b)}); styles = []
    for r0, r1 in zip(cuts, cuts[1:]):
        st = copy.deepcopy(base); st["range"] = [r0, r1]; st["fill"]["content"]["solid"]["color"] = YELLOW if any(a <= r0 < b for a, b in hl_ranges) else WHITE; styles.append(st)
    c["text"] = text; c["styles"] = styles; m["content"] = json.dumps(c, ensure_ascii=False)
    toks = text.split(" "); n = sum(len(t) for t in toks) or 1; st_, en_, tx = [], [], []; t = 0.0
    for i, tok in enumerate(toks):
        st_.append(int(t)); en_.append(int(t + 1000 * len(tok) / n)); tx.append(tok); t += 1000 * len(tok) / n
        if i < len(toks) - 1: st_.append(int(t)); en_.append(int(t)); tx.append(" ")
    m["words"] = {"start_time": st_, "end_time": en_, "text": tx}; mats["texts"].append(m); return m
def anim_material(seg_dur_us, entry_preset, fade_out=True):
    anims = []
    if entry_preset:
        a = copy.deepcopy(AN["anims"][entry_preset]); a["start"] = 0
        if entry_preset == "in:Fade In": a["duration"] = int(FADE_IN * US)
        anims.append(a)
    if fade_out:
        fo = copy.deepcopy(AN["anims"]["out:Fade Out"]); fo["duration"] = int(FADE_OUT * US); fo["start"] = int(seg_dur_us - FADE_OUT * US); anims.append(fo)
    w = copy.deepcopy(AN["wrapper"]); w["id"] = capcut._new_id(); w["animations"] = anims
    mats.setdefault("material_animations", []).append(w); return w["id"]
maxri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
tracks_k = []
def free_track(seg_start, seg_dur):
    """first kinetic track with no segment overlapping [seg_start, seg_start+seg_dur); a new one if none"""
    for i, t in enumerate(tracks_k):
        if all(s["target_timerange"]["start"] >= seg_start + seg_dur or s["target_timerange"]["start"] + s["target_timerange"]["duration"] <= seg_start for s in t["segments"]): return i
    tracks_k.append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": f"kinetic {len(tracks_k)+1}", "segments": [], "type": "text"}); return len(tracks_k) - 1
def place(_unused, text, size, hl_ranges, style, seg_start, seg_dur, variant, exit_kind, x0, y_keys, dropped):
    """one text segment with entrance (variant) and exit (exit_kind, or a plain fade when dropped mid-stack)"""
    global maxri
    m = new_text_material(text, size, hl_ranges, style)
    preset = {"grow": "in:Grow", "showing": "in:Showing Up"}.get(variant, "in:Fade In")
    seg = copy.deepcopy(donor_seg); maxri += 1
    seg.update({"id": capcut._new_id(), "material_id": m["id"], "extra_material_refs": [anim_material(seg_dur, preset)], "render_index": maxri,
                "target_timerange": {"start": seg_start, "duration": seg_dur}, "source_timerange": {"start": 0, "duration": seg_dur}, "keyframe_refs": []})
    ys = list(y_keys); xs = [kf(0, x0)]; rot = [kf(0, 0.0)]
    if variant == "pop": sc = [kf(0, 0.4, "CurveInOut"), kf(0.22 * US, 1.10, "CurveInOut"), kf(POP_T * US, 1.0, "CurveInOut")]
    elif variant == "zoom_out": sc = [kf(0, 1.7, "CurveInOut"), kf(0.35 * US, 1.0, "CurveInOut")]
    elif variant == "tilt": sc = [kf(0, 0.8, "CurveOut"), kf(0.30 * US, 1.0, "CurveOut")]; rot = [kf(0, -8.0, "CurveOut"), kf(0.30 * US, 0.0, "CurveOut")]
    elif variant == "word": sc = [kf(0, 0.5, "CurveOut"), kf(0.14 * US, 1.08, "CurveOut"), kf(0.24 * US, 1.0, "CurveInOut")]
    else: sc = [kf(0, 1.0)]
    if variant == "slide_right": xs = [kf(0, x0 + 0.30, "CurveOut"), kf(0.30 * US, x0, "CurveOut")]
    y0 = ys[0]["values"][0]
    if variant == "slide_up": ys = [kf(0, y0 - 0.06, "CurveInOut"), kf(0.35 * US, y0, "CurveInOut")] + ys[1:]
    if variant == "drop": ys = [kf(0, y0 + 0.06, "CurveOut"), kf(0.24 * US, y0 - 0.008, "CurveInOut"), kf(0.34 * US, y0, "CurveInOut")] + ys[1:]
    if not dropped:
        if exit_kind == "shrink": sc += [kf(seg_dur - int(0.25 * US), 1.0, "CurveInOut"), kf(seg_dur, 0.6, "CurveInOut")]
        elif exit_kind == "rise_out":
            yl = ys[-1]["values"][0]; ys += [kf(seg_dur - int(0.25 * US), yl, "CurveIn"), kf(seg_dur, yl + 0.05, "CurveIn")]
    for L in (sc, xs, rot, ys):
        if L[-1]["time_offset"] < seg_dur: L.append(kf(seg_dur, L[-1]["values"][0]))
    seg["clip"] = {"scale": {"x": sc[0]["values"][0], "y": sc[0]["values"][0]}, "rotation": rot[0]["values"][0], "transform": {"x": xs[0]["values"][0], "y": ys[0]["values"][0]}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    seg["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=capcut._new_id()) for k in sc]), group("KFTypePositionY", ys), group("KFTypePositionX", xs), group("KFTypeRotation", rot)]
    tracks_k[free_track(seg_start, seg_dur)]["segments"].append(seg)
def first_word(spec, mode): return spec[0][1][0][0] if mode == "words" else spec[0][0]
starts = [max(0.0, WORDS[first_word(spec, mode)]["start_s"] - 0.05) for mode, spec in STACKS]
def last_word(spec, mode): return spec[-1][1][-1][1] if mode == "words" else spec[-1][1]
lasts = [last_word(spec, mode) for mode, spec in STACKS]
def clamp_end(si, w1):
    if si + 1 < len(starts): w1 = min(w1, starts[si + 1] - 0.05)
    nxt = lasts[si] + 1
    if nxt < len(WORDS) and WORDS[nxt]["start_s"] - WORDS[lasts[si]]["end_s"] < 3: w1 = min(w1, WORDS[nxt]["start_s"] - 0.02)
    return max(w1, WORDS[lasts[si]]["end_s"] + 0.08)
windows = []; clicks = []; n_lines = 0; shrunk = []; report = []
for si, (mode, spec) in enumerate(STACKS):
    variant = ENTRANCES[si % len(ENTRANCES)]; exit_kind = EXITS[si % len(EXITS)]
    if mode == "words":
        rows = []   # (size, [(t_in, text, hl, width)])
        for style, ws in spec:
            size = WSIZES[style]; texts = [clean(t) for _, _, t, _ in ws]
            while size > 14 and sum(width_px(t, style, size) for t in texts) + 0.32 * K * size * (len(ws) - 1) > WRAP_PX: size -= 1
            rows.append((style, size, [(WORDS[a]["start_s"], WORDS[b]["end_s"], t, h) for (a, b, _, h), t in zip(ws, texts)]))
        w0 = max(0.0, rows[0][2][0][0] - 0.05); w1 = clamp_end(si, rows[-1][2][-1][1] + TAIL); windows.append((w0, w1))
        while sum(pitch(sz, True) for _, sz, _ in rows) + 4 * (len(rows) - 1) > ZONE_BOT - ZONE_TOP and min(sz for _, sz, _ in rows) > 15: rows = [(st, sz - 1, ws) for st, sz, ws in rows]
        cy = layout([size for _, size, _ in rows], tight=True, gap=4); ti = 0
        for ri, (style, size, ws) in enumerate(rows):
            gap = 0.32 * K * size; widths = [width_px(t, style, size) for _, _, t, _ in ws]; total = sum(widths) + gap * (len(ws) - 1); right = 540 + total / 2
            for wi, ((ws_, we_, text, hl), wpx) in enumerate(zip(ws, widths)):
                cx = right - sum(widths[:wi]) - gap * wi - wpx / 2
                t_in = max(w0, ws_ - 0.03); seg_start = int(t_in * US); seg_dur = int(w1 * US) - seg_start
                place(ti % 6, text, size, [(0, len(text))] if hl else [], style, seg_start, seg_dur, "word", exit_kind, x_tr(cx), [kf(0, y_tr(cy[ri]))], False)
                if hl or (wi == 0 and clean(text) not in STOP): clicks.append(t_in)
                ti += 1; n_lines += 1
                if DRY: print(f"      row{ri} {text:8s} size {size:4.1f} cx {cx:6.0f} w {wpx:4.0f} y {cy[ri]:5.0f} t {t_in:6.2f}")
        report.append(f"  #{si+1:2d} {w0:6.1f}–{w1:6.1f}  words     exit={exit_kind:8s} {len(rows)} rows  " + " | ".join(" ".join(t for _, _, t, _ in ws) for _, _, ws in rows))
        continue
    max_visible = 1 if mode == "replace" else 9
    lines = []
    for (a, b, style, hl, text) in spec:
        parts = fit(text, style)
        if parts[0][1] != SIZES[style] or len(parts) > 1: shrunk.append((text, [p[1] for p in parts]))
        for j, (txt, size) in enumerate(parts):
            wa = a + (b - a) * j // len(parts); hlr = [(txt.index(hl), txt.index(hl) + len(hl))] if (hl and hl in txt) else []
            lines.append((WORDS[wa]["start_s"], WORDS[b]["end_s"], style, size, hlr, txt))
    w0 = max(0.0, lines[0][0] - 0.05); w1 = clamp_end(si, lines[-1][1] + TAIL); windows.append((w0, w1))
    sizes = [size for _, _, _, size, _, _ in lines]; t_ev = [max(w0, ws - 0.05) for ws, *_ in lines]
    # pages: the lines are shown in groups that fit the zone together ("צמד 1+2 ואז צמד 3+4"); when a group
    # can't hold every line, the split goes where the speaker pauses longest, never mid-phrase by count
    def fits(seg): return len(seg) <= max_visible and sum(pitch(x) for x in seg) + GAP * (len(seg) - 1) <= ZONE_BOT - ZONE_TOP
    def paginate(lo, hi):
        if fits(sizes[lo:hi]): return [(lo, hi)]
        cands = [k for k in range(lo + 1, hi) if fits(sizes[lo:k])]
        pauses = {k: lines[k][0] - lines[k - 1][1] for k in cands}
        k = max(cands, key=lambda k: pauses[k]) if max(pauses.values()) >= 0.35 else max(cands)   # a real pause wins, else the fullest page
        return [(lo, k)] + paginate(k, hi)
    pages = paginate(0, len(lines)); page_of = {i: p for p, (lo, hi) in enumerate(pages) for i in range(lo, hi)}
    for i, (ws, we, style, size, hlr, text) in enumerate(lines):
        p = page_of[i]; lo, hi = pages[p]
        t_in = t_ev[i]; t_end = (t_ev[pages[p + 1][0]] + FADE_OUT) if p + 1 < len(pages) else w1
        seg_start = int(t_in * US); seg_dur = int(t_end * US) - seg_start
        if seg_dur < int(0.45 * US): continue
        slot = lambda k: layout(sizes[lo:k + 1])[i - lo]
        ys = [kf(0, y_tr(slot(i)))]
        for k in range(i + 1, hi):
            tk = t_ev[k] - t_in
            if tk * US <= ys[-1]["time_offset"] + 1000: continue
            ys += [kf(tk * US, ys[-1]["values"][0], "CurveInOut"), kf((tk + SHIFT_T) * US, y_tr(slot(k)), "CurveInOut")]
        v = variant if style != "b" or variant in ("zoom_out", "tilt", "drop") else "pop"
        place(0, text, size, hlr, style, seg_start, seg_dur, v, exit_kind, 0.0, ys, p + 1 < len(pages)); n_lines += 1
    report.append(f"  #{si+1:2d} {w0:6.1f}–{w1:6.1f}  {mode:7s} {variant:11s} exit={exit_kind:8s} {len(lines)} lines in {len(pages)} pages {[hi-lo for lo,hi in pages]}  " + " | ".join(t for *_, t in lines))
    continue
d["tracks"] += [t for t in tracks_k if t["segments"]]
print("\n".join(report)); print(f"stacks {len(STACKS)} | text segments {n_lines} | clicks {len(clicks)} | shrunk/split {shrunk}")
# ---- captions rebuilt word by word from the fullest backup: every spoken word is either inside a stack's word
# range (shown by the kinetic text) or on exactly one regular card — nothing missing, nothing twice
ranges = [(first_word(spec, mode), last_word(spec, mode)) for mode, spec in STACKS]
def in_stack(i): return any(a <= i <= b for a, b in ranges)
import difflib
BACKUP = D / "draft_info.caption-base-v4.json"     # frozen copy (not in the backup rotation) of the full-coverage caption track
WORDMAP = json.load(open(D / "ccstudio-0910-wordmap.json"))["b134"]   # QA-corrected token per word, from the pre-kinetic backup
bd = json.load(open(BACKUP, encoding="utf-8")); btm = {m["id"]: m for m in bd["materials"]["texts"]}
bt = max([t for t in bd["tracks"] if t["type"] == "text"], key=lambda t: len(t["segments"]))
def norm(w): return w.strip(".,?!:;\"'")
bcards = []   # (word indices, tokens by index, material)
bsegs = sorted(bt["segments"], key=lambda x: x["target_timerange"]["start"])
for ci, seg in enumerate(bsegs):   # align each card's tokens only to the raw words spoken while it is on screen
    a0 = seg["target_timerange"]["start"] / US; b0 = a0 + seg["target_timerange"]["duration"] / US
    toks = json.loads(btm[seg["material_id"]]["content"])["text"].split(" ")
    idx = [i for i, w in enumerate(WORDS) if a0 - 0.08 <= w["start_s"] < b0 - 0.08 and not in_stack(i)]   # base cards are gap-free on word boundaries
    sm = difflib.SequenceMatcher(None, [norm(t) for t in toks], [norm(WORDS[i]["text"]) for i in idx], autojunk=False); tokmap = {}
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i1 - i0 == j1 - j0):
            for k in range(i1 - i0): tokmap[idx[j0 + k]] = toks[i0 + k]
        elif tag == "replace" and j1 > j0:
            tokmap[idx[j0]] = " ".join(toks[i0:i1])
            for k in range(j0 + 1, j1): tokmap[idx[k]] = ""
    if not tokmap: print("  ⚠️ base card not aligned:", round(a0, 2), " ".join(toks)); continue
    lo, hi = min(tokmap), max(tokmap)
    for i in range(lo, hi + 1): tokmap.setdefault(i, WORDMAP.get(str(i), clean(WORDS[i]["text"])))
    bcards.append((list(range(lo, hi + 1)), tokmap, btm[seg["material_id"]]))
owner = {}
for ci, (idx, tokmap, _) in enumerate(bcards):
    for i in idx: owner.setdefault(i, ci)
tokens = {i: (bcards[owner[i]][1][i] if i in owner else WORDMAP.get(str(i), clean(WORDS[i]["text"]))) for i in range(len(WORDS))}
# cards = backup cards minus stack words; uncovered words become their own run, glued to the next card when the phrase continues
runs = []
for ci, (idx, tokmap, mat) in enumerate(bcards):
    keep_idx = [i for i in idx if not in_stack(i)]
    if keep_idx: runs.append((keep_idx, mat if keep_idx == idx else None))
covered = {i for idx, _ in runs for i in idx}
loose = [i for i in range(len(WORDS)) if not in_stack(i) and i not in covered]
for i in loose:
    nxt = next((r for r in runs if r[0][0] == i + 1), None)
    if nxt and not re.search(r"[.?!]$", tokens[i]) and WORDS[i + 1]["start_s"] - WORDS[i]["end_s"] < 0.6: nxt[0].insert(0, i); runs[runs.index(nxt)] = (nxt[0], None)
    else: runs.append(([i], None))
runs.sort(key=lambda r: r[0][0])
# a date split across two backup cards («ב-27» | «בספטמבר …») is joined: the month moves onto the day's card
for r in range(len(runs) - 1):
    a_idx, b_idx = runs[r][0], runs[r + 1][0]
    last_a = next((tokens[i] for i in reversed(a_idx) if tokens[i]), ""); first_b = next((tokens[i] for i in b_idx if tokens[i]), "")
    if re.fullmatch(r"ב-\d+", last_a) and first_b.startswith("בספטמבר") and b_idx[0] == a_idx[-1] + 1:
        a_idx.append(b_idx.pop(0)); runs[r] = (a_idx, None); runs[r + 1] = (b_idx, None)
runs = [r for r in runs if r[0]]
def card_text(idx): return " ".join(t for t in (tokens[i] for i in idx) if t)
# cards shorter than half a second flicker: glue them to a neighbour (never into a date card), and re-cut anything
# that no longer fits one row at the best word; repeat until stable
def span(idx): return WORDS[idx[-1]]["end_s"] - WORDS[idx[0]]["start_s"]
def is_date(idx): return any(re.fullmatch(r"ב-\d+", tokens[i] or "") for i in idx)
CAP_SIZE = 20.0
def width_cap(idx): return ImageFont.truetype(BOLD, 60).getlength(card_text(idx)) * CAP_SIZE / 10
def contiguous(a, b): both = sorted(a + b); return both[-1] - both[0] == len(both) - 1
def merge_short(runs):
    for r, (idx, mat) in enumerate(runs):
        if span(idx) >= 0.5: continue
        for q in (r + 1, r - 1):
            if 0 <= q < len(runs) and not is_date(runs[q][0]) and contiguous(idx, runs[q][0]) and width_cap(sorted(idx + runs[q][0])) <= WRAP_PX:
                runs[min(r, q)] = (sorted(idx + runs[q][0]), None); del runs[max(r, q)]; return True
        q = r + 1
        if q < len(runs) and not is_date(runs[q][0]) and contiguous(idx, runs[q][0]):
            runs[r] = (sorted(idx + runs[q][0]), None); del runs[q]; return True
    return False
def split_wide(runs):
    out = []; changed = False
    for idx, mat in runs:
        if width_cap(idx) <= WRAP_PX or len(idx) < 2: out.append((idx, mat)); continue
        cands = [k for k in range(1, len(idx)) if width_cap(idx[:k]) <= WRAP_PX]
        good = [k for k in cands if span(idx[:k]) >= 0.5 and span(idx[k:]) >= 0.5] or cands or [len(idx) // 2]
        k = min(good, key=lambda k: abs(width_cap(idx[:k]) - width_cap(idx[k:]))); out += [(idx[:k], None), (idx[k:], None)]; changed = True
    return out, changed
# a merged date «ב-27 בספטמבר» must sit on one card: split a run that has the date in the middle/end so the date is whole
fixed = []
for idx, mat in runs:
    parts = [(idx, mat)]
    nb = [i for i in idx if tokens[i]]   # non-blank word positions
    for q in range(len(nb) - 1):
        if re.fullmatch(r"ב-\d+", tokens[nb[q]]) and tokens[nb[q + 1]].startswith("בספטמבר") and (q > 0 or q + 2 < len(nb)):
            pos = idx.index(nb[q]); end = idx.index(nb[q + 1]) + 1
            head, date, tail = idx[:pos], idx[pos:end], idx[end:]
            parts = [(x, None) for x in (head, date, tail) if x]; break
    fixed += parts
runs = fixed
for _ in range(12):   # after the date is whole: glue flickers, re-cut wide rows, until stable
    m = merge_short(runs); runs, w = split_wide(runs)
    if not m and not w: break
# timing: gap-free between neighbours, ending at a stack's start and starting after its end
n_reused = 0; new_segs = []
for r, (idx, mat) in enumerate(runs):
    t0 = WORDS[idx[0]]["start_s"]; t_last = WORDS[idx[-1]]["end_s"]
    for (w0, w1), (ra, rb) in zip(windows, ranges):
        if rb + 1 == idx[0]: t0 = max(t0, w1)
    if r + 1 < len(runs):
        nxt0 = WORDS[runs[r + 1][0][0]]["start_s"]; t1 = nxt0 if nxt0 - t_last <= 1.5 else t_last + 0.4
    else: t1 = t_last + 0.4
    for (w0, w1), (ra, rb) in zip(windows, ranges):
        if idx[-1] + 1 == ra: t1 = min(t1, w0)
    if t1 - t0 < 0.25: t1 = min(t0 + 0.25, WORDS[runs[r + 1][0][0]]["start_s"]) if r + 1 < len(runs) else t0 + 0.25
    text = card_text(idx)
    if mat is not None and json.loads(mat["content"])["text"] == text:
        m = copy.deepcopy(mat); m["id"] = capcut._new_id(); n_reused += 1
    else:
        m = copy.deepcopy(donor_mat); m["id"] = capcut._new_id(); m["fixed_width"] = -1.0; m["font_size"] = CAP_SIZE; m["global_alpha"] = 1.0; m["italic_degree"] = 0
        c = json.loads(m["content"]); base = c["styles"][0]; base["size"] = CAP_SIZE; base["font"] = {"path": BOLD, "id": ""}; base["fill"]["content"]["solid"]["color"] = WHITE
        toks = text.split(" "); styles = []; pos = 0
        for tk in toks:
            st = copy.deepcopy(base); st["range"] = [pos, pos + len(tk) + (1 if tk is not toks[-1] else 0)]
            if re.fullmatch(r"ב-\d+", tk) or tk.startswith("בספטמבר"): st["fill"]["content"]["solid"]["color"] = YELLOW
            if re.search(r"[A-Za-z]", tk): st["font"] = {"path": FONTS + "Heebo-ExtraBold.ttf", "id": ""}; st["size"] = 16.0
            styles.append(st); pos += len(tk) + 1
        merged = [styles[0]]
        for st in styles[1:]:
            p = merged[-1]
            if p["fill"] == st["fill"] and p["font"] == st["font"] and p["size"] == st["size"]: p["range"][1] = st["range"][1]
            else: merged.append(st)
        c["text"] = text; c["styles"] = merged; m["content"] = json.dumps(c, ensure_ascii=False)
        m["words"] = {"start_time": [], "end_time": [], "text": []}
    mats["texts"].append(m)
    seg = copy.deepcopy(donor_seg); maxri += 1
    seg.update({"id": capcut._new_id(), "material_id": m["id"], "extra_material_refs": [], "render_index": maxri, "common_keyframes": [], "keyframe_refs": [],
                "target_timerange": {"start": int(t0 * US), "duration": int(t1 * US) - int(t0 * US)}, "source_timerange": {"start": 0, "duration": int(t1 * US) - int(t0 * US)}})
    seg["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "transform": {"x": 0.0, "y": -0.19}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    new_segs.append(seg)
old_ids = {s_["material_id"] for s_ in cap_track["segments"]}; mats["texts"] = [m for m in mats["texts"] if m["id"] not in old_ids]
cap_track["segments"] = new_segs
# verification: coverage + no duplicates + no card overlapping a stack window
cov = {}
for idx, _ in runs:
    for i in idx: cov[i] = cov.get(i, 0) + 1
gaps = [i for i in range(len(WORDS)) if not in_stack(i) and cov.get(i, 0) == 0]; dups = [i for i in range(len(WORDS)) if in_stack(i) and cov.get(i, 0)] + [i for i, n in cov.items() if n > 1]
clash = [(round(sg["target_timerange"]["start"] / US, 2)) for sg in new_segs for w0, w1 in windows if sg["target_timerange"]["start"] / US < w1 - 0.01 and (sg["target_timerange"]["start"] + sg["target_timerange"]["duration"]) / US > w0 + 0.01]
print(f"captions rebuilt: {len(new_segs)} cards ({n_reused} reused verbatim) | words without caption: {gaps} | shown twice: {dups} | cards inside a stack window: {clash}")
# ---- logo: the whole video — one piece per contiguous camera run (never on the white cards)
lt = next(t for t in d["tracks"] if t.get("name") == "logo"); tpl = lt["segments"][0]; runs = []
for s in d["tracks"][0]["segments"]:
    if vm[s["material_id"]].get("type") == "photo": continue
    a, b = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
    if runs and a - runs[-1][1] <= 1000: runs[-1][1] = b
    else: runs.append([a, b])
lt["segments"] = []
import glob as _glob
FADE_IN_VIDEO = {"id": "6798320778182922760", "type": "in", "start": 0, "duration": 500000, "path": _glob.glob(os.path.expanduser("~/Movies/CapCut/User Data/Cache/effect/6798320778182922760/*"))[0],
                 "platform": "all", "resource_id": "6798320778182922760", "third_resource_id": "6798320778182922760", "source_platform": 1, "name": "Fade In", "category_id": "2037708372",
                 "category_name": "Trending-2", "panel": "video", "material_type": "video", "anim_adjust_params": None, "request_id": ""}
for n_, (a, b) in enumerate(runs):
    if n_ == 0: a = max(a, int(1.5 * US))   # the opener breathes: the logo fades in at 1.5s instead of sitting on frame one
    p = copy.deepcopy(tpl); p["id"] = capcut._new_id(); p["target_timerange"] = {"start": a, "duration": b - a}; p["source_timerange"] = {"start": a, "duration": b - a}; p["common_keyframes"] = []
    p["extra_material_refs"] = [r for r in p["extra_material_refs"] if r not in {w["id"] for w in mats.get("material_animations", [])}]
    if n_ == 0:
        w = copy.deepcopy(AN["wrapper"]); w["id"] = capcut._new_id(); w["animations"] = [copy.deepcopy(FADE_IN_VIDEO)]; mats.setdefault("material_animations", []).append(w); p["extra_material_refs"].append(w["id"])
    lt["segments"].append(p)
print(f"logo pieces {len(runs)} covering {sum(b-a for a,b in runs)/US:.1f}s")
# ---- SFX: swoosh on roll/replace stack starts (not near a CTA pop), click on every word
donor_amat, donor_aseg, donor_aextras = capcut._audio_donor()
def audio_track(name, src, dest_name, hits, vol):
    dest = D / dest_name; shutil.copy(src, dest); adur = capcut._probe_audio_dur_us(dest)
    am = copy.deepcopy(donor_amat); am.update({"id": capcut._new_id(), "path": str(dest), "name": dest_name, "material_name": dest_name, "duration": adur, "type": "extract_music"}); mats["audios"].append(am)
    lanes = []   # hits closer than one sample length go to a second lane (CapCut refuses overlaps on one track)
    for t in sorted(hits):
        seg = copy.deepcopy(donor_aseg); refs = capcut._clone_extras(mats, donor_aextras)
        seg.update({"id": capcut._new_id(), "material_id": am["id"], "extra_material_refs": refs, "volume": vol, "last_nonzero_volume": vol, "speed": 1.0,
                    "target_timerange": {"start": int(t * US), "duration": adur}, "source_timerange": {"start": 0, "duration": adur}, "common_keyframes": [], "keyframe_refs": [], "render_index": 0})
        lane = next((L for L in lanes if L[-1]["target_timerange"]["start"] + adur <= seg["target_timerange"]["start"]), None)
        if lane is None: lanes.append([]); lane = lanes[-1]
        lane.append(seg)
    for i, segs in enumerate(lanes):
        d["tracks"].append({"attribute": 0, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": name if i == 0 else f"{name} {i+1}", "segments": segs, "type": "audio"})
    return adur / US
sw = [w0 for (mode, _), (w0, w1) in zip(STACKS, windows) if mode != "words" and not any(abs(w0 - c) < 1.2 for c in CTA)]
audio_track("sfx text", SWOOSH, "ccstudio-audio-swoosh.mp3", sw, SWOOSH_VOL)
cl = sorted(clicks); cl = [t for i, t in enumerate(cl) if i == 0 or t - cl[i - 1] >= 0.12]
cdur = audio_track("sfx click", CLICK, "ccstudio-audio-click.wav", cl, CLICK_VOL)
print(f"swoosh hits {len(sw)} | clicks {len(cl)} ({cdur:.2f}s each @ {CLICK_VOL})")
if DRY: print("DRY RUN — nothing written")
else: capcut._backup(D); capcut._atomic_write(D, d); print("written")
