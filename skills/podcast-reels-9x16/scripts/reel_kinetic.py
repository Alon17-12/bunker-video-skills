# -*- coding: utf-8 -*-
"""Kinetic text stacks for ANY reel project, driven by a plan file — the 0910 look (`kinetic_headlines.py`, v5) without
the 0910 hard-codes. Alon, 0923 r11: «עוד אנימציות טקסט בסגנון של הסרטונים שעשינו ל-whiteboard, מילים שזזות, גדלים
משתנים, פה ושם בצורה עדינה».

    python reel_kinetic.py "<project>" --plan kinetic.json [--zone 930,1200] [--write]

plan.json: {"stacks": [
   {"mode": "roll",    "from": 141.68, "to": 142.98, "lines": [{"style": "s", "text": "זה היה"}, {"style": "b", "text": "עובד ב-2020", "hl": "2020"}]},
   {"mode": "replace", "from": 118.65, "to": 119.38, "lines": [{"style": "b", "text": "מה קורה מנגד?"}]},
   {"mode": "words",   "from": 179.55, "to": 181.98, "rows":  [{"style": "b", "words": [["תשאירו", true], ["פרטים", true]]}, {"style": "s", "words": [["ואנחנו", false], …]}]}
 ]}
`from`/`to` are CAPTION CARD boundaries on the timeline: the stack CONSUMES every caption card inside [from, to) — those
cards are removed and the stack shows their words (the caption contract: every word once, on a card or in a stack).
Word times inside a card are split by character count (no word-level cache needed for cards ≤ 1.5 s). Lines/rows must
spell the consumed cards' words in order (punctuation ignored) — the script refuses anything else, so nothing is lost.
Zone = above the logo (0923: logo top 1216 px → 930–1200), sizes s/m/b = 15/18/25, calibration `px = PIL@60 × size/10`,
wrap 770; entrance/exit cycle per stack (pop · slide-up · zoom-out · Grow · slide-right · Showing Up · drop · tilt /
Fade Out · shrink · rise-out); a swoosh on roll/replace starts and a click on a row's first + highlighted words, on
`sfx text` lanes (clones of the project's own swoosh/click materials). Idempotent: its own `kinetic *` / `sfx text*`
tracks are torn down first — but the consumed caption cards are gone for good, so keep a frozen base.
"""
import argparse, copy, json, os, re, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
from PIL import ImageFont
US = 1_000_000; SP = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--plan", required=True); ap.add_argument("--zone", default="930,1200"); ap.add_argument("--captions", default="כתוביות"); ap.add_argument("--sfx", default="sfx")
ap.add_argument("--swoosh-vol", type=float, default=0.28); ap.add_argument("--click-vol", type=float, default=0.32); ap.add_argument("--hl-color", default="", help="hex of the highlight, e.g. f47d20 (default the 0910 yellow)"); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; FR = US / d.get("fps", 60.0); snap = lambda t: int(round(t / FR) * FR)
nid = lambda: str(uuid.uuid4()).upper(); PLAN = json.load(open(A.plan)); ZONE_TOP, ZONE_BOT = [int(x) for x in A.zone.split(",")]; Y_CENTER = (ZONE_TOP + ZONE_BOT) / 2
AN = json.load(open(os.path.join(SP, "..", "references", "text_anim_donors.json")))
FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/"); LIGHT = FONTS + "Assistant-Regular.ttf"
YELLOW = [0.96, 0.78, 0.06]; WHITE = [1.0, 1.0, 1.0]; SIZES = {"s": 15.0, "m": 18.0, "b": 25.0, "l": 15.0}; WSIZES = {"s": 16.0, "m": 18.0, "b": 25.0}
if A.hl_color: YELLOW = [int(A.hl_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
STOP = {"של", "מה", "את", "אין", "לא", "כל", "עם", "על", "גם", "זה", "אם"}; K = 6.0; WRAP_PX = 770.0; GAP = 8
POP_T, SHIFT_T, TAIL, FADE_IN, FADE_OUT = 0.36, 0.30, 0.35, 0.20, 0.25
ENTRANCES = ["pop", "slide_up", "zoom_out", "grow", "slide_right", "showing", "drop", "tilt"]; EXITS = ["fade", "shrink", "rise_out"]
# ---- tear down a previous run
def drop_tracks(pred):
    gone = [t for t in d["tracks"] if pred(t)]; ids = {s["material_id"] for t in gone for s in t["segments"]}; refs = {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
    for k in list(mats):
        if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and (m.get("id") in ids or m.get("id") in refs))]
    d["tracks"] = [t for t in d["tracks"] if t not in gone]
drop_tracks(lambda t: (t.get("name") or "").startswith(("kinetic", "sfx text")))
tm = {m["id"]: m for m in mats["texts"]}; am = {m["id"]: m for m in mats["audios"]}
cap = next(t for t in d["tracks"] if t["type"] == "text" and t.get("name") == A.captions); cap["segments"].sort(key=lambda s: s["target_timerange"]["start"])
donor_seg = cap["segments"][0]; donor_mat = tm[donor_seg["material_id"]]; BOLD = donor_mat.get("font_path") or FONTS + "bamberger-grunge-bold-fm.ttf"
sfx = next((t for t in d["tracks"] if t.get("name") == A.sfx), None)
def sfx_seg(name):
    if not sfx: return None
    return next((s for s in sfx["segments"] if am.get(s["material_id"], {}).get("name") == name), None)
SW, CK = sfx_seg("ccstudio-sfx-swoosh"), sfx_seg("ccstudio-sfx-click")
def kf(t, v, curve="Line"): return {"id": nid(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": nid(), "material_id": "", "property_type": prop, "keyframe_list": keys}
def y_tr(py): return (960 - py) / 960
def x_tr(px): return (px - 540) / 540
def font_of(style): return LIGHT if style == "l" else BOLD
def width_px(text, style, size): return ImageFont.truetype(font_of(style), 60).getlength(text) * size / 10
def pitch(size, tight=False): return (6.0 if tight else 6.6) * size
def norm(w): return re.sub(r"[.,?!:;\"'«»]+", "", w).strip()
def fit(text, style):
    size = SIZES[style]
    while size > 13 and width_px(text, style, size) > WRAP_PX: size -= 1
    return [(text, size)]
def layout(sizes, tight=False, gap=GAP):
    tot = sum(pitch(s, tight) for s in sizes) + gap * (len(sizes) - 1); yc = min(max(Y_CENTER, ZONE_TOP + tot / 2), ZONE_BOT - tot / 2); top = yc - tot / 2; out = []
    for s in sizes: out.append(top + pitch(s, tight) / 2); top += pitch(s, tight) + gap
    return out
def new_text_material(text, size, hl_ranges, style):
    m = copy.deepcopy(donor_mat); m["id"] = nid(); m["fixed_width"] = -1.0; m["fixed_height"] = -1.0; m["font_size"] = size; m["font_path"] = font_of(style)
    c = json.loads(m["content"]); base = copy.deepcopy(c["styles"][0]); base["size"] = size; base["font"] = {"path": m["font_path"], "id": ""}; base.pop("effectStyle", None)
    if style == "l":
        m["global_alpha"] = 0.62; m["italic_degree"] = 10; m["border_width"] = 0.0; m["has_shadow"] = False; base.pop("strokes", None); base.pop("shadows", None)
    else: m["global_alpha"] = 1.0; m["italic_degree"] = 0
    cuts = sorted({0, len(text)} | {x for a, b in hl_ranges for x in (a, b)}); styles = []
    for r0, r1 in zip(cuts, cuts[1:]):
        st = copy.deepcopy(base); st["range"] = [r0, r1]; st["fill"]["content"]["solid"]["color"] = YELLOW if any(a <= r0 < b for a, b in hl_ranges) else WHITE; styles.append(st)
    c["text"] = text; c["styles"] = styles; m["content"] = json.dumps(c, ensure_ascii=False); m["words"] = {"start_time": [], "end_time": [], "text": []}; mats["texts"].append(m); return m
def anim_material(seg_dur_us, entry_preset, fade_out=True):
    anims = []
    if entry_preset:
        a = copy.deepcopy(AN["anims"][entry_preset]); a["start"] = 0
        if entry_preset == "in:Fade In": a["duration"] = int(FADE_IN * US)
        anims.append(a)
    if fade_out:
        fo = copy.deepcopy(AN["anims"]["out:Fade Out"]); fo["duration"] = int(FADE_OUT * US); fo["start"] = int(seg_dur_us - FADE_OUT * US); anims.append(fo)
    w = copy.deepcopy(AN["wrapper"]); w["id"] = nid(); w["animations"] = anims; mats.setdefault("material_animations", []).append(w); return w["id"]
maxri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"]); tracks_k = []
def free_track(a, L):
    for i, t in enumerate(tracks_k):
        if all(s["target_timerange"]["start"] >= a + L or s["target_timerange"]["start"] + s["target_timerange"]["duration"] <= a for s in t["segments"]): return i
    tracks_k.append({"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": f"kinetic {len(tracks_k)+1}", "segments": [], "type": "text"}); return len(tracks_k) - 1
def place(text, size, hl_ranges, style, seg_start, seg_dur, variant, exit_kind, x0, y_keys, dropped):
    global maxri
    m = new_text_material(text, size, hl_ranges, style); preset = {"grow": "in:Grow", "showing": "in:Showing Up"}.get(variant, "in:Fade In")
    seg = copy.deepcopy(donor_seg); maxri += 1
    seg.update({"id": nid(), "material_id": m["id"], "extra_material_refs": [anim_material(seg_dur, preset)], "render_index": maxri, "target_timerange": {"start": seg_start, "duration": seg_dur}, "source_timerange": {"start": 0, "duration": seg_dur}, "keyframe_refs": []})
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
        elif exit_kind == "rise_out": yl = ys[-1]["values"][0]; ys += [kf(seg_dur - int(0.25 * US), yl, "CurveIn"), kf(seg_dur, yl + 0.05, "CurveIn")]
    for L in (sc, xs, rot, ys):
        if L[-1]["time_offset"] < seg_dur: L.append(kf(seg_dur, L[-1]["values"][0]))
    seg["clip"] = {"scale": {"x": sc[0]["values"][0], "y": sc[0]["values"][0]}, "rotation": rot[0]["values"][0], "transform": {"x": xs[0]["values"][0], "y": ys[0]["values"][0]}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    seg["common_keyframes"] = [group("KFTypeScaleX", sc), group("KFTypeScaleY", [dict(k, id=nid()) for k in sc]), group("KFTypePositionY", ys), group("KFTypePositionX", xs), group("KFTypeRotation", rot)]
    tracks_k[free_track(seg_start, seg_dur)]["segments"].append(seg)
# ---- the words of the consumed cards, timed by character share inside each card
def card_words(f, t):
    segs = [s for s in cap["segments"] if s["target_timerange"]["start"] >= f * US - 20000 and s["target_timerange"]["start"] + s["target_timerange"]["duration"] <= t * US + 20000]
    words = []
    for s in segs:
        toks = json.loads(tm[s["material_id"]]["content"])["text"].replace("\n", " ").split(); a = s["target_timerange"]["start"] / US; L = s["target_timerange"]["duration"] / US; n = sum(len(x) for x in toks) or 1; t0 = a
        for tok in toks: w = L * len(tok) / n; words.append({"text": tok, "start_s": t0, "end_s": t0 + w}); t0 += w
    return segs, words
def match(words, texts):
    """map each line text (a run of words) onto the word list, in order; returns [(i0, i1)] or raises"""
    out = []; pos = 0
    for text in texts:
        toks = [norm(x) for x in text.split()]; n = len(toks)
        while pos + n <= len(words) and [norm(w["text"]) for w in words[pos:pos + n]] != toks: pos += 1
        if pos + n > len(words): raise SystemExit(f"✗ «{text}» not found in the consumed cards: {' '.join(w['text'] for w in words)}")
        out.append((pos, pos + n - 1)); pos += n
    if pos != len(words): raise SystemExit(f"✗ words left uncovered after the last line: {' '.join(w['text'] for w in words[pos:])}")
    return out
consumed = []; report = []; swoosh_at = []; clicks = []; n_lines = 0
for si, st in enumerate(PLAN["stacks"]):
    mode = st["mode"]; segs, words = card_words(st["from"], st["to"]); assert segs, f"stack #{si+1}: no caption cards in {st['from']}–{st['to']}"
    variant = ENTRANCES[si % len(ENTRANCES)]; exit_kind = EXITS[si % len(EXITS)]
    if st.get("entrance"): variant = st["entrance"]
    # window: 0.05 s before the first word; ends 0.02 s before the next caption card (`to`) — a stack's tail never
    # covers the next caption. (The last word ends AT `to` by construction, so the +0.08 floor of 0910 would overlap.)
    w0 = max(0.0, words[0]["start_s"] - 0.05); w1 = st["to"] - 0.02
    if mode == "words":
        flat = [w for row in st["rows"] for w in row["words"]]; idx = match(words, [" ".join(w[0] for w in flat)])
        rows = []; p = 0
        for row in st["rows"]:
            style = row["style"]; size = WSIZES[style]; texts = [norm(w[0]) for w in row["words"]]
            while size > 14 and sum(width_px(t, style, size) for t in texts) + 0.32 * K * size * (len(texts) - 1) > WRAP_PX: size -= 1
            rows.append((style, size, [(words[p + i]["start_s"], words[p + i]["end_s"], t, bool(row["words"][i][1])) for i, t in enumerate(texts)])); p += len(texts)
        while sum(pitch(sz, True) for _, sz, _ in rows) + 4 * (len(rows) - 1) > ZONE_BOT - ZONE_TOP and min(sz for _, sz, _ in rows) > 15: rows = [(s_, sz - 1, ws) for s_, sz, ws in rows]
        cy = layout([size for _, size, _ in rows], tight=True, gap=4)
        for ri, (style, size, ws) in enumerate(rows):
            gap = 0.32 * K * size; widths = [width_px(t, style, size) for _, _, t, _ in ws]; total = sum(widths) + gap * (len(ws) - 1); right = 540 + total / 2
            for wi, ((ws_, we_, text, hl), wpx) in enumerate(zip(ws, widths)):
                cx = right - sum(widths[:wi]) - gap * wi - wpx / 2; t_in = max(w0, ws_ - 0.03); a = snap(t_in * US); L = snap(w1 * US) - a
                place(text, size, [(0, len(text))] if hl else [], style, a, L, "word", exit_kind, x_tr(cx), [kf(0, y_tr(cy[ri]))], False); n_lines += 1
                if hl or (wi == 0 and text not in STOP): clicks.append(t_in)
        report.append(f"  #{si+1} {w0:7.2f}–{w1:7.2f} words   exit={exit_kind:8s} {len(rows)} rows · " + " | ".join(" ".join(t for _, _, t, _ in ws) + f" ({sz:.0f})" for _, sz, ws in rows) + f" · cards {len(segs)}")
    else:
        lines_spec = st["lines"]; idx = match(words, [x["text"] for x in lines_spec]); lines = []
        for (a_, b_), ln in zip(idx, lines_spec):
            (txt, size), = fit(ln["text"], ln["style"]); hl = ln.get("hl"); hlr = [(txt.index(hl), txt.index(hl) + len(hl))] if (hl and hl in txt) else []
            lines.append((words[a_]["start_s"], words[b_]["end_s"], ln["style"], size, hlr, txt))
        max_visible = 1 if mode == "replace" else 9; sizes = [x[3] for x in lines]; t_ev = [max(w0, x[0] - 0.05) for x in lines]
        def fits(seg): return len(seg) <= max_visible and sum(pitch(x) for x in seg) + GAP * (len(seg) - 1) <= ZONE_BOT - ZONE_TOP
        def paginate(lo, hi):
            if fits(sizes[lo:hi]): return [(lo, hi)]
            cands = [k for k in range(lo + 1, hi) if fits(sizes[lo:k])]; pauses = {k: lines[k][0] - lines[k - 1][1] for k in cands}
            k = max(cands, key=lambda k: pauses[k]) if max(pauses.values()) >= 0.35 else max(cands); return [(lo, k)] + paginate(k, hi)
        pages = paginate(0, len(lines)); page_of = {i: p for p, (lo, hi) in enumerate(pages) for i in range(lo, hi)}
        for i, (ws_, we_, style, size, hlr, text) in enumerate(lines):
            p = page_of[i]; lo, hi = pages[p]; t_in = t_ev[i]; t_end = (t_ev[pages[p + 1][0]] + FADE_OUT) if p + 1 < len(pages) else w1
            a = snap(t_in * US); L = snap(t_end * US) - a
            if L < int(0.45 * US): continue
            slot = lambda k: layout(sizes[lo:k + 1])[i - lo]; ys = [kf(0, y_tr(slot(i)))]
            for k in range(i + 1, hi):
                tk = t_ev[k] - t_in
                if tk * US <= ys[-1]["time_offset"] + 1000: continue
                ys += [kf(tk * US, ys[-1]["values"][0], "CurveInOut"), kf((tk + SHIFT_T) * US, y_tr(slot(k)), "CurveInOut")]
            v = variant if style != "b" or variant in ("zoom_out", "tilt", "drop") else "pop"
            place(text, size, hlr, style, a, L, v, exit_kind, 0.0, ys, p + 1 < len(pages)); n_lines += 1
        swoosh_at.append(w0)
        report.append(f"  #{si+1} {w0:7.2f}–{w1:7.2f} {mode:7s} {variant:11s} exit={exit_kind:8s} {len(lines)} lines/{len(pages)} pages · " + " | ".join(f"{t} ({sz:.0f}{'·hl' if h else ''})" for _, _, _, sz, h, t in lines) + f" · cards {len(segs)}")
    consumed += segs
# ---- remove the consumed caption cards (their words now live in the stacks)
gone = {s["id"] for s in consumed}; gone_m = {s["material_id"] for s in consumed}
cap["segments"] = [s for s in cap["segments"] if s["id"] not in gone]; mats["texts"] = [m for m in mats["texts"] if m["id"] not in gone_m]
d["tracks"] += [t for t in tracks_k if t["segments"]]
# ---- sfx: swoosh on roll/replace starts, click on words — clones of the project's own sfx segments, own lanes
def lanes_for(hits, tpl, vol, name):
    if tpl is None or not hits: return 0
    dur = tpl["target_timerange"]["duration"]; lanes = []; global maxri
    for t in sorted(hits):
        s = copy.deepcopy(tpl); s["id"] = nid(); maxri += 1; s["render_index"] = maxri; s["target_timerange"] = {"start": snap(t * US), "duration": dur}; s["volume"] = vol; s["last_nonzero_volume"] = vol
        refs = []
        for r in tpl.get("extra_material_refs", []):
            for k, v in mats.items():
                if isinstance(v, list):
                    src = next((x for x in v if isinstance(x, dict) and x.get("id") == r), None)
                    if src is not None: c = copy.deepcopy(src); c["id"] = nid(); v.append(c); refs.append(c["id"]); break
        s["extra_material_refs"] = refs
        lane = next((L for L in lanes if L[-1]["target_timerange"]["start"] + dur <= s["target_timerange"]["start"]), None)
        if lane is None: lanes.append([]); lane = lanes[-1]
        lane.append(s)
    for i, segs in enumerate(lanes): d["tracks"].append({"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": name if i == 0 else f"{name} {i+1}", "segments": segs, "type": "audio"})
    return len(lanes)
nl_sw = lanes_for(swoosh_at, SW, A.swoosh_vol, "sfx text"); nl_ck = lanes_for(clicks, CK, A.click_vol, "sfx text click")
print("\n".join(report)); print(f"stacks {len(PLAN['stacks'])} | text segments {n_lines} on {len([t for t in tracks_k if t['segments']])} tracks | captions consumed {len(consumed)} → {len(cap['segments'])} left | swooshes {len(swoosh_at)} ({nl_sw} lanes) | clicks {len(clicks)} ({nl_ck} lanes)")
# QA: no caption overlaps a stack window; consumed words all shown
ss = sorted(cap["segments"], key=lambda s: s["target_timerange"]["start"]); ov = sum(1 for a, b in zip(ss, ss[1:]) if b["target_timerange"]["start"] < a["target_timerange"]["start"] + a["target_timerange"]["duration"] - 1)
print(f"caption overlaps {ov} | kinetic tracks {[t['name'] for t in tracks_k]}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
