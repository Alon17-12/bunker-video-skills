"""0919 «דף תודה» — full edit of the two thank-you videos (16:9, 1920×1080, 60fps).
Stages: routing (flip camera on every jump cut + split long holds) → cinematic drift zoom per shot →
captions (0902 donor, brand highlights, Latin in Heebo) with kinetic title stacks (word-contract) →
name card → music bed → b-roll layer (Seedance clips) + whoosh → logos → SFX. Idempotent: the
main track is rebuilt from a frozen copy of Alon's cut (draft_info.0919-base.json)."""
import json, os, sys, copy, re, shutil, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut, paths, transcribe
from PIL import ImageFont
SP = Path(os.path.expanduser(os.environ.get("WORK", "~/Movies/reel-captions-work/landing-16x9"))); NAME = os.environ.get("DRAFT", "0919"); SRC = os.environ.get("BASE_NAME", "0919"); US = 1_000_000; FR = US / 60; DRY = "--write" not in sys.argv
D = capcut.DRAFTS_DIR / NAME
FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/")
BOLD, HEEBO, LIGHT = FONTS + "bamberger-grunge-bold-fm.ttf", FONTS + "Heebo-ExtraBold.ttf", FONTS + "Assistant-Regular.ttf"
SFX = os.path.expanduser("~/VideoAssets/סאונד/SFX/")
AN = json.load(open(os.path.expanduser("~/.claude/skills/podcast-reels-9x16/references/text_anim_donors.json")))
WHITE, YELLOW, RED = [1.0, 1.0, 1.0], [0.96, 0.78, 0.06], [0.93, 0.27, 0.22]
def snap(us): return int(round(round(us / FR) * FR))
def nid(): return capcut._new_id()
def kf(t, v, curve="Line"):
    return {"id": nid(), "curveType": curve, "time_offset": int(t), "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}, "values": [v], "string_value": "", "graphID": ""}
def group(prop, keys): return {"id": nid(), "material_id": "", "property_type": prop, "keyframe_list": keys}
FREDOKA, FREDOKA_M = FONTS + "Fredoka-Bold.ttf", FONTS + "Fredoka-SemiBold.ttf"
_F60 = {p: ImageFont.truetype(p, 60) for p in (BOLD, HEEBO, LIGHT, FREDOKA, FREDOKA_M)}
def _latin_ok(p):
    f = ImageFont.truetype(p, 40); return f.getlength("W") != f.getlength("￿")
HAS_LATIN = {p: _latin_ok(p) for p in _F60}
CANVAS_K = 1920 / 1080
def width_px(txt, size, font=None):
    """rendered width in canvas px.

    The house figure — 6 px per size unit, i.e. PIL@60 × size/10 — was calibrated on 9:16 projects,
    where the canvas is 1080 px WIDE. CapCut scales text off the canvas width, so on this 1920-wide
    landscape canvas every glyph comes out 1920/1080 = 1.778× bigger, in BOTH axes. Leaving that out
    is what put titles off the right edge and stacked lines on top of each other: the pitch between
    lines was computed 1.78× too tight. Measure through here and through line_h(), never raw.
    """
    return _F60[font or BOLD].getlength(txt) * size / 10 * CANVAS_K
def line_h(size): return 6 * size * CANVAS_K          # one em, in canvas px
WRAP_PX = 0.82 * 1920

# ---------------------------------------------------------------- words
W = json.load(open(SP / "0919_words_fixed.json"))
def core(t): return t.strip(".,?!:;")
def merge_tokens(ws, seq, new):
    out, i = [], 0
    while i < len(ws):
        if [core(w["text"]) for w in ws[i:i+len(seq)]] == [core(x) for x in seq]:
            tail = ws[i+len(seq)-1]["text"][len(seq[-1]):]
            out.append({"text": new + tail, "start_s": ws[i]["start_s"], "end_s": ws[i+len(seq)-1]["end_s"]}); i += len(seq)
        else: out.append(ws[i]); i += 1
    return out
for v in W["videos"]:
    v["words"] = merge_tokens(v["words"], ["ל", "-40", "%"], "ל-40%")
    v["words"] = merge_tokens(v["words"], ["1", ",600"], "1,600")
import difflib
fuzzy_hits = []
def find_phrase(ws, phrase):
    """exact token match first; otherwise the best window by token similarity (a re-transcription drifts by a
    word or two — «או אולי» vs «אולי» — and an anchor that dies on that is an anchor that dies every rerun)"""
    seq = [core(x) for x in phrase.split()]; toks = [core(w["text"]) for w in ws]
    for i in range(len(ws) - len(seq) + 1):
        if toks[i:i + len(seq)] == seq: return i, i + len(seq) - 1
    best = (0.0, None)
    for n in (len(seq) - 1, len(seq), len(seq) + 1):
        if n < 1: continue
        for i in range(len(ws) - n + 1):
            r = difflib.SequenceMatcher(None, toks[i:i + n], seq).ratio()
            if r > best[0]: best = (r, (i, i + n - 1))
    if best[0] >= 0.66:
        fuzzy_hits.append((phrase, " ".join(toks[best[1][0]:best[1][1] + 1]), round(best[0], 2))); return best[1]
    raise SystemExit(f"phrase not found: {phrase!r} (best {best[0]:.2f})")

# Title sizes are chosen so the two videos render the SAME cap height (Fredoka's cap is 0.70 em,
# bamberger's 0.60), which is what makes them read as one family across the cut.
SIZES = {"s": 7.0, "m": 8.9, "b": 14.0}                    # bunker / bamberger — the headline reads at ~2.5× the caption
CAP_SIZE, CAP_Y = 10.0, -0.6667                            # 0902 donor
CAP_MAX_W = 700 * CANVAS_K                                 # unchanged behaviour, now stated in real px
# ---------------------------------------------------------------- per-video spec
VIDEOS = [
 {"key": "wb", "vi": 0, "hl": YELLOW, "music": "ccstudio-bed-wb.mp3", "music_vol": 0.063, "logo": "ccstudio-logo-whiteboard.png", "logo_scale": 0.11,
  "font": FREDOKA, "cap_font": FREDOKA_M, "title_sizes": {"s": 6.0, "m": 7.6, "b": 12.0}, "cap_size": 9.0,
  "name": ["אלון גבאי", "מנכ״ל WhiteBoard"],
  "keywords": ["WhiteBoard", "Education", "AI", "הזדמנות", "10%", "ל-40%", "200", "400", "40", "160", "1,600", "פסיבי", "win", "זכוכית", "משנת", "חיים", "אתגר", "שותפים", "מסלול", "כסף", "אחוז", "אחוזים"],
  "titles": [
   ("WhiteBoard זו פלטפורמה חדשה ליצירת קורסים וקהילות דיגיטליות מבוססות AI", [("s", "פלטפורמה חדשה ליצירת", WHITE), ("b", "קורסים וקהילות", None), ("m", "מבוססות AI", WHITE)]),
   ("איך את או אתה עושים מזה כסף?", [("m", "איך עושים", WHITE), ("b", "מזה כסף?", None)]),
   ("מנהלות סושיאל, עורכי וידאו, קמפיינרים או אולי אפילו מפיקי קורסים", [("m", "מנהלות סושיאל", WHITE), ("m", "עורכי וידאו", WHITE), ("b", "מפיקי קורסים", None)]),
   ("האחוזים נעים בין 10% ל-40% מאורך חיי הלקוח", [("s", "האחוזים", WHITE), ("b", "10% – 40%", None), ("m", "מאורך חיי הלקוח", WHITE)]),
   ("תקבלו 40 שקל בחודש באופן פסיבי", [("s", "מנוי 400 ₪ · 10%", WHITE), ("b", "40 ₪ בחודש", None), ("m", "באופן פסיבי", WHITE)]),
   ("תשיגו 160 שקל באופן פסיבי כל חודש", [("s", "ב-40%", WHITE), ("b", "160 ₪ בחודש", None), ("m", "באופן פסיבי", WHITE)]),
   ("תביאו 10 כאלה, זה כבר 1,600", [("m", "10 לקוחות", WHITE), ("b", "1,600 ₪ בחודש", None)]),
   ("ואין פה שום תקרת זכוכית", [("b", "אין תקרת זכוכית", None)]),
   ("שכולה בנויה על win win", [("b", "win win", None)]),
   ("זאת הפעם הראשונה שאתגר כזה קורה בישראל", [("s", "אתגר כזה", WHITE), ("b", "לראשונה", None), ("m", "בישראל", WHITE)]),
   ("אז תרשמו ביומנים, ואנחנו נתראה", [("m", "נתראה בלייב", WHITE), ("b", "תרשמו ביומנים", None)]),
  ],
  # One storyboard, one world: a bright workspace in the brand palette, the real WhiteBoard UI on
  # every screen, and BOARDi living INSIDE the screen — building the hub, ordering a playlist,
  # working for a student who is watching him, filling in a lecturer's course, presenting to a team.
  # This replaces the screen-grabs with a mascot popped on top; the mascot now acts inside the story.
  # Every clip shows what the sentence SAYS (Alon, v2: "חלק מהבירולס לא מדויקים למלל הנאמר").
  "broll": [("פלטפורמה חדשה ליצירת קורסים", "ccstudio-boardi-1.mp4", 4.6),   # BOARDi builds the hub, cards fly in
            ("בנויים בתור פלייליסט", "ccstudio-boardi-2.mp4", 4.6),          # BOARDi drags a lesson into the playlist
            ("בשיעורי זום מוקלטים", "ccstudio-broll-wb2.mp4", 4.0),          # recorded lessons on a screen — the words
            ("למרצה לבנות את הקורס", "ccstudio-boardi-4.mp4", 4.6),          # the lecturer's course builds itself
            ("כלי AI שעוזרים לו", "ccstudio-boardi-3.mp4", 4.6),             # a student watches BOARDi highlight and summarise
            ("עובדים עם עסקים וארגונים", "ccstudio-boardi-5.mp4", 4.6),      # a team, BOARDi presenting the board
            ("כל זה אפשרי בתוך WhiteBoard", "ccstudio-frame-sys-builder.mp4", 4.0),  # the feature list → the real builder, framed
            ("תעבירו אותם ל-WhiteBoard", "ccstudio-frame-sys-hub.mp4", 4.0),  # the real hub, framed
            ("ואתם תקבלו אחוז מסוים", "ccstudio-broll-wb42.mp4", 4.0),        # the dashboard shown to a client
            ("תקבלו 40 שקל בחודש", "ccstudio-broll-wb5.mp4", 4.0),
            ("מי יגיע, איך יגיע", "ccstudio-broll-wb6.mp4", 4.0)],
  # Chapter cards: the reference creators announce sections (Martell's dark card, Giang's paper card,
  # ניסטור's «#2»). One card 1.5 s before each section's opening title, over the speech, with a whoosh.
  "chapters": [("WhiteBoard זו פלטפורמה", "01", "מה זה WhiteBoard"), ("איך את או אתה עושים", "02", "איך עושים מזה כסף?"),
               ("האחוזים נעים בין", "03", "המספרים"), ("זאת הפעם הראשונה שאתגר", "04", "האתגר")],
  "mascot": []},
 {"key": "bk", "vi": 1, "hl": RED, "music": "ccstudio-bed-bk.mp3", "music_vol": 0.053, "logo": "ccstudio-logo-bunker.png", "logo_scale": 0.13,
  "font": BOLD, "cap_font": BOLD, "title_sizes": SIZES, "cap_size": CAP_SIZE,
  "name": ["אלון גבאי", "הבעלים של הבונקר"],
  "keywords": ["הבונקר", "בבונקר", "פודקאסט", "סשן", "היכרות", "באותו", "יום", "היום", "רילס", "ניתוב", "מצלמות", "טלפרומפטר", "VSL-ים", "לינק", "הלינק", "רמות", "השרון", "ה-15", "לופט", "AI", "מקצה", "לקצה", "קליק", "מוכן", "לפרסום", "אוטומטית", "ברנד"],
  "titles": [
   ("להקים פודקאסט, ליצור תוכן ולייצר פרסונל ברנד חזק יותר", [("m", "להקים פודקאסט", WHITE), ("m", "ליצור תוכן", WHITE), ("b", "פרסונל ברנד חזק", None)]),
   ("זה פשוט להגיע לסשן היכרות", [("s", "השלב הראשון", WHITE), ("b", "סשן היכרות", None)]),
   ("שממנה יוצא פרק ארוך מוכן לפרסום שמגיע לכם באותו יום", [("m", "שעה באולפן", WHITE), ("b", "פרק מוכן לפרסום", None), ("m", "באותו יום", WHITE)]),
   ("כולל ניתוב מצלמות, חיתוך של ההתחלה והסיום", [("m", "ניתוב מצלמות", WHITE), ("b", "חיתוך התחלה וסיום", None)]),
   ("יצירה של רילס, ראיון איתי שאני אראיין אתכם, חבילות שונות", [("m", "רילס", WHITE), ("m", "ראיון איתי", WHITE), ("b", "חבילות שונות", None)]),
   ("לקמפיינים עם טלפרומפטר, תרצו לצלם VSL-ים, תרצו לצלם אולי קורסים דיגיטליים", [("m", "קמפיינים עם טלפרומפטר", WHITE), ("m", "VSL-ים", WHITE), ("b", "קורסים דיגיטליים", None)]),
   ("סשן היכרות של שעה לא מחייבת", [("b", "שעה אחת", None), ("m", "לא מחייבת", WHITE)]),
   ("אולפן בלב רמות השרון, בקומה ה-15 עם לופט, עם נוף מטורף", [("s", "לב רמות השרון", WHITE), ("b", "קומה 15 · לופט", None), ("m", "נוף מטורף", WHITE)]),
   ("הפרק עובר עריכה אוטומטית על ידי המערכת שלנו", [("b", "עריכה אוטומטית", None), ("m", "החומרים באותו היום", WHITE)]),
   ("חבילה שמותאמת ככפפה ליד", [("b", "חבילה ככפפה ליד", None)]),
   ("באינטימיות, בדאגה לפרטים הקטנים, באווירה שיש כאן", [("m", "אינטימיות", WHITE), ("m", "דאגה לפרטים הקטנים", WHITE), ("b", "אווירה", None)]),
   ("איזשהו קורס עזר, דיבור למצלמה", [("b", "קורס דיבור למצלמה", None)]),
   ("באסטרטגיה שיווקית, אורגנית או ממומנת", [("b", "אסטרטגיה שיווקית", None), ("m", "אורגנית · ממומנת", WHITE)]),
   ("באמת מעטפת מקצה לקצה", [("b", "מעטפת מקצה לקצה", None)]),
   ("יש לכם את הלינק לתיאום", [("b", "הלינק לתיאום", None), ("m", "כאן בדף", WHITE)]),
  ],
  "broll": [("להקים פודקאסט, ליצור", "ccstudio-broll-bk1.mp4", 4.5), ("לשעה באולפן שממנה", "ccstudio-broll-bk2.mp4", 4.5), ("לקמפיינים עם טלפרומפטר", "ccstudio-broll-bk3.mp4", 4.5),
            # no clip on "קומה 15 עם לופט": the loft is a real place we have no reference of, and the
            # generated one was visibly a different studio. The title carries the line instead.
            ("תקבלו קפה, סודה", "ccstudio-broll-bk5.mp4", 4.5), ("יגיעו אליכם באותו היום", "ccstudio-broll-bk6.mp4", 4.5), ("נוכל לבנות דרך ארוכה", "ccstudio-broll-bk7.mp4", 4.5)],
  "chapters": [("להקים פודקאסט, ליצור", "01", "מה עושים בבונקר"), ("זה פשוט להגיע לסשן", "02", "סשן היכרות"),
               ("אולפן בלב רמות השרון", "03", "האולפן"), ("באמת מעטפת מקצה לקצה", "04", "מעטפת מקצה לקצה")],
  "mascot": []},
]
# Titles live in the one column that is free in BOTH camera framings: the speaker's head sits at
# x 700–1160, so everything right of 1176 is background. The block is right-aligned against a fixed
# edge, vertically centred on a fixed line, and carries a fixed accent rule — so eleven different
# titles land in exactly the same place instead of drifting. A gradient scrim rides underneath so a
# white line stays readable when the shot under it is a white screen-grab of the system.
TITLE_RIGHT_PX, TITLE_LEFT_PX, TITLE_MID_PX = 1786, 1176, 372
TITLE_BOX_W = TITLE_RIGHT_PX - TITLE_LEFT_PX
LINE_GAP, RULE_X_PX = 0.30, 1814                            # air between lines (ems); the accent rule's centre
MAX_HOLD, CAM2_MIN, CAM2_MAX, MIN_SHOT = 7.0, 2.5, 6.0, 1.2          # no reference creator holds one framing past ~7 s

# ---------------------------------------------------------------- draft
pid = capcut._capcut_pid()
if not DRY and pid and f"{D}/" in capcut._capcut_open_files(pid): raise SystemExit("0919 is open in CapCut — not writing")
d = capcut.load_draft(NAME); mats = d["materials"]
BASE = D / f"draft_info.{SRC}-base.json"     # the frozen ORIGINAL cut travels with a duplicate under the source name
if not BASE.exists(): shutil.copy(D / "draft_info.json", BASE); print("frozen base saved")
base = json.load(open(BASE))
def byid_of(m):
    return {x["id"]: (k, x) for k, v in m.items() if isinstance(v, list) for x in v if isinstance(x, dict) and "id" in x}
OURS = ("broll", "boardi", "logo", "כתוביות", "name card", "music bed", "sfx", "chapter", "title plate")
# ---- tear down our tracks (idempotent) and restore Alon's main track from the base
gone = [t for t in d["tracks"] if (t.get("name") or "").startswith(OURS) or (t.get("name") or "").startswith("title")]
ids = {s["material_id"] for t in gone for s in t["segments"]} | {r for t in gone for s in t["segments"] for r in s.get("extra_material_refs", [])}
main_ids = {s["material_id"] for s in d["tracks"][0]["segments"]} | {r for s in d["tracks"][0]["segments"] for r in s.get("extra_material_refs", [])}
base_refs = {r for s in base["tracks"][0]["segments"] for r in [s["material_id"]] + s.get("extra_material_refs", [])}
for k in list(mats):
    if isinstance(mats[k], list): mats[k] = [m for m in mats[k] if not (isinstance(m, dict) and (m.get("id") in ids or (m.get("id") in main_ids and m.get("id") not in base_refs)))]
bb = byid_of(base["materials"])
for r in base_refs:
    if r in bb and not any(isinstance(m, dict) and m.get("id") == r for m in mats.get(bb[r][0], [])): mats.setdefault(bb[r][0], []).append(copy.deepcopy(bb[r][1]))
d["tracks"] = [t for t in d["tracks"] if t not in gone]
d["tracks"][0]["segments"] = copy.deepcopy(base["tracks"][0]["segments"])
byid = byid_of(mats); vids = {m["id"]: m for m in mats["videos"]}; drafts = {x["id"]: x for x in mats["drafts"]}
def extras_of(seg): return [{"list": byid[r][0], "material": byid[r][1]} for r in seg["extra_material_refs"] if r in byid]
maxri = max(s.get("render_index", 0) for t in d["tracks"] for s in t["segments"])
def next_ri():
    global maxri; maxri += 1; return maxri
def new_track(name, typ): return {"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False, "name": name, "segments": [], "type": typ}

# ---------------------------------------------------------------- routing
main = d["tracks"][0]; pieces = sorted([s for s in main["segments"] if vids[s["material_id"]].get("multi_camera_info")], key=lambda s: s["target_timerange"]["start"])
def cams_of(dref):
    nd = drafts[dref]["draft"]; nv = {x["id"]: x for x in nd["materials"]["videos"]}; cam = {}
    for t in nd["tracks"]:
        if t["type"] != "video": continue
        x = t["segments"][0]; n = int(re.findall(r"\d", os.path.splitext(os.path.basename(nv[x["material_id"]]["path"]))[0])[-1]); cam[n] = t["id"]
    return cam
new_main = [s for s in main["segments"] if s not in pieces]; route_report = []
for V in VIDEOS:
    ws = W["videos"][V["vi"]]["words"]; sent_starts = [ws[0]["start_s"]] + [ws[i+1]["start_s"] for i in range(len(ws)-1) if ws[i]["text"][-1:] in ".?!"]
    gaps = [(ws[i]["end_s"], ws[i+1]["start_s"] - ws[i]["end_s"]) for i in range(len(ws)-1)]
    A, B = W["videos"][V["vi"]]["A"] / US, W["videos"][V["vi"]]["B"] / US
    vp = [s for s in pieces if A - 0.01 <= s["target_timerange"]["start"] / US < B]; V["pieces"] = vp
    dref = next(r for r in vp[0]["extra_material_refs"] if r in drafts); cam = cams_of(dref); V["cam"] = cam; V["dref"] = dref
    def best_cut(t_ideal, lo, hi):
        """sentence start nearest t_ideal inside (lo, hi), else the longest word gap there"""
        cands = [t for t in sent_starts if lo <= t <= hi]
        if cands: return min(cands, key=lambda t: abs(t - t_ideal))
        g = [(t + gp / 2, gp) for t, gp in gaps if lo <= t <= hi]
        return max(g, key=lambda x: x[1])[0] if g else None            # the longest pause in the window (a word boundary at worst)
    shots = []   # (a, b, cam_forced_or_None, jump_at_start)
    for p in vp:
        a, b = p["target_timerange"]["start"] / US, (p["target_timerange"]["start"] + p["target_timerange"]["duration"]) / US
        forced = 2 if vids[p["material_id"]]["multi_camera_info"]["cur_camera_track_id"] == cam[2] else None
        cuts = [a]
        while b - cuts[-1] > MAX_HOLD:
            c = best_cut(cuts[-1] + MAX_HOLD * 0.85, cuts[-1] + 3.5, cuts[-1] + MAX_HOLD)
            if c is None or b - c < 2.5: break
            cuts.append(c)
        cuts.append(b)
        for i in range(len(cuts) - 1): shots.append([cuts[i], cuts[i+1], forced if i == 0 else None, i == 0])   # his camera-2 choice holds the piece's first shot; internal cuts are free
    # camera walk: a jump cut always flips the camera (it hides the cut); an internal cut inside a long hold
    # opens a short camera-2 beat (2.5–5.5 s) and returns to camera 1; camera-2 holds are bounded; tiny shots keep the camera
    cur = 1; run = 0.0; plan = []
    for i, (a, b, forced, jump) in enumerate(shots):
        L = b - a
        if forced: c = 2
        elif i == 0: c = 1
        elif L < MIN_SHOT: c = cur
        elif cur == 1 and not jump and run < 5.0 and run + L <= MAX_HOLD: c = 1   # camera 1 keeps the floor a while — but never past MAX_HOLD in one framing
        else: c = 2 if cur == 1 else 1
        if c == 2 and L > CAM2_MAX:
            cut = best_cut(a + 3.8, a + CAM2_MIN, a + 5.5)
            if cut and b - cut >= 1.5: plan.append([a, cut, 2]); plan.append([cut, b, 1]); cur = 1; run = b - cut; continue
            c = 1
        if c == 2 and L < CAM2_MIN and not forced: c = 1
        if c == cur and not jump and run + L > MAX_HOLD and L >= MIN_SHOT: c = 2 if cur == 1 else 1   # the other side of the same rule
        run = run + L if c == cur else L
        plan.append([a, b, c]); cur = c
    merged = []
    for a, b, c in plan:
        if merged and merged[-1][2] == c and abs(merged[-1][1] - a) < 1e-6 and not any(abs(p["target_timerange"]["start"] / US - a) < 1e-6 for p in vp): merged[-1][1] = b
        else: merged.append([a, b, c])
    V["plan"] = merged
    durs = [b - a for a, b, c in merged]; c1 = sum(b - a for a, b, c in merged if c == 1)
    route_report.append(f"{V['key']}: {len(vp)} pieces → {len(merged)} shots | min {min(durs):.2f} med {sorted(durs)[len(durs)//2]:.1f} max {max(durs):.1f}s | cam1 {100*c1/(B-A):.0f}%")
    # rebuild the pieces: one segment per shot, source continuity from the piece it lies in
    for a, b, c in merged:
        p = next(p for p in vp if p["target_timerange"]["start"] / US - 1e-6 <= a < (p["target_timerange"]["start"] + p["target_timerange"]["duration"]) / US)
        a_us = p["target_timerange"]["start"] if abs(p["target_timerange"]["start"] / US - a) < 1e-6 else snap(a * US)
        pend = p["target_timerange"]["start"] + p["target_timerange"]["duration"]; b_us = pend if abs(pend / US - b) < 1e-6 else snap(b * US)
        m = copy.deepcopy(vids[p["material_id"]]); m["id"] = nid(); m["multi_camera_info"] = dict(m["multi_camera_info"], id=nid(), cur_camera_track_id=cam[c]); mats["videos"].append(m)
        s = copy.deepcopy(p); s["id"] = nid(); s["material_id"] = m["id"]
        s["extra_material_refs"] = [V["dref"]] + capcut._clone_extras(mats, [e for e in extras_of(p) if e["material"]["id"] != V["dref"]])
        s["target_timerange"] = {"start": a_us, "duration": b_us - a_us}; s["source_timerange"] = {"start": p["source_timerange"]["start"] + (a_us - p["target_timerange"]["start"]), "duration": b_us - a_us}
        s["common_keyframes"] = []; s["keyframe_refs"] = []; s["_cam"] = c; new_main.append(s)
old_piece_ids = {p["material_id"] for p in pieces}
mats["videos"] = [m for m in mats["videos"] if m["id"] not in old_piece_ids]
new_main.sort(key=lambda s: s["target_timerange"]["start"]); main["segments"] = new_main
for p, q in zip(new_main, new_main[1:]): assert p["target_timerange"]["start"] + p["target_timerange"]["duration"] == q["target_timerange"]["start"], (p["target_timerange"], q["target_timerange"])
print("\n".join(route_report))

# ---------------------------------------------------------------- motion: punches, not drift
# Measured off the six reference creators (creator-styles.md): a talking head holds STILL and snaps
# between two framings on sentence starts — the same "punches, not drift" note Alon gave on 0910.
# Each shot sits on one of two levels; on a sentence start ≥ PUNCH_GAP after the last move, ≥ 1.5 s
# after the cut and ≥ 1.0 s before it, the shot snaps to the other level over PUNCH_S with CurveInOut.
# Even shots alternate 1.00 ↔ 1.06, odd shots 1.03 ↔ 1.09 (fill = 1.0 on 16:9, ceiling ×1.09), so a cut
# always lands with a framing change and the punches alternate in / out. The first shot of each video
# keeps the intro zoom-out (×1.05 → target over 1.0 s). The face is held in place through every move.
FACE = {"wb": {1: (0.484, 0.404), 2: (0.464, 0.359)}, "bk": {1: (0.501, 0.420), 2: (0.392, 0.388)}}   # composited face centre (x from left, y from top)
PUNCH_S, PUNCH_GAP, LEVELS = 0.35, 2.5, ((1.00, 1.08), (1.04, 1.12))     # v2.1: he "barely saw" 6 % — 8 % snaps, closer
k = 0; n_punch = 0
for V in VIDEOS:
    ws = W["videos"][V["vi"]]["words"]
    sent_starts = [ws[i + 1]["start_s"] for i in range(len(ws) - 1) if ws[i]["text"][-1:] in ".?!"]
    gaps_v = [(ws[i]["end_s"], ws[i + 1]["start_s"] - ws[i]["end_s"]) for i in range(len(ws) - 1)]
    shots = [s for s in new_main if any(s["target_timerange"]["start"] / US >= a - 1e-6 and s["target_timerange"]["start"] / US < b for a, b, c in V["plan"])]
    for si, s in enumerate(shots):
        L = s["source_timerange"]["duration"] / US; src0 = s["source_timerange"]["start"]; cam_n = s.pop("_cam")
        t0 = s["target_timerange"]["start"] / US
        lo, hi = LEVELS[k % 2]; lvl = 0
        keys = []                                                   # (t_rel_s, scale, curve)
        if si == 0:
            keys += [(0.0, lo * 1.05, "CurveInOut"), (1.0, lo, "CurveInOut")]; last = 1.0
        else:
            keys += [(0.0, lo, "CurveInOut")]; last = 0.0
        beats = sorted(sent_starts)
        if L >= 5.5 and not any(t0 + 1.2 <= t <= t0 + L - 1.0 - PUNCH_S for t in beats):
            inside = [(t + gp / 2, gp) for t, gp in gaps_v if t0 + 1.2 <= t <= t0 + L - 1.0 - PUNCH_S]
            if inside: beats.append(max(inside, key=lambda x: x[1])[0])          # no sentence start in a long hold → the longest pause
        for t in sorted(beats):
            r = t - t0
            if r < max(1.2, last + PUNCH_GAP) or r > L - 1.0 - PUNCH_S: continue
            cur = (lo, hi)[lvl]; lvl ^= 1; nxt = (lo, hi)[lvl]
            keys += [(r, cur, "CurveInOut"), (r + PUNCH_S, nxt, "CurveInOut")]; last = r + PUNCH_S; n_punch += 1
        keys.append((L, (lo, hi)[lvl], "CurveInOut"))
        fx, fy = FACE[V["key"]][cam_n]
        def pos(sc): return (-(sc - 1) * (2 * fx - 1), -(sc - 1) * (1 - 2 * fy))
        s["common_keyframes"] = [group("KFTypeScaleX", [kf(src0 + int(t * US), v, c) for t, v, c in keys]), group("KFTypeScaleY", [kf(src0 + int(t * US), v, c) for t, v, c in keys]),
                                 group("KFTypePositionX", [kf(src0 + int(t * US), pos(v)[0], c) for t, v, c in keys]), group("KFTypePositionY", [kf(src0 + int(t * US), pos(v)[1], c) for t, v, c in keys])]
        s0 = keys[0][1]; s["clip"]["scale"] = {"x": s0, "y": s0}; s["clip"]["transform"] = {"x": pos(s0)[0], "y": pos(s0)[1]}; k += 1
print(f"motion: {k} shots, {n_punch} punches on sentence starts (levels {LEVELS}, {PUNCH_S}s snaps, ≥{PUNCH_GAP}s apart)")


# ---------------------------------------------------------------- layered motion helper
# Every overlay moves in space, not just on/off: enters with a slide + scale (+ a degree or two of
# rotation for the cards), drifts while it holds, leaves with a punch. Keyframes on the segment's own
# clock (photos/text start at 0; b-roll adds its source offset), CurveInOut everywhere.
def motion(seg, dur_us, base, entry=None, t_in=0.4, drift=None, exit_=None, t_out=0.3, off_us=0, fade=None):
    """base=(x, y, s, rot); entry/exit_/drift = (dx, dy, ds, drot) deltas applied to base; fade=(up_s, down_s) adds an alpha ramp"""
    x, y, sc, rot = base; keys = []
    def at(t, d): return (t, x + d[0], y + d[1], sc * (1 + d[2]), rot + d[3])
    z = (0, 0, 0, 0)
    if entry: keys += [at(0, entry), at(int(t_in * US), z)]
    else: keys.append(at(0, z))
    end_body = int(dur_us - (t_out * US if exit_ else 0))
    keys.append(at(end_body, drift or z))
    if exit_: keys.append(at(dur_us, tuple(a + b for a, b in zip(drift or z, exit_))))
    seg["common_keyframes"] = [group("KFTypePositionX", [kf(off_us + t, vx, "CurveInOut") for t, vx, vy, vs, vr in keys]),
                               group("KFTypePositionY", [kf(off_us + t, vy, "CurveInOut") for t, vx, vy, vs, vr in keys]),
                               group("KFTypeScaleX", [kf(off_us + t, vs, "CurveInOut") for t, vx, vy, vs, vr in keys]),
                               group("KFTypeScaleY", [kf(off_us + t, vs, "CurveInOut") for t, vx, vy, vs, vr in keys]),
                               group("KFTypeRotation", [kf(off_us + t, vr, "CurveInOut") for t, vx, vy, vs, vr in keys])]
    if fade:
        up, down = fade
        seg["common_keyframes"].append(group("KFTypeAlpha", [kf(off_us, 0.0), kf(off_us + int(up * US), 1.0, "CurveInOut"), kf(off_us + int(dur_us - down * US), 1.0, "CurveInOut"), kf(off_us + dur_us, 0.0)]))
        seg["clip"]["alpha"] = 1.0
    t, vx, vy, vs, vr = keys[0]; seg["clip"]["transform"] = {"x": vx, "y": vy}; seg["clip"]["scale"] = {"x": vs, "y": vs}; seg["clip"]["rotation"] = vr
    return seg

# ---------------------------------------------------------------- text helpers (0902 donor)
d2 = capcut.load_draft("0902"); t2 = d2["tracks"][1]; tm2 = {m["id"]: m for m in d2["materials"]["texts"]}
DSEG = t2["segments"][len(t2["segments"]) // 2]; DMAT = tm2[DSEG["material_id"]]
def style(rng, color, size, font=BOLD, effect=True):
    st = {"fill": {"content": {"solid": {"color": color}, "render_type": "solid"}}, "range": list(rng), "useLetterColor": True, "size": size, "font": {"path": font, "id": ""}}
    if effect: st["effectStyle"] = copy.deepcopy(json.loads(DMAT["content"])["styles"][0]["effectStyle"])
    return st
def text_material(text, styles, words=None, size=CAP_SIZE, alpha=1.0, italic=0):
    m = copy.deepcopy(DMAT); m["id"] = nid(); m["font_size"] = size; m["global_alpha"] = alpha
    m["content"] = json.dumps({"styles": styles, "text": text}, ensure_ascii=False); m["base_content"] = ""; m["recognize_text"] = text
    m["words"] = {"start_time": [], "end_time": [], "text": []}
    if words: capcut._set_text(m, text, words); m["content"] = json.dumps({"styles": styles, "text": text}, ensure_ascii=False)
    if italic: m["italic_degree"] = italic
    mats["texts"].append(m); return m
def text_segment(m, start_us, dur_us, x=0.0, y=CAP_Y, scale=1.0, anims=None):
    s = copy.deepcopy(DSEG); s["id"] = nid(); s["material_id"] = m["id"]; s["extra_material_refs"] = []
    s["target_timerange"] = {"start": int(start_us), "duration": int(dur_us)}; s["render_index"] = next_ri(); s["common_keyframes"] = []
    s["clip"] = {"scale": {"x": scale, "y": scale}, "rotation": 0.0, "transform": {"x": x, "y": y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    if anims:
        w = copy.deepcopy(AN["wrapper"]); w["id"] = nid(); w["animations"] = []
        for key, dur in anims:
            a = copy.deepcopy(AN["anims"][key]); a["duration"] = int(dur * US); w["animations"].append(a)
        mats.setdefault("material_animations", []).append(w); s["extra_material_refs"].append(w["id"])
    return s
def styled_ranges(text, hl_color, keywords, size=CAP_SIZE, font=None):
    """brand colour on keywords; a font that lacks Latin glyphs hands Latin runs to Heebo"""
    font = font or BOLD; latin_ok = HAS_LATIN[font]
    styles = []; pos = 0
    for tok in re.split(r"(\s+)", text):
        if not tok: continue
        a, b = pos, pos + len(tok); pos = b
        if tok.isspace(): styles.append(style((a, b), WHITE, size, font)); continue
        latin = bool(re.search(r"[A-Za-z]", tok)); color = hl_color if core(tok) in keywords or tok in keywords else WHITE
        if latin and not latin_ok:
            for mm in re.finditer(r"[A-Za-z][A-Za-z\-]*[A-Za-z]|[A-Za-z]|[^A-Za-z]+", tok):
                la = bool(re.match(r"[A-Za-z]", mm.group())); styles.append(style((a + mm.start(), a + mm.end()), color, size * 0.8 if la else size, HEEBO if la else font))
        else: styles.append(style((a, b), color, size, font))
    # merge adjacent identical
    out = []
    for st in styles:
        if out and {k: v for k, v in out[-1].items() if k != "range"} == {k: v for k, v in st.items() if k != "range"} and out[-1]["range"][1] == st["range"][0]: out[-1]["range"][1] = st["range"][1]
        else: out.append(st)
    return out

# ---------------------------------------------------------------- titles (kinetic stacks) + captions with the word contract
cap_track = new_track("כתוביות", "text"); title_tracks = []; sfx = new_track("sfx", "audio"); name_track = new_track("name card 1", "text"); name_track2 = new_track("name card 2", "text")
def audio_material(path, name):
    m = {"id": nid(), "type": "extract_music", "name": name, "duration": capcut._probe_audio_dur_us(Path(path)), "path": path, "category_name": "", "wave_points": [], "music_id": "", "app_id": 0,
         "text_id": "", "tone_type": "", "source_platform": 0, "video_id": "", "effect_id": "", "resource_id": "", "third_resource_id": "", "category_id": "", "intensifies_path": "", "formula_id": "",
         "check_flag": 1, "team_id": "", "local_material_id": "", "tone_speaker": "", "mock_tone_speaker": "", "tone_effect_id": "", "tone_effect_name": "", "tone_platform": "", "cloned_model_type": "",
         "tone_category_id": "", "tone_category_name": "", "tone_second_category_id": "", "tone_second_category_name": "", "is_ai_clone_tone": False, "ai_music_track_names": "", "is_ugc_music": False,
         "ugc_music_id": "", "query": "", "search_id": "", "music_source": "", "video_source": "", "text_source": "", "musicPlatform": 0, "is_text_edit_overdub": False, "voice_clone_task_id": "",
         "source_from": "", "beat_point_list": [], "raw_material_id": ""}
    mats["audios"].append(m); return m
AUD_DONOR = None
def audio_segment(m, start_us, dur_us, vol, fade_in=0, fade_out=0, src=0):
    s = {"id": nid(), "source_timerange": {"start": int(src), "duration": int(dur_us)}, "target_timerange": {"start": int(start_us), "duration": int(dur_us)}, "render_timerange": {"start": 0, "duration": 0},
         "desc": "", "state": 0, "speed": 1.0, "is_loop": False, "is_tone_modify": False, "reverse": False, "intensifies_audio": False, "cartoon": False, "volume": vol, "last_nonzero_volume": vol, "clip": None,
         "uniform_scale": None, "material_id": m["id"], "extra_material_refs": [], "render_index": 0, "keyframe_refs": [], "enable_lut": False, "enable_adjust": False, "enable_hsl": False, "visible": True,
         "group_id": "", "enable_color_curves": True, "enable_hsl_curves": True, "track_render_index": 0, "hdr_settings": None, "enable_color_wheels": True, "track_attribute": 0, "is_placeholder": False,
         "template_id": "", "enable_smart_color_adjust": False, "template_scene": "default", "common_keyframes": [], "caption_info": None,
         "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0}, "enable_color_match_adjust": False, "enable_color_correct_adjust": False,
         "enable_adjust_mask": False, "raw_segment_id": "", "lyric_keyframes": None, "enable_video_mask": True, "digital_human_template_group_id": "", "color_correct_alg_result": "", "source": "segmentsourcenormal",
         "enable_mask_stroke": False, "enable_mask_shadow": False}
    sp = {"id": nid(), "type": "speed", "mode": 0, "speed": 1.0, "curve_speed": None}; mats["speeds"].append(sp)
    fd = {"id": nid(), "type": "audio_fade", "fade_type": 0, "fade_in_duration": int(fade_in * US), "fade_out_duration": int(fade_out * US)}; mats.setdefault("audio_fades", []).append(fd)
    sc = {"id": nid(), "type": "none", "audio_channel_mapping": 0, "is_config_open": False}; mats["sound_channel_mappings"].append(sc)
    vs = {"id": nid(), "type": "vocal_separation", "choice": 0, "removed_sounds": [], "time_range": None, "production_path": "", "final_algorithm": "", "enter_from": ""}; mats["vocal_separations"].append(vs)
    s["extra_material_refs"] = [sp["id"], fd["id"], sc["id"], vs["id"]]; return s
SWOOSH = audio_material(SFX + "swoosh quick 1.mp3", "swoosh quick 1"); WHOOSH = audio_material(SFX + "Woosh #2.WAV", "Woosh #2")
def add_sfx(m, t0, dur_s, vol):
    """One SFX track (Alon, v2.1: 20 tracks is a mess). A whoosh that would start inside the previous
    one trims the previous tail — a 30 ms shorter tail is inaudible, a third audio track is not."""
    st = int(t0 * US); dur = min(m["duration"], int(dur_s * US))
    for prev in sfx["segments"]:
        p0 = prev["target_timerange"]["start"]; p1 = p0 + prev["target_timerange"]["duration"]
        if p0 < st < p1:
            if st - p0 < int(0.25 * US): return None                        # two hits inside a quarter second: keep the first
            prev["target_timerange"]["duration"] = prev["source_timerange"]["duration"] = st - p0
        elif st <= p0 < st + dur: dur = p0 - st
    if dur < int(0.2 * US): return None
    seg = audio_segment(m, st, dur, vol); sfx["segments"].append(seg); return seg
def pop_keys(src0, dur_us):
    return [kf(src0, 0.6, "CurveInOut"), kf(src0 + int(0.22 * US), 1.06, "CurveInOut"), kf(src0 + int(0.36 * US), 1.0, "CurveInOut"), kf(src0 + dur_us, 1.0)]
qa = {"words_without_caption": [], "shown_twice": []}
too_wide, boxes, title_spans, name_spans = [], [], [], []
# ---- chapter slots first: a card sits ON the pause that opens its section, never mid-sentence.
# v2.1 slid every card 1.85 s ahead of its title to dodge the title window, so all eight landed inside
# the previous sentence and read as unrelated (Alon: "הכיתוב של שם הפרק לא רלוונטי"). The title that
# follows moves out of the card's way instead (below), not the other way round.
CH_DUR, CH_PAUSE = 2.8, 0.35
chapter_slots, chapter_plan = [], []
for V in VIDEOS:
    ws = W["videos"][V["vi"]]["words"]; A = W["videos"][V["vi"]]["A"] / US
    prev_end = A + 4.6                                                    # the first card may start as the name card fades (A + 5.6)
    for phrase, num, text in V.get("chapters", []):
        i0, i1 = find_phrase(ws, phrase); t_anchor = ws[i0]["start_s"]
        gaps = [(ws[j]["end_s"], ws[j + 1]["start_s"]) for j in range(max(0, i0 - 40), i0)]
        gaps = [(a, b) for a, b in gaps if b - a >= CH_PAUSE and t_anchor - 7.0 <= a <= t_anchor and a >= prev_end + 1.0]
        g = max(gaps) if gaps else None                                       # the last pause BEFORE the opening sentence — never after it
        t0 = (g[0] + 0.05) if g else max(prev_end + 1.0, t_anchor - CH_DUR - 0.2)
        chapter_slots.append((t0, t0 + CH_DUR)); chapter_plan.append((V, num, text, t0)); prev_end = t0 + CH_DUR
        print(f"  chapter {V['key']}-{num} {text!r}: anchor {t_anchor:.2f}, pause {'%.2f–%.2f' % g if g else 'none'} → card {t0:.2f}–{t0 + CH_DUR:.2f}")
for V in VIDEOS:
    ws = W["videos"][V["vi"]]["words"]; covered = [None] * len(ws)
    # ---- titles
    windows = []
    for phrase, lines in V["titles"]:
        i0, i1 = find_phrase(ws, phrase); t0 = ws[i0]["start_s"] - 0.10; t1 = ws[i1]["end_s"] + 0.40
        if i1 + 1 < len(ws): t1 = min(t1, ws[i1 + 1]["start_s"] - 0.12)          # the tail ends before the next word (and before the next window)
        for c0, c1 in chapter_slots:                                             # a title never shares the screen with a chapter card:
            if t0 < c1 + 0.4 and t1 > c0:                                        # it waits for the card to leave, then holds ≥2.6 s
                if t0 < c0 and c0 - 0.1 - t0 >= 2.0: t1 = c0 - 0.1
                else: t0 = c1 + 0.4; t1 = max(t1, t0 + 2.6)
        windows.append([t0, t1, i0, i1, lines])
    windows.sort()
    for w, nxt in zip(windows, windows[1:]): w[1] = min(w[1], nxt[0] - 0.2)      # a held title still ends before the next one
    for w in windows:
        if w[1] - w[0] < 0.8: print(f"  !! title {w[4][0][1]!r} squeezed to {w[1] - w[0]:.2f}s — dropped")
    windows = [tuple(w) for w in windows if w[1] - w[0] >= 0.8]
    for t0, t1, i0, i1, lines in windows:
        for i in range(i0, i1 + 1): covered[i] = "title"
    V["title_windows"] = [(w[0], w[1]) for w in windows]
    for wi, (t0, t1, i0, i1, lines) in enumerate(windows):
        # ---- layout: a right-aligned block in the free column right of the speaker, under the logo.
        # Every line is measured in real canvas px and shrunk (never wrapped) so nothing can run over the line below.
        font = V["font"]; sizes = V["title_sizes"]
        lay = []
        for sz, text, color in lines:
            s_pt = sizes[sz]
            while s_pt > sizes[sz] * 0.70 and width_px(text, s_pt, font) > TITLE_BOX_W: s_pt -= 0.1
            w = width_px(text, s_pt, font)
            if w > TITLE_BOX_W: too_wide.append((V["key"], text, round(w)))   # copy too long for the column — say so, don't ship it
            lay.append((s_pt, text, color, w))
        heights = [line_h(s_pt) * (1 + LINE_GAP) for s_pt, *_ in lay]
        total = sum(heights)
        y_cursor = TITLE_MID_PX - total / 2                                 # the block is centred on one fixed line, every time
        dur_us = int((t1 - t0) * US)
        for li, ((s_pt, text, color, w), h) in enumerate(zip(lay, heights)):
            y_center_px = y_cursor + h / 2; y_cursor += h
            yc = (540 - y_center_px) / 540                                  # canvas units, + = up
            xc = (TITLE_RIGHT_PX - w / 2 - 960) / 960                       # right edges aligned
            col = V["hl"] if color is None else WHITE
            kw = set(text.split()) if color is None else set()
            m = text_material(text, styled_ranges(text, col, kw, size=s_pt, font=font), size=s_pt)
            lead = min(li * 0.09, 0.27)                                     # the lines arrive one after the other, not as a slab
            s = text_segment(m, (t0 + lead) * US, int(dur_us - lead * US), x=xc, y=yc,
                             anims=[("in:Fade In", 0.3), ("out:Fade Out", 0.25)])
            motion(s, int(dur_us - lead * US), (xc, yc, 1.0, 0.0), entry=(0.035, 0, -0.03, 0), t_in=0.38, exit_=(0.025, 0, 0.02, 0), t_out=0.25)
            while len(title_tracks) <= li: title_tracks.append(new_track(f"title {len(title_tracks) + 1}", "text"))
            title_tracks[li]["segments"].append(s)
            boxes.append((V["key"], t0, t1, TITLE_RIGHT_PX - w, TITLE_RIGHT_PX, y_center_px - line_h(s_pt) / 2, y_center_px + line_h(s_pt) / 2, "title"))
        title_spans.append((V, t0, t1, total))
        add_sfx(SWOOSH, t0, 0.9, 0.35)
        if os.environ.get("TITLEDBG"):
            print(f"  {V['key']} {t0:7.2f}-{t1:6.2f} " + " | ".join(f"{t!r} s{sp:.2f} w{w:.0f} top{y0:.0f}" for (sp, t, c, w), y0 in zip(lay, [TITLE_MID_PX - total / 2 + sum(heights[:i]) for i in range(len(lay))])))
    # ---- captions: cards of ≤4 words, never across a title window or a sentence mark, ≥0.5 s, single line ≤ CAP_MAX_W px
    LEAD = {"אולי", "את", "של", "עם", "גם", "או", "עד", "על", "כי", "אבל", "כדי", "לפי", "בין", "כמו", "אם"}
    free = [i for i in range(len(ws)) if covered[i] is None]
    runs = []
    for i in free:
        if runs and runs[-1][-1] == i - 1: runs[-1].append(i)
        else: runs.append([i])
    cards = []
    for run in runs:
        cur = []
        def flush():
            if cur: cards.append(list(cur)); cur.clear()
        for i in run:
            cand = cur + [i]; text = " ".join(core(ws[j]["text"]) for j in cand)
            if len(cur) >= 2 and core(ws[i]["text"]) in LEAD: flush()          # a lead word opens the next card, never closes this one
            elif cur and (len(cand) > 4 or width_px(text, CAP_SIZE) > CAP_MAX_W or ws[i]["start_s"] - ws[cur[-1]]["end_s"] > 0.7 or ws[i]["start_s"] - ws[cur[0]]["start_s"] > 3.2): flush()
            cur.append(i)
            if ws[i]["text"][-1:] in ".?!": flush()
        flush()
    # merge cards shorter than 0.5 s into a neighbour inside the same run, when width allows
    def card_dur(c): return ws[c[-1]]["end_s"] - ws[c[0]]["start_s"]
    changed = True
    while changed:
        changed = False
        for ci, c in enumerate(cards):
            if card_dur(c) >= 0.5: continue
            for nb in (ci - 1, ci + 1):
                if 0 <= nb < len(cards) and cards[nb][-1] + 1 == c[0] or (0 <= nb < len(cards) and c[-1] + 1 == cards[nb][0]):
                    merged = sorted(cards[nb] + c); text = " ".join(core(ws[j]["text"]) for j in merged)
                    if len(merged) <= 5 and width_px(text, CAP_SIZE) <= CAP_MAX_W and (core(ws[merged[-1]]["text"]) not in LEAD or card_dur(c) < 0.35) and not (nb < ci and ws[cards[nb][-1]]["text"][-1:] in ".?!") and not (nb > ci and ws[c[-1]]["text"][-1:] in ".?!"):
                        cards[min(nb, ci)] = merged; del cards[max(nb, ci)]; changed = True; break
            if changed: break
    # (post-pass kept as a safety net)
    LEAD = {"אולי", "את", "של", "עם", "גם", "או", "עד", "על", "כי", "אבל", "כדי", "לפי", "בין", "כמו", "אם"}
    for ci in range(len(cards) - 1):
        c, n = cards[ci], cards[ci + 1]
        if len(c) > 1 and c[-1] + 1 == n[0] and core(ws[c[-1]]["text"]) in LEAD and ws[c[-1]]["text"][-1:] not in ".?!":
            if width_px(" ".join(core(ws[j]["text"]) for j in [c[-1]] + n), CAP_SIZE) <= CAP_MAX_W and len(n) < 4:
                cards[ci + 1] = [c.pop()] + n
    cards = [c for c in cards if c]
    kw = set(V["keywords"])
    for ci, c in enumerate(cards):
        t0 = ws[c[0]]["start_s"]; t1 = ws[c[-1]]["end_s"] + 0.15
        nxt = ws[c[-1] + 1]["start_s"] if c[-1] + 1 < len(ws) else t1
        t1 = min(max(t1, nxt if (ci + 1 < len(cards) and cards[ci + 1][0] == c[-1] + 1) else t1), nxt)   # gap-free inside a run
        t1 = min([t1] + [w0 - 0.02 for w0, _, _, _, _ in windows if w0 >= t0])                            # never into a title window
        text = " ".join(ws[j]["text"] for j in c); text = re.sub(r"[.,;:!]", "", text)
        wd = [{"text": core(ws[j]["text"]), "start_ms": int((ws[j]["start_s"] - t0) * 1000), "end_ms": int((ws[j]["end_s"] - t0) * 1000)} for j in c]
        m = text_material(text, styled_ranges(text, V["hl"], kw, size=V["cap_size"], font=V["cap_font"]), words=wd, size=V["cap_size"])
        cap_track["segments"].append(text_segment(m, t0 * US, (t1 - t0) * US, anims=[("in:Fade In", 0.12), ("out:Fade Out", 0.12)]))
        cw = width_px(text, V["cap_size"], V["cap_font"]); cy = 540 - CAP_Y * 540
        boxes.append((V["key"], t0, t1, 960 - cw / 2, 960 + cw / 2, cy - line_h(V["cap_size"]) / 2, cy + line_h(V["cap_size"]) / 2, "caption"))
        for j in c: covered[j] = "caption"
    qa["words_without_caption"] += [(V["key"], ws[i]["text"]) for i in range(len(ws)) if covered[i] is None]
    V["n_cards"] = len(cards); V["n_titles"] = len(windows)
    # ---- name card: bottom-left, left edges aligned, lifted clear of the caption band.
    # It used to sit on the caption's own baseline, so "מנכ״ל WhiteBoard" and the caption beside it
    # read as one run-on line. The caption band is 1244 px wide at most, i.e. x 338–1582, so there is
    # no horizontal escape from it down there — the separation has to be vertical.
    A = W["videos"][V["vi"]]["A"] / US
    NAME_LEFT_PX, NAME_Y1, NAME_Y2, NM1, NM2 = 150, 600, 700, 11.0, 7.5
    f2 = V["font"] if HAS_LATIN[V["font"]] else LIGHT
    n1 = text_material(V["name"][0], styled_ranges(V["name"][0], WHITE, set(), size=NM1, font=V["font"]), size=NM1)
    l2 = V["name"][1]; n2 = text_material(l2, styled_ranges(l2, WHITE, set(), size=NM2, font=f2), size=NM2, alpha=0.9)
    w1, w2 = width_px(V["name"][0], NM1, V["font"]), width_px(l2, NM2, f2)
    x1, x2 = (NAME_LEFT_PX + w1 / 2 - 960) / 960, (NAME_LEFT_PX + w2 / 2 - 960) / 960
    t_n0, t_n1 = A + 1.0, A + 5.5
    n1s = text_segment(n1, t_n0 * US, 4.5 * US, x=x1, y=(540 - NAME_Y1) / 540, anims=[("in:Fade In", 0.35), ("out:Fade Out", 0.4)])
    motion(n1s, int(4.5 * US), (x1, (540 - NAME_Y1) / 540, 1.0, 0.0), entry=(-0.04, 0, 0, 0), t_in=0.45, exit_=(-0.03, 0, 0, 0), t_out=0.4)
    n2s = text_segment(n2, (t_n0 + 0.12) * US, 4.38 * US, x=x2, y=(540 - NAME_Y2) / 540, anims=[("in:Fade In", 0.35), ("out:Fade Out", 0.4)])
    motion(n2s, int(4.38 * US), (x2, (540 - NAME_Y2) / 540, 1.0, 0.0), entry=(-0.04, 0, 0, 0), t_in=0.45, exit_=(-0.03, 0, 0, 0), t_out=0.4)
    name_track["segments"].append(n1s); name_track2["segments"].append(n2s)
    top, bot = NAME_Y1 - line_h(NM1) / 2, NAME_Y2 + line_h(NM2) / 2
    boxes.append((V["key"], t_n0, t_n1, NAME_LEFT_PX, NAME_LEFT_PX + max(w1, w2), top, bot, "name"))
    name_spans.append((V, t_n0, t_n1, bot - top, (top + bot) / 2, NAME_LEFT_PX, w1, (NAME_Y1 + NAME_Y2) / 2 - 4))
print("captions:", {V["key"]: (V["n_cards"], V["n_titles"]) for V in VIDEOS}, "| words without caption:", qa["words_without_caption"])
if fuzzy_hits: print("  anchors matched fuzzily (check them):", *[f"\n    {a!r} → {b!r} ({r})" for a, b, r in fuzzy_hits])

# ---------------------------------------------------------------- music beds
music = new_track("music bed", "audio")
for V in VIDEOS:
    A, B = W["videos"][V["vi"]]["A"], W["videos"][V["vi"]]["B"]
    m = audio_material(f"##_draftpath_placeholder_{DMAT and ''}{''}" if False else str(D / V["music"]), V["music"].replace("ccstudio-bed-", "bed "))
    music["segments"].append(audio_segment(m, A, B - A, V["music_vol"], fade_in=1.0, fade_out=1.6))

# ---------------------------------------------------------------- b-roll layer + whoosh, logos
broll = new_track("broll", "video"); logo = new_track("logo", "video"); mascot = new_track("boardi", "video")
vids = {m["id"]: m for m in mats["videos"]}; PHOTO_DONOR = next(s for s in main["segments"] if vids[s["material_id"]].get("type") == "photo"); PHOTO_MAT = vids[PHOTO_DONOR["material_id"]]
def video_material(path, w, h, dur_us, typ="video"):
    m = copy.deepcopy(PHOTO_MAT); m["id"] = nid(); m["type"] = typ; m["path"] = path; m["material_name"] = os.path.basename(path); m["width"] = w; m["height"] = h; m["duration"] = dur_us
    m["has_audio"] = typ == "video"; m["multi_camera_info"] = None; m["crop"] = {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0}
    mats["videos"].append(m); return m
def video_segment(m, start_us, dur_us, src_us=0, scale=1.0, x=0.0, y=0.0, vol=1.0, sy=None):
    s = copy.deepcopy(PHOTO_DONOR); s["id"] = nid(); s["material_id"] = m["id"]
    s["extra_material_refs"] = capcut._clone_extras(mats, [e for e in extras_of(PHOTO_DONOR) if e["list"] != "drafts"])
    s["target_timerange"] = {"start": int(start_us), "duration": int(dur_us)}; s["source_timerange"] = {"start": int(src_us), "duration": int(dur_us)}
    s["clip"] = {"scale": {"x": scale, "y": scale if sy is None else sy}, "rotation": 0.0, "transform": {"x": x, "y": y}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}
    s["volume"] = vol; s["last_nonzero_volume"] = 1.0; s["render_index"] = next_ri(); s["common_keyframes"] = []; s["keyframe_refs"] = []; return s
def probe(path):
    err = subprocess.run([str(paths.FFMPEG), "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err); wh = re.search(r" (\d{2,5})x(\d{2,5})[, ]", err)
    return int(wh.group(1)), int(wh.group(2)), int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))

# ---------------------------------------------------------------- framed inserts: the real system inside a card
# None of the reference creators shows a raw screen-grab full-frame: reference material sits in a
# rounded card with a shadow on a blurred, darkened plate of itself. Built once per recording with
# ffmpeg (alphamerge against a PIL mask) so CapCut just plays an ordinary MP4.
from PIL import Image as _IM, ImageDraw as _ID, ImageFont as _IF, ImageFilter as _IFL
CARD_W, CARD_H, CARD_X, CARD_Y, CARD_R = 1180, 664, 100, 208, 28
def _card_masks():
    mp, sp = D / "ccstudio-card-mask.png", D / "ccstudio-card-shadow.png"
    if not mp.exists():
        m = _IM.new("L", (CARD_W, CARD_H), 0); _ID.Draw(m).rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), CARD_R, fill=255); m.save(mp)
    if not sp.exists():
        pad = 60; sh = _IM.new("RGBA", (CARD_W + 2 * pad, CARD_H + 2 * pad), (0, 0, 0, 0))
        _ID.Draw(sh).rounded_rectangle((pad, pad + 18, pad + CARD_W, pad + CARD_H + 18), CARD_R, fill=(0, 0, 0, 170))
        sh.filter(_IFL.GaussianBlur(26)).save(sp)
    return mp, sp
def framed_asset(src_name):
    """ccstudio-broll-sys-hub.mp4 → ccstudio-frame-sys-hub.mp4 (idempotent)"""
    src = D / src_name; out = D / src_name.replace("ccstudio-broll-", "ccstudio-frame-")
    if out.exists() or not src.exists(): return out
    mp, sp = _card_masks()
    fc = (f"[0:v]split=2[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=28:3,eq=brightness=-0.32:saturation=0.65[plate];"
          f"[b]scale={CARD_W}:{CARD_H}:force_original_aspect_ratio=decrease,pad={CARD_W}:{CARD_H}:-1:-1:color=0x0e1a2b,format=rgba[card];"
          f"[card][2:v]alphamerge[cardr];[plate][1:v]overlay={CARD_X - 60}:{CARD_Y - 60}[p2];[p2][cardr]overlay={CARD_X}:{CARD_Y}[out]")
    subprocess.run([str(paths.FFMPEG), "-v", "error", "-y", "-i", str(src), "-i", str(sp), "-i", str(mp), "-filter_complex", fc, "-map", "[out]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(out)], check=True)
    return out
for V in VIDEOS:
    for phrase, fn, dur in V["broll"]:
        if fn.startswith("ccstudio-frame-"): framed_asset(fn.replace("ccstudio-frame-", "ccstudio-broll-"))

# ---------------------------------------------------------------- chapter cards, drawn locally (Hebrew is never generated)
from landing_16x9_cards import chapter_card as _chapter_card, rtl              # opaque cards; see that module's docstring
def chapter_card(V, num, text): return _chapter_card(D, V["key"], num, text)

# ---------------------------------------------------------------- chapter cards on the timeline (placed before the b-roll, which yields to them)
chapter_tr = new_track("chapter", "video")
# 2.8 s on screen, a 0.4 s fade each way and a 4 % drift: readable, and one device at a time. v2.1's
# 1.6 s zoom-through with 3° of rotation plus a counter-moving HUD layer left under a second of
# reading time (Alon: "הכניסה של הפרקים מהירה ולא נעימה").
for V, num, text, t0 in chapter_plan:
    png = chapter_card(V, num, text); cm = video_material(str(png), 1920, 1080, 10800000000, typ="photo")
    cs = video_segment(cm, t0 * US, CH_DUR * US, scale=1.0)
    motion(cs, int(CH_DUR * US), (0, 0, 1.0, 0.0), entry=(0, 0, -0.02, 0), t_in=0.5, drift=(0, 0, 0.04, 0), fade=(0.4, 0.4))
    chapter_tr["segments"].append(cs); add_sfx(WHOOSH, t0, 1.0, 0.35)
print("chapters:", len(chapter_tr["segments"]), "| slots:", [round(a, 1) for a, b in chapter_slots])

missing = []
for V in VIDEOS:
    ws = W["videos"][V["vi"]]["words"]; A, B = W["videos"][V["vi"]]["A"] / US, W["videos"][V["vi"]]["B"] / US
    placed = []
    for phrase, fn, dur in V["broll"]:
        if not (D / fn).exists(): missing.append(fn); continue
        i0, i1 = find_phrase(ws, phrase)
        j = i1                                                                # the clip is literal for its whole SENTENCE, not just the anchor words
        while j + 1 < len(ws) and not core(ws[j]["text"]) != ws[j]["text"].strip() and ws[j + 1]["start_s"] - ws[j]["end_s"] < 0.35 and ws[j]["end_s"] - ws[i1]["end_s"] < 4.0: j += 1
        placed.append((ws[i0]["start_s"] - 0.1, fn, dur, ws[j]["end_s"]))
    for t0, fn, dur, t_phrase_end in sorted(placed):                                     # by TIME — the spacing rule below reads the previous clip, so list order must not decide
        p = D / fn
        if t0 < A + 6.0: t0 = max(t0, A + 6.0)      # never over the name card
        t1 = min(t0 + dur, B - 0.5)
        hit = next(((c0, c1) for c0, c1 in chapter_slots if t0 < c1 + 2.0 and t1 > c0 - 1.0), None)
        if hit:                                                              # chapter cards were placed first and win, with air on both sides
            c0, c1 = hit
            if t0 < c0 and c0 - 1.0 - t0 >= 2.0: t1 = c0 - 1.0
            elif c1 + 2.0 <= t_phrase_end + 1.5: t0 = c1 + 2.0; t1 = t0 + dur          # still inside its own sentence: wait for the card to leave
            else: print(f"  b-roll {fn} at {t0:.1f} skipped: a chapter card sits on its sentence (a delayed clip is no longer literal)"); continue
        if broll["segments"] and t0 < (broll["segments"][-1]["target_timerange"]["start"] + broll["segments"][-1]["target_timerange"]["duration"]) / US + 2.0:
            print(f"  b-roll {fn} at {t0:.1f} skipped: within 2 s of the previous clip"); continue
        w, h, L = probe(str(p)); m = video_material(str(p), w, h, int(L * US))
        s = video_segment(m, t0 * US, (t1 - t0) * US, src_us=int(0.3 * US), vol=0.0)
        # v2.1 entered every clip from 112 % with a slide and left on an 8 % punch — "קי פריימים אגרסיביים
        # מאוד בבי רולס שלא לצורך". Now: a framed insert only fades; footage settles from 104 % over 0.6 s,
        # pushes 3 % across the hold, and leaves on a plain cut.
        if fn.startswith("ccstudio-frame-"): motion(s, int((t1 - t0) * US), (0, 0, 1.0, 0), drift=(0, 0, 0.02, 0), off_us=int(0.3 * US), fade=(0.35, 0.3))
        else: motion(s, int((t1 - t0) * US), (0, 0, 1.0, 0), entry=(0, 0, 0.04, 0), t_in=0.6, drift=(0, 0, 0.03, 0), off_us=int(0.3 * US))
        broll["segments"].append(s); add_sfx(WHOOSH, t0, 1.2, 0.35)
        if os.environ.get("TITLEDBG"): print(f"  b-roll {fn:28s} {t0:7.2f}-{t1:6.2f}")
    # BOARDi mascot: pops in low-left beside the speaker on the AI lines (never over the captions)
    for phrase, dur in V.get("mascot", []):
        bp = D / "ccstudio-boardi.png"
        if not bp.exists(): continue
        i0, i1 = find_phrase(ws, phrase); t0 = ws[i0]["start_s"] - 0.15
        from PIL import Image as _I; mw, mh = _I.open(bp).size
        mm_ = video_material(str(bp), mw, mh, 10800000000, typ="photo")
        sc0 = 0.17
        ms_ = video_segment(mm_, t0 * US, dur * US, scale=sc0, x=-0.60, y=-0.28)
        keys = [kf(0, 0.01, "CurveInOut"), kf(int(0.26 * US), sc0 * 1.10, "CurveInOut"), kf(int(0.42 * US), sc0, "CurveInOut"),
                kf(int((dur - 0.3) * US), sc0, "CurveInOut"), kf(int(dur * US), 0.01, "CurveInOut")]
        ms_["common_keyframes"] = [group("KFTypeScaleX", keys), group("KFTypeScaleY", [dict(x, id=nid()) for x in keys])]
        ms_["clip"]["scale"] = {"x": 0.01, "y": 0.01}
        mascot["segments"].append(ms_); add_sfx(WHOOSH, t0, 0.9, 0.3)
    # logo: top-right corner for the whole video span
    lp = D / V["logo"]; from PIL import Image; lw, lh = Image.open(lp).size
    lm = video_material(str(lp), lw, lh, 10800000000, typ="photo")
    rendered_w = 1920 * V["logo_scale"]; x = 1 - (rendered_w / 2 + 40) / 960; y = 1 - (rendered_w * lh / lw / 2 + 40) / 540
    ls_ = video_segment(lm, A * US, (B - A) * US, scale=V["logo_scale"], x=x, y=y)
    motion(ls_, int((B - A) * US), (x, y, V["logo_scale"], 0.0), entry=(0, 0.06, -0.15, 0), t_in=0.6)
    logo["segments"].append(ls_)
print("broll:", len(broll["segments"]), "clips | missing files:", missing, "| logos:", len(logo["segments"]))

# ---------------------------------------------------------------- the bed ducks −3 dB under every full-frame overlay
# CapCut has no sidechain; KFTypeVolume keyframes on the bed pieces are the mechanism (0910 round 10).
covers = sorted([(s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]) for t in (broll, chapter_tr) for s in t["segments"]])
for ms_ in music["segments"]:
    base_v = ms_["volume"]; a0, a1 = ms_["target_timerange"]["start"], ms_["target_timerange"]["start"] + ms_["target_timerange"]["duration"]
    R = int(0.30 * US); keys = [kf(0, base_v)]
    for c0, c1 in covers:
        if c1 <= a0 or c0 >= a1: continue
        c0, c1 = max(c0, a0 + R), min(c1, a1 - R)
        keys += [kf(c0 - R - a0, base_v, "CurveInOut"), kf(c0 - a0, base_v * 0.71, "CurveInOut"), kf(c1 - a0, base_v * 0.71, "CurveInOut"), kf(c1 + R - a0, base_v, "CurveInOut")]
    keys.append(kf(a1 - a0, base_v))
    keys.sort(key=lambda x: x["time_offset"]); ms_["common_keyframes"] = [group("KFTypeVolume", keys)]
print("ducking:", sum(len(ms_["common_keyframes"][0]["keyframe_list"]) for ms_ in music["segments"]), "volume keys over", len(covers), "covers")

# ---------------------------------------------------------------- the title furniture: scrim + accent rule
# A title is only as good as its background. Over the studio the white kicker reads fine; over a
# white screen-grab of the system it disappears, which is exactly what happened at 0:18. So every
# title brings its own gradient scrim — dark at the right edge, gone by the middle of the frame —
# and a fixed accent rule in the video's colour. Both are generated here so the look is one recipe.
from PIL import Image as _IM
def _make_scrim(path):
    if Path(path).exists(): return
    im = _IM.new("RGBA", (1920, 1080), (0, 0, 0, 0)); px = im.load()
    for x in range(1920):
        fx = max(0.0, (x - 420) / (1860 - 420)) ** 1.5                      # nothing on the left half
        for y in range(1080):
            fy = min(1.0, y / 120.0) * min(1.0, max(0.0, (760 - y) / 200.0))  # a band around the title block
            a = int(165 * fx * fy)
            if a: px[x, y] = (8, 14, 28, a)
    im.save(path)
def _make_rule(path, rgb):
    if Path(path).exists(): return
    h = 1000; im = _IM.new("RGBA", (24, h), (0, 0, 0, 0)); px = im.load()
    for y in range(h):
        a = int(255 * min(1.0, y / (h * 0.08)) * min(1.0, (h - y) / (h * 0.08)))
        for x in range(24): px[x, y] = (*rgb, a)
    im.save(path)
SCRIM = D / "ccstudio-title-scrim.png"; _make_scrim(SCRIM)
plate_tr = new_track("title plate", "video")
def _make_plate(path, rgb, rule_h):
    """scrim + the accent rule for one block height, baked into one PNG — one track instead of two"""
    if Path(path).exists(): return
    im = _IM.open(SCRIM).convert("RGBA"); px = im.load()
    y0, y1 = int(TITLE_MID_PX - rule_h / 2), int(TITLE_MID_PX + rule_h / 2); soft = max(4, int(rule_h * 0.08))
    for y in range(max(0, y0), min(1080, y1)):
        a = int(255 * min(1.0, (y - y0) / soft) * min(1.0, (y1 - y) / soft))
        for x in range(RULE_X_PX - 5, RULE_X_PX + 5): px[x, y] = (*rgb, a)
    im.save(path)
_plates = {}
def _fade(seg, dur_us, up=0.35, down=0.3):
    keys = [kf(0, 0.0), kf(int(up * US), 1.0, "CurveInOut"), kf(int(dur_us - down * US), 1.0, "CurveInOut"), kf(int(dur_us), 0.0)]
    seg["common_keyframes"] = [group("KFTypeAlpha", keys)]; seg["clip"]["alpha"] = 1.0; return seg
for V, t0, t1, block_h in title_spans:
    dur = int((t1 - t0) * US); h = int(round((block_h + 26) / 20.0) * 20)     # a plate per 20 px of block height: a handful of files, not one per title
    key = (V["key"], h)
    if key not in _plates:
        pp = D / f"ccstudio-title-plate-{V['key']}-{h}.png"; _make_plate(pp, tuple(int(255 * c) for c in V["hl"]), h)
        _plates[key] = video_material(str(pp), 1920, 1080, 10800000000, typ="photo")
    plate_tr["segments"].append(_fade(video_segment(_plates[key], t0 * US, dur, scale=1.0), dur))
def _make_hrule(path, rgb):
    if Path(path).exists(): return
    w = 1000; im = _IM.new("RGBA", (w, 24), (0, 0, 0, 0)); px = im.load()
    for x in range(w):
        a = int(255 * min(1.0, x / (w * 0.06)) * min(1.0, (w - x) / (w * 0.06)))
        for y in range(24): px[x, y] = (*rgb, a)
    im.save(path)
for V, t0, t1, block_h, mid, x_left, w_name, y_line in name_spans:        # Martell's lower-third: a thin accent underline between name and role
    dur = int((t1 - t0) * US)
    hp = D / f"ccstudio-hrule-{V['key']}.png"; _make_hrule(hp, tuple(int(255 * c) for c in V["hl"]))
    rm = video_material(str(hp), 1000, 24, 10800000000, typ="photo")
    sx, sy = w_name / 1920, 4.0 / (1920 * 24 / 1000)                       # a wide flat photo is fitted by width: 1920 × 46 px at scale 1
    plate_tr["segments"].append(_fade(video_segment(rm, (t0 + 0.12) * US, dur - int(0.12 * US), scale=sx, sy=sy, x=(x_left + w_name / 2 - 960) / 960, y=(540 - y_line) / 540), dur - int(0.12 * US)))
print("title furniture:", len(plate_tr["segments"]), "plates (", len(_plates), "distinct PNGs ) + name underlines")

# ---------------------------------------------------------------- assemble tracks: video layers first (broll under logo), then text, then audio
d["tracks"] = d["tracks"][:2] + [t for t in (broll, chapter_tr, plate_tr, mascot, logo) if t["segments"]] + d["tracks"][2:] + [cap_track] + title_tracks + [name_track, name_track2, music, sfx]
print("tracks:", len(d["tracks"]), [t.get("name") or t["type"] for t in d["tracks"]])
for t in d["tracks"]:
    for i, s in enumerate(sorted(t["segments"], key=lambda s: s["target_timerange"]["start"])): pass
    t["segments"].sort(key=lambda s: s["target_timerange"]["start"])
# QA: overlaps inside every new track
for t in d["tracks"]:
    if t.get("name") in OURS or (t.get("name") or "").startswith("title"):
        segs = t["segments"]; ov = sum(1 for a, b in zip(segs, segs[1:]) if a["target_timerange"]["start"] + a["target_timerange"]["duration"] > b["target_timerange"]["start"] + 1)
        if ov: print(f"  !! {t['name']}: {ov} overlaps")
# QA the LAYOUT, not just the timeline: every text box in real canvas px, checked against the frame
# and against every other box that is on screen at the same moment. This is the check that was
# missing — the timeline was clean while two blocks sat on the same baseline.
if too_wide: print("  !! copy too wide for the title column:", too_wide)
off = [b for b in boxes if b[3] < 90 or b[4] > 1830 or b[5] < 40 or b[6] > 1040]
print("  text outside the safe frame:", [(b[0], b[7], round(b[3]), round(b[4])) for b in off] or "none")
clash = []
for i, a in enumerate(boxes):
    for b in boxes[i + 1:]:
        if a[0] != b[0] or a[7] == b[7] == "caption": continue
        if a[2] <= b[1] + 0.02 or b[2] <= a[1] + 0.02: continue                       # not on screen together
        if a[4] <= b[3] + 8 or b[4] <= a[3] + 8 or a[6] <= b[5] + 8 or b[6] <= a[5] + 8: continue
        clash.append((a[7], b[7], round(max(a[1], b[1]), 2)))
print("  overlapping text boxes:", len(clash), clash[:6])
d["duration"] = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for t in d["tracks"] for s in t["segments"])
plan_out = {V["key"]: {"plan": V["plan"], "cards": V["n_cards"], "titles": V["n_titles"]} for V in VIDEOS}
json.dump(plan_out, open(SP / f"{NAME}_plan.json", "w"), ensure_ascii=False, indent=1)
if DRY: print("DRY RUN — nothing written"); sys.exit()
capcut._backup(D); tmp = D / "draft_info.json.tmp"
tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("WRITTEN")
