# -*- coding: utf-8 -*-
"""Speaker-coloured Hebrew captions for a finished reel, built from the two mics.

This is the pipeline in SKILL.md stage 7, end to end and parameterised, because
it had been rewritten from scratch on three projects and each rewrite lost a
lesson: per-word ownership (not blanket speaker regions), zero-length words
dropped first, cards split by DP instead of greedily, terms glued before
chunking, and every card clipped to the segment it lives in.

    python reel_captions.py "<project>" \
        --mic1 ".../1_COMBO-1.wav" --mic2 ".../2_COMBO-2.wav" \
        --donor "פרויקט-דוגמה N רילס" --cap-y -0.426          # dry run
    ... --write [--replace]                                # and again to inject

The mic wavs must be the raw per-channel recordings that are **sample-aligned
with the camera files** (same length): the script walks the main track and pulls
each segment's `source_timerange` out of them, so the audio it transcribes is
the cut as it is now. If they are not aligned, cross-correlate first and pass
`--mic-offset`.

Read-only without `--write`, and it refuses while CapCut holds the draft.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys

import numpy as np
from PIL import ImageFont

sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000
SR = 16000
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")

ap = argparse.ArgumentParser(description="speaker-coloured captions for a reel draft")
ap.add_argument("project")
ap.add_argument("--mic1", required=True, help="raw channel of camera 1 (wav)")
ap.add_argument("--mic2", default="", help="raw channel of camera 2 (wav)")
ap.add_argument("--mono", action="store_true",
                help="the shoot has no isolated channels — one summed mix. Captions "
                     "come out in a single colour, because per-word ownership off a "
                     "mix is a guess dressed as a measurement")
ap.add_argument("--mono-own", type=int, default=2,
                help="which colour the single-mix captions take (1 = yellow, 2 = white)")
ap.add_argument("--mic-offset", type=float, default=0.0,
                help="seconds to add to source time when reading the mic wavs")
ap.add_argument("--mic-offset-map", default="",
                help="JSON file of [start, end, offset] triples (project-clock "
                     "seconds) for a source whose own offset to the mics is not "
                     "one constant — a program file (רז) baked from several "
                     "takes drifts or jumps at each internal splice. FOOT pieces "
                     "are further split at these boundaries (a caption may not "
                     "straddle one, same as any other cut) and each piece reads "
                     "the mics at its own offset instead of --mic-offset.")
ap.add_argument("--max-lines", type=int, default=1,
                help="a card may wrap onto this many lines (each ≤ the width "
                     "ceiling) instead of forcing one long line or a hard split")
ap.add_argument("--keep-punct", action="store_true",
                help="keep the transcriber's punctuation instead of stripping it "
                     "— readable-sentence (YouTube) style, not punchy reel style")
ap.add_argument("--split-sentences", action="store_true",
                help="end a card at a sentence-ending . ! ? — never carry a new "
                     "sentence into the same card as the one before it. Only "
                     "meaningful with --keep-punct (a stripped '.' can't be seen)")
ap.add_argument("--main-track", type=int, default=0,
                help="index of the track whose segments define the real time jumps")
ap.add_argument("--donor-track", type=int, default=-1,
                help="index of the donor's text track to clone (default: the one with most segments — "
                     "wrong when the biggest track is an older reel set in another style, as on 0830 (1))")
ap.add_argument("--all-white", action="store_true",
                help="both speakers in the cool colour (a single-colour donor track is then fine)")
ap.add_argument("--donor", default="פרויקט-דוגמה N רילס",
                help="project to clone the caption style (and width ceiling) from")
ap.add_argument("--cap-y", type=float, required=True,
                help="transform.y for every caption — measure it, do not guess")
ap.add_argument("--font", default=os.path.expanduser(
    "~/Library/Fonts/bamberger-grunge-bold-fm.ttf"))
ap.add_argument("--work", default=os.path.expanduser("~/Movies/reel-captions-work"))
ap.add_argument("--terms", default="", help="file of multi-word terms, one per line")
ap.add_argument("--max-words", type=int, default=3)
ap.add_argument("--max-dur", type=float, default=3.0)
ap.add_argument("--min-dur", type=float, default=0.42,
                help="shortest a card may live on screen — read off his reels")
ap.add_argument("--max-gap", type=float, default=0.25,
                help="a pause longer than this ends the card")
ap.add_argument("--shadow-white", action="store_true",
                help="drop shadow on the white speaker (light clothing/background)")
ap.add_argument("--cap-size", type=float, default=0.0,
                help="override the donor's font size. A 9:16 donor's 20 is not a "
                     "16:9 caption — his own landscape reels run at an effective 10")
ap.add_argument("--width-limit", type=float, default=1.0,
                help="multiplier on the donor's line-width ceiling; a wider canvas "
                     "at a smaller size holds a longer line")
ap.add_argument("--range", default="",
                help="only caption this span of the timeline, START:END in seconds — "
                     "for adding captions to one block of a project that already has them")
ap.add_argument("--track-name", default="כתוביות")
ap.add_argument("--add", action="store_true",
                help="add another caption track instead of refusing because one exists")
ap.add_argument("--reuse", action="store_true", help="reuse cached audio + words")
ap.add_argument("--write", action="store_true")
ap.add_argument("--replace", action="store_true", help="drop an existing caption track")
A = ap.parse_args()
if not A.mono and not A.mic2:
    ap.error("--mic2 חסר (או --mono אם אין ערוצים נפרדים)")
if A.mono:
    A.mic2 = A.mic1

DST = capcut.DRAFTS_DIR / A.project
os.makedirs(A.work, exist_ok=True)
CACHE = os.path.join(A.work, re.sub(r"\W+", "_", A.project + ("_" + A.range if A.range else "")))
draft = json.loads((DST / "draft_info.json").read_text())
FR = US / draft.get("fps", 30.0)          # CapCut re-rounds every segment to this grid
snap = lambda t: int(round(t * US / FR) * FR)                          # noqa: E731
main = draft["tracks"][A.main_track]
_VM = {m["id"]: m for m in draft["materials"].get("videos", [])}
# A title card is not footage: its source_timerange starts at 0, so pulling the
# mics at that offset lays the first seconds of the episode under a white frame
# and the transcriber duly writes captions for it. Cards are gaps here.
#
# ⚠️ "card" is not only type == photo. A **Compound clip** is type video with an
# EMPTY path, and it slipped through this filter on 0830: its source_timerange
# starts at 0 too, so the engine transcribed the opening seconds of the episode
# and laid «יאללה אליפות» over the first 2.5s. Alon read it as invented words.
# The honest test is a real file on disk, not the type field.
def _is_footage(seg):
    m = _VM.get(seg["material_id"], {})
    return m.get("type") != "photo" and bool(m.get("path"))

# A **Multi-camera clip** is a compound, and a compound is not a card: it has an
# empty path like a card does, but there is real footage inside it. Dropping it
# leaves nothing to transcribe on a project he has already turned into multicam;
# transcribing it blind reads the wrapper's source clock, which is the compound's
# own zero and not the camera's. Walk into the nested draft — it lives inline at
# materials.drafts[i].draft — and re-express each piece in the underlying file's
# clock, splitting wherever the nested cut does.
_DRAFTS = {m["id"]: m["draft"] for m in draft["materials"].get("drafts", [])
           if isinstance(m.get("draft"), dict)}


def _flatten(segs, vm, drafts, depth=0):
    """Segments whose source_timerange speaks the real file's clock."""
    out = []
    for s in segs:
        mat = vm.get(s["material_id"])
        # ⚠️ A card can carry a real path too — the white-card asset here is a
        # genuine file on disk (a rendered .image), not an empty placeholder.
        # Checking path alone let it through as "footage": CLIPS then included
        # its outer time slot, and build_audio() pasted whatever the mic wavs
        # held at the card's own (arbitrary) source_timerange into that slot —
        # real speech from an unrelated moment, not silence. Same test as
        # _is_footage(), or a card is captioned with someone else's words.
        if mat is not None and mat.get("path") and mat.get("type") != "photo":
            out.append(s)
            continue
        # ⚠️ The compound is NOT reachable from material_id — that resolves to a
        # placeholder `videos` entry with an empty path, one per cut piece. The
        # nested draft hangs off the segment's extra_material_refs.
        nd = next((drafts[r] for r in s.get("extra_material_refs", []) if r in drafts), None)
        if nd is None or depth > 3:
            continue                                   # a genuine card
        ntr = max((t for t in nd["tracks"] if t["type"] == "video"),
                  key=lambda t: len(t["segments"]), default=None)
        if ntr is None:
            continue
        nvm = {m["id"]: m for m in nd["materials"].get("videos", [])}
        ndr = {m["id"]: m["draft"] for m in nd["materials"].get("drafts", [])
               if isinstance(m.get("draft"), dict)}
        inner = _flatten(sorted(ntr["segments"], key=lambda x: x["target_timerange"]["start"]),
                         nvm, ndr, depth + 1)
        sp = s.get("speed") or 1.0
        c0 = (s.get("source_timerange") or {}).get("start", 0)          # compound clock
        c1 = c0 + s["target_timerange"]["duration"] * sp
        for n in inner:
            na = n["target_timerange"]["start"]
            nb = na + n["target_timerange"]["duration"]
            lo, hi = max(na, c0), min(nb, c1)
            if hi - lo <= 1000:
                continue
            nsp = n.get("speed") or 1.0
            piece = copy.deepcopy(s)
            piece["target_timerange"] = {
                "start": int(round(s["target_timerange"]["start"] + (lo - c0) / sp)),
                "duration": int(round((hi - lo) / sp))}
            piece["source_timerange"] = {
                "start": int(round(n["source_timerange"]["start"] + (lo - na) * nsp)),
                "duration": int(round((hi - lo) * nsp))}
            piece["speed"] = sp * nsp
            out.append(piece)
    return out


_flat = _flatten(sorted(main["segments"], key=lambda s: s["target_timerange"]["start"]),
                 _VM, _DRAFTS)
_n_comp = sum(1 for s in main["segments"]
              if any(r in _DRAFTS for r in s.get("extra_material_refs", [])))
if _n_comp:
    print(f"נפתחו {_n_comp} קליפים מרוכבים (Multi-camera) → {len(_flat)} מקטעי צילום "
          f"בשעון הקובץ עצמו")
FOOT = sorted(_flat, key=lambda s: s["target_timerange"]["start"])
_skipped = [s for s in main["segments"] if not _is_footage(s)
            and not any(r in _DRAFTS for r in s.get("extra_material_refs", []))]
if _skipped:
    print(f"מדלג על {len(_skipped)} מקטעים שאינם צילום "
          f"(כרטיס/Compound — אין להם מקור אמיתי): "
          + ", ".join(f"{s['target_timerange']['start']/US:.2f}" for s in _skipped[:6]))
if A.range:
    # ⚠️ Selecting "the segments that overlap the window" is only equivalent to
    # the window in a reels project, where the segments ARE the reels. On an
    # episode the main track is two segments a quarter of an hour long, so the
    # filter quietly selects the whole episode and captions everything. Clip the
    # copies to the window instead — and accept several windows separated by
    # commas, so a set of marked reels becomes ONE transcription and one card
    # grid rather than four tracks to merge by hand.
    WINS = sorted(tuple(float(v) for v in part.split(":")) for part in A.range.split(","))
    for _i in range(len(WINS) - 1):
        if WINS[_i][1] > WINS[_i + 1][0]:
            sys.exit(f"✗ טווחים חופפים: {WINS[_i]} ו-{WINS[_i + 1]}")
    _cut = []
    for s in FOOT:
        a = s["target_timerange"]["start"] / US
        b = a + s["target_timerange"]["duration"] / US
        sp = s.get("speed") or 1.0
        for ra, rb in WINS:
            lo, hi = max(a, ra), min(b, rb)
            if hi - lo <= 0.01:
                continue
            c = copy.deepcopy(s)
            c["target_timerange"] = {"start": int(round(lo * US)),
                                     "duration": int(round((hi - lo) * US))}
            if s.get("source_timerange"):
                c["source_timerange"] = {
                    "start": int(round(s["source_timerange"]["start"] + (lo - a) * sp * US)),
                    "duration": int(round((hi - lo) * sp * US))}
            _cut.append(c)
    FOOT = sorted(_cut, key=lambda s: s["target_timerange"]["start"])
    if not FOOT:
        sys.exit(f"✗ אין צילום בטווח {A.range}")
    print("חלונות: " + " · ".join(f"{x:.2f}–{y:.2f}" for x, y in WINS))
if A.mic_offset_map:
    # A single source file can still carry several internal splices baked in —
    # a program (רז) cut together from takes has no CapCut-level segment
    # boundary at each one, but the mics-to-file offset still jumps there. Cut
    # FOOT the same way --range does, at each map boundary, and stamp the
    # offset onto the piece so build_audio() reads the right stretch of the
    # mic wavs instead of guessing one constant across a splice.
    OMAP = sorted(tuple(v) for v in json.load(open(A.mic_offset_map)))
    _cut = []
    for s in FOOT:
        a = s["target_timerange"]["start"] / US
        b = a + s["target_timerange"]["duration"] / US
        sp = s.get("speed") or 1.0
        for ra, rb, moff in OMAP:
            lo, hi = max(a, ra), min(b, rb)
            if hi - lo <= 0.01:
                continue
            c = copy.deepcopy(s)
            c["target_timerange"] = {"start": int(round(lo * US)),
                                     "duration": int(round((hi - lo) * US))}
            if s.get("source_timerange"):
                c["source_timerange"] = {
                    "start": int(round(s["source_timerange"]["start"] + (lo - a) * sp * US)),
                    "duration": int(round((hi - lo) * sp * US))}
            c["_moff"] = moff
            _cut.append(c)
    FOOT = sorted(_cut, key=lambda s: s["target_timerange"]["start"])
    if not FOOT:
        sys.exit("✗ אין חפיפה בין הצילום למפת האופסטים")
    print(f"מפת אופסטים: {len(OMAP)} מקטעים → {len(FOOT)} מקטעי צילום")

CLIPS = [(s["target_timerange"]["start"] / US,
          (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / US)
         for s in FOOT]
# Everything downstream works in timeline seconds, but the audio array only
# covers the range — carrying a quarter hour of silence in front of it would
# both waste the transcription and give the model room to hallucinate into.
OFF = CLIPS[0][0]
print(f"טווח: {CLIPS[0][0]:.2f}–{CLIPS[-1][1]:.2f}s | {len(FOOT)} מקטעי צילום")


def clip_of(t):
    for i, (a, b) in enumerate(CLIPS):
        if a <= t < b:
            return i
    return -1


# ---------------------------------------------------------------- timeline audio

def grab(path, ss, dur):
    out = subprocess.run([FF, "-v", "error", "-ss", f"{ss:.6f}", "-t", f"{dur:.6f}",
                          "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.float32)


def build_audio():
    end = CLIPS[-1][1] - OFF
    tot = int(end * SR) + SR
    m1 = np.zeros(tot, np.float32)
    m2 = np.zeros(tot, np.float32)
    for s in FOOT:
        src = s["source_timerange"]["start"] / US + s.get("_moff", A.mic_offset)
        L = s["target_timerange"]["duration"] / US
        i0 = int(round((s["target_timerange"]["start"] / US - OFF) * SR))
        a, b = grab(A.mic1, src, L + 0.05), grab(A.mic2, src, L + 0.05)
        k = min(len(a), len(b), tot - i0, int(round(L * SR)))
        m1[i0:i0 + k] += a[:k]
        m2[i0:i0 + k] += b[:k]
    return m1, m2


# ⚠️ The cache belongs to the cut it was built from. Alon trimmed 39s out of
# 0830 between two runs and --reuse replayed the old word timings onto the new
# timeline: every card landed on different footage. The signature is cheap.
_SIG = json.dumps([[s["target_timerange"]["start"], s["target_timerange"]["duration"],
                    (s.get("source_timerange") or {}).get("start")] for s in FOOT])
if A.reuse and os.path.exists(CACHE + "-sig.json"):
    if open(CACHE + "-sig.json").read() != _SIG:
        sys.exit("✗ הציר השתנה מאז שהמטמון נבנה — הכרטיסים ינחתו על חומר אחר. "
                 "להריץ בלי --reuse.")
open(CACHE + "-sig.json", "w").write(_SIG)
if A.reuse and os.path.exists(CACHE + "-m1.npy"):
    m1, m2 = np.load(CACHE + "-m1.npy"), np.load(CACHE + "-m2.npy")
else:
    m1, m2 = build_audio()
    np.save(CACHE + "-m1.npy", m1)
    np.save(CACHE + "-m2.npy", m2)
e1, e2 = float((m1 ** 2).sum()), float((m2 ** 2).sum())
print(f"אודיו: {len(CLIPS)} מקטעים | {len(m1)/SR:.2f}s | מיק'1 {100*e1/(e1+e2):.1f}% מהאנרגיה")


def energy(x, a, b):
    i, j = int((a - OFF) * SR), max(int((b - OFF) * SR), int((a - OFF) * SR) + 1)
    return float((x[max(i, 0):j] ** 2).sum())


# ---------------------------------------------------------------- transcribe

if A.reuse and os.path.exists(CACHE + "-words.json"):
    raw = json.load(open(CACHE + "-words.json"))
else:
    import transcribe
    raw = []
    for i, a in (((A.mono_own, m1),) if A.mono else ((1, m1), (2, m2))):
        print(f"מתמלל {'מיקס' if A.mono else 'מיקרופון ' + str(i)} ({len(a)/SR:.0f}s) ...",
              flush=True)
        w = transcribe.transcribe(a)
        for x in w:
            x["mic"] = i
            x["start_s"] += OFF                 # array time -> timeline time
            x["end_s"] += OFF
        print(f"  ✓ {len(w)} מילים", flush=True)
        raw += w
    json.dump(raw, open(CACHE + "-words.json", "w"), ensure_ascii=False)

# ---------------------------------------------------------------- ownership
# Per word, not per region. A blanket speaker region built from the envelope
# lets a 0.3s «אוקיי» swallow the words the other channel actually said.
raw = [w for w in raw if w["end_s"] - w["start_s"] >= 0.06]      # transcriber artefacts
words = []
if A.mono:
    # nothing to own: one mix, one colour. Saying so is the honest output —
    # inferring a speaker from a summed track is how a card ends up in the
    # wrong man's colour with a measurement's confidence behind it.
    words = [{**w, "own": A.mono_own, "ratio": 1.0} for w in raw]
for w in ([] if A.mono else raw):
    a, b = w["start_s"], max(w["end_s"], w["start_s"] + 0.08)
    ea, eb = energy(m1, a, b), energy(m2, a, b)
    if (1 if ea > eb else 2) == w["mic"]:
        words.append({**w, "own": w["mic"], "ratio": max(ea, eb) / max(min(ea, eb), 1e-12)})
words.sort(key=lambda w: (w["start_s"], w["end_s"]))

dedup = []
for w in words:                                  # same token on both channels = bleed
    if dedup:
        p = dedup[-1]
        ov = min(p["end_s"], w["end_s"]) - max(p["start_s"], w["start_s"])
        same = p["text"].strip(".,!?") == w["text"].strip(".,!?")
        if p["own"] != w["own"] and ((same and ov > -0.35) or ov > 0.6 * min(
                p["end_s"] - p["start_s"], w["end_s"] - w["start_s"])):
            if w["ratio"] > p["ratio"]:
                dedup[-1] = w
            continue
    dedup.append(w)
words = dedup
print(f"מילים: {len(raw)} גולמיות → {len(words)} אחרי בעלות "
      f"(מיק'1 {sum(1 for w in words if w['own']==1)} | מיק'2 {sum(1 for w in words if w['own']==2)})")

# ---------------------------------------------------------------- text clean-up
PUNCT = re.compile(r"[.,;:!?\"'־–—]+")
if A.keep_punct:
    clean = [{**w, "text": w["text"].strip()} for w in words]
else:
    clean = [{**w, "text": PUNCT.sub("", w["text"]).strip()} for w in words]
clean = [w for w in clean if w["text"]]
for i in range(len(clean) - 1):                  # «ל -4» → «ל-4», before the dash goes
    if clean[i]["text"] in ("ל", "ב", "מ", "ו", "כ", "ה") and clean[i + 1]["text"].startswith("-"):
        clean[i + 1]["text"] = clean[i]["text"] + clean[i + 1]["text"]
        clean[i + 1]["start_s"] = clean[i]["start_s"]
        clean[i]["text"] = ""
for i in range(len(clean) - 1):    # «2» «,000» → «2,000» — the transcriber splits a thousands group
    if re.match(r"^(?:[א-ת]-)?-?\d+$", clean[i]["text"] or "") and re.match(r"^,\d{3}\b", clean[i + 1]["text"] or ""):
        clean[i]["text"] += clean[i + 1]["text"]
        clean[i]["end_s"] = clean[i + 1]["end_s"]
        clean[i + 1]["text"] = ""
clean = [w for w in clean if w["text"]]
for w in clean:
    w["text"] = re.sub(r"^-\s*", "", w["text"])
clean = [w for w in clean if w["text"]]

# ⚠️ Not only under --range. build_audio() zero-pads every gap between FOOT
# windows (a title card between two reels leaves ~12s of pure silence sitting
# INSIDE the one buffer that gets transcribed whole) — and Whisper hallucinates
# into long silence instead of staying quiet. On «לקוח H רילס» this put
# «שלום אלוני היקר» — a stock phrase, not anything said — over two different
# white cards, at the same relative offset into each: the tell of a hallucination,
# not a transcription. Any word whose midpoint falls outside every FOOT window is
# fabricated by construction, --range or not.
_n0 = len(clean)
clean = [w for w in clean if clip_of((w["start_s"] + w["end_s"]) / 2) >= 0]
if len(clean) != _n0:
    print(f"הושמטו {_n0 - len(clean)} מילים שנפלו בשקט שבין חלונות הצילום (כרטיסים)")

TERMS = []
if A.terms:
    TERMS = [ln.split() for ln in open(A.terms).read().splitlines() if ln.strip()]
_bare = lambda t: PUNCT.sub("", t or "").strip()                       # noqa: E731
i = 0
while i < len(clean):                            # a term is one token from here on
    for term in sorted(TERMS, key=len, reverse=True):
        n = len(term)
        # ⚠️ Under --keep-punct the last word of a run often carries a comma or
        # period («כלל,»); matching the raw text against the term list missed
        # every one of those. Compare bare words, keep the real (punctuated)
        # text of the LAST word so the term still ends the sentence correctly.
        if [_bare(x["text"]) for x in clean[i:i + n]] == term:
            last_raw = clean[i + n - 1]["text"]
            clean[i]["text"] = " ".join(term[:-1] + [last_raw]) if n > 1 else last_raw
            clean[i]["end_s"] = clean[i + n - 1]["end_s"]
            del clean[i + 1:i + n]
            break
    i += 1

# ---------------------------------------------------------------- chunking
f100 = ImageFont.truetype(A.font, 100)
w100 = lambda t: f100.getbbox(t)[2] - f100.getbbox(t)[0]           # noqa: E731


def wrap_lines(text, limit):
    """Wrap to the fewest lines that each fit LIMIT.

    Two lines are common (any card wider than one line), and a greedy fill
    stuffs the first line to the wall and dumps whatever is left on the
    second — a card can end up 10 words over 1 — which reads as broken, not
    as two lines. Prefer the most BALANCED legal two-way split; fall back to
    greedy only when no two-way split fits (>2 lines needed, or one run of
    words has nowhere to break).
    """
    words = text.split()
    if w100(text) <= limit:
        return [text]
    best = None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        w1, w2 = w100(l1), w100(l2)
        if w1 <= limit and w2 <= limit:
            score = abs(w1 - w2)
            if best is None or score < best[0]:
                best = (score, [l1, l2])
    if best:
        return best[1]
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and w100(trial) > limit:
            lines.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines
donor = json.loads((capcut.DRAFTS_DIR / A.donor / "draft_info.json").read_text())
dtm = {m["id"]: m for m in donor["materials"]["texts"]}
dcap = (donor["tracks"][A.donor_track] if A.donor_track >= 0 else
        max((t for t in donor["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"])))
assert dcap["type"] == "text", "--donor-track is not a text track"
LIMIT = A.width_limit * max(
    w100(json.loads(dtm[s["material_id"]]["content"])["text"])
    for s in dcap["segments"]
    if "\n" not in json.loads(dtm[s["material_id"]]["content"])["text"])
print(f"תקרת רוחב מ«{A.donor}»: {LIMIT:.0f}")


# Where a card may break. The transcriber hands out touching word intervals, so
# "the gap between two words" is almost always 0 — the only honest signal is the
# energy actually dipping at the boundary. Breaking mid-phrase is what Alon reads
# as "חוסר דיוק בחלוקת המילים".
_MIX = m1 + m2
_HOP = 0.02
_ENV = np.array([float(np.sqrt((_MIX[int(i*_HOP*SR):int((i+1)*_HOP*SR)] ** 2).mean()))
                 for i in range(int(len(_MIX) / (_HOP * SR)))])
_DB = 20 * np.log10(np.maximum(_ENV, 1e-9))
_SPEECH = float(np.percentile(_DB[_DB > -60], 70)) if (_DB > -60).any() else -20.0


def dip(t0, t1):
    """0 = the speaker never stopped here, 1 = a real silence."""
    i = max(0, int((t0 - OFF - 0.05) / _HOP)); j = min(len(_DB), int((t1 - OFF + 0.05) / _HOP) + 1)
    if j <= i:
        return 0.0
    return float(np.clip((_SPEECH - _DB[i:j].min()) / 18.0, 0.0, 1.0))


# Words that lean on the next one (never end a card) or on the previous one
# (never start one). Hebrew has no morphological cue for this — it is a list.
LEAN_FWD = set("של את עם כמו אל על אצל בין כי אבל או גם רק כל מה יותר הכי לא כבר "
               "אני אתה הוא היא הם אתם אנחנו זה זאת אז שהוא שהיא שהם שאני חוץ וחוץ "
               "בשביל בגלל אחרי לפני מתוך תוך עוד איזה כזה כמה שתי שני מול נגד בלי".split())
LEAN_BACK = set("אותי אותו אותה אותם אותנו אתכם לי לו לה להם לנו לכם בי בו בה בהם "
                "שלי שלו שלה שלהם שלנו שלכם".split())


def wclip(w):
    """A word on a cut belongs to the side holding its own mic's energy."""
    a, b = w["start_s"], w["end_s"]
    ca, cb = clip_of(a), clip_of(max(a, b - 1e-6))
    if ca == cb:
        return ca
    if ca < 0 or cb < 0:
        return max(ca, cb)
    x = m1 if w["own"] == 1 else m2
    bnd = CLIPS[ca][1]
    return ca if energy(x, a, bnd) >= energy(x, bnd, b) else cb


SENT_END = re.compile(r"[.!?]$")
runs, cur = [], []
for w in clean:
    if cur and (w["own"] != cur[-1]["own"] or wclip(w) != wclip(cur[0])
                or w["start_s"] - cur[-1]["end_s"] > A.max_gap
                or (A.split_sentences and SENT_END.search(cur[-1]["text"]))):
        runs.append(cur)
        cur = []
    cur.append(w)
if cur:
    runs.append(cur)


def weigh(tok):
    return len(tok["text"].split())


def cards(run):
    """Cheapest partition, cost (max_words − words)² — 2+2 beats 3+1."""
    n, INF = len(run), float("inf")
    best = [INF] * (n + 1); back = [0] * (n + 1); best[0] = 0
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            g = run[i:j]
            if sum(weigh(x) for x in g) > A.max_words:
                break
            if len(wrap_lines(" ".join(x["text"] for x in g), LIMIT)) > A.max_lines:
                break
            if g[-1]["end_s"] - g[0]["start_s"] > A.max_dur:
                break
            c = best[i] + (A.max_words - sum(weigh(x) for x in g)) ** 2
            if j < n:
                c += 20.0 * (1.0 - dip(g[-1]["end_s"], run[j]["start_s"]))
                if g[-1]["text"] in LEAN_FWD: c += 12.0
                if run[j]["text"] in LEAN_BACK: c += 12.0
            if i > 0 and g[0]["text"] in LEAN_BACK: c += 12.0
            if g[-1]["end_s"] - g[0]["start_s"] < 0.40: c += 8.0
            if c < best[j]:
                best[j] = c; back[j] = i
    if best[n] == INF:
        return [[x] for x in run]
    groups, j = [], n
    while j > 0:
        groups.append(run[back[j]:j]); j = back[j]
    return groups[::-1]


out = []
for run in (g for r in runs for g in cards(r)):
    t = "\n".join(wrap_lines(" ".join(x["text"] for x in run).strip(), LIMIT))
    a_ = run[0]["start_s"]; b_ = max(run[-1]["end_s"], a_ + 0.35)
    ci = wclip(run[0])
    if ci < 0:                            # a title card is not footage — no words live there
        continue
    a_ = max(a_, CLIPS[ci][0]); b_ = min(max(b_, a_ + 0.35), CLIPS[ci][1])
    if b_ - a_ < 0.30:                    # sliced off by a cut — drop the word, not the take
        continue
    out.append({"text": t, "start": a_, "end": b_, "own": run[0]["own"],
                "ws": run[0]["start_s"], "we": run[-1]["end_s"],
                "words": [{"text": x["text"], "start_ms": int((x["start_s"] - a_) * 1000),
                           "end_ms": int((x["end_s"] - a_) * 1000)} for x in run]})
out.sort(key=lambda c: c["start"])
for a, b in zip(out, out[1:]):
    if a["end"] > b["start"]:
        a["end"] = b["start"]
for i, c in enumerate(out):                       # gap-free inside a clip
    ci = clip_of(c["start"])
    nxt = out[i + 1] if i + 1 < len(out) else None
    if nxt is not None and clip_of(nxt["start"]) == ci and nxt["start"] - c["end"] < 1.1:
        c["end"] = nxt["start"]
    elif ci >= 0:
        c["end"] = min(CLIPS[ci][1], c["end"] + 0.9)
pulled = 0
for i, c in enumerate(out):                       # first card of a clip starts with it
    ci = clip_of(c["start"])
    if ci < 0 or (i > 0 and clip_of(out[i - 1]["start"]) == ci):
        continue
    dt = c["start"] - CLIPS[ci][0]
    if 0 < dt <= 1.2:
        for w in c["words"]:
            w["start_ms"] += int(dt * 1000); w["end_ms"] += int(dt * 1000)
        c["start"] = CLIPS[ci][0]; pulled += 1

# Frame grid: snap both edges, then make every card end exactly where the next
# begins. Raw microsecond times survive the injection and then CapCut rounds each
# segment on its own — start up, previous end down — and a one-frame hole opens
# between cards. On a 60fps project that reads as the captions flickering.
for c in out:
    c["si"] = snap(c["start"]); c["ei"] = snap(c["end"])
for i, c in enumerate(out):
    nxt = out[i + 1] if i + 1 < len(out) else None
    if nxt and clip_of(nxt["start"]) == clip_of(c["start"]) and abs(nxt["si"] - c["ei"]) <= FR * 1.5:
        c["ei"] = nxt["si"]
for a, b in zip(out, out[1:]):
    if a["ei"] > b["si"]: a["ei"] = b["si"]

# The floor, and it has to come last. A card's life is set by the *next* card,
# so lengthening one in isolation is undone by the very next overlap clamp —
# which is exactly what happened here: the minimum was written, then clipped
# straight back off, and 8% of the cards shipped under half a second. A card can
# only get longer by taking the time from a neighbour or by merging into one.
FLOOR = int(np.ceil(A.min_dur * US / FR) * FR)      # whole frames, or it lands one short
DROP = int(FLOOR // 2)
same_clip = lambda a, b: clip_of(a["start"]) == clip_of(b["start"])         # noqa: E731


def fuse(host, other):
    """other's words join host's card; host keeps its own colour and start."""
    first, second = (host, other) if host["si"] <= other["si"] else (other, host)
    dt = int((first["si"] - host["si"]) / 1000), int((second["si"] - host["si"]) / 1000)
    host["words"] = ([{**w, "start_ms": w["start_ms"] + dt[0],
                       "end_ms": w["end_ms"] + dt[0]} for w in first["words"]] +
                     [{**w, "start_ms": w["start_ms"] + dt[1],
                       "end_ms": w["end_ms"] + dt[1]} for w in second["words"]])
    flat = f"{first['text']} {second['text']}".replace("\n", " ").strip()
    host["text"] = "\n".join(wrap_lines(flat, LIMIT))
    host["si"] = min(host["si"], other["si"]); host["ei"] = max(host["ei"], other["ei"])
    host["ws"] = min(host["ws"], other["ws"]); host["we"] = max(host["we"], other["we"])
    for w in host["words"]:
        w["start_ms"] = max(0, w["start_ms"]); w["end_ms"] = max(w["start_ms"], w["end_ms"])


merged = dropped = borrowed = 0
i = 0
while i < len(out):
    c = out[i]
    if c["ei"] - c["si"] >= FLOOR:
        i += 1
        continue
    p = out[i - 1] if i > 0 and same_clip(out[i - 1], c) else None
    n = out[i + 1] if i + 1 < len(out) and same_clip(out[i + 1], c) else None
    need = FLOOR - (c["ei"] - c["si"])
    # Borrow first, merge second. Merging is the stronger move but it can glue a
    # card across a pause, and a card holding a 1.3s silence is the same defect
    # in the other direction. The next card donates before the previous one: a
    # caption may lead its words a little, it may not trail them.
    for lender, sign in ((n, +1), (p, -1)):
        if not need or lender is None:
            continue
        # in frames, not microseconds: the grid is 33333.33µs, so a need of
        # exactly one frame floor-divides to zero and the card gets merged
        # instead of topped up by the frame it was missing
        take = min(int(round(need / FR)),
                   int(round(((lender["ei"] - lender["si"]) - FLOOR) / FR)))
        if take <= 0:
            continue
        slack = int(round(take * FR))
        if sign > 0:
            lender["si"] += slack; c["ei"] += slack
        else:
            lender["ei"] -= slack; c["si"] -= slack
            for w in c["words"]:
                w["start_ms"] += int(slack / 1000); w["end_ms"] += int(slack / 1000)
        need -= slack; borrowed += 1
    if c["ei"] - c["si"] < FLOOR:           # nobody had time to give — join a neighbour
        for nb, gap in ((p, c["ws"] - p["we"] if p else 9),
                        (n, n["ws"] - c["we"] if n else 9)):
            if (nb and nb["own"] == c["own"] and gap <= A.max_gap
                    and len(wrap_lines(f"{nb['text']} {c['text']}".replace(chr(10), ' '), LIMIT))
                    <= A.max_lines):
                fuse(nb, c); out.pop(i); merged += 1
                break
        else:
            if c["ei"] - c["si"] >= DROP:
                i += 1
            else:
                out.pop(i); dropped += 1
                if i and i < len(out) and same_clip(out[i - 1], out[i]):
                    out[i - 1]["ei"] = out[i]["si"]
        continue
    i += 1
print(f"רצפת אורך {A.min_dur:.2f}s: {merged} מוזגו | {borrowed} שאלו זמן | {dropped} הוסרו")

short = sum(1 for c in out if c["ei"] - c["si"] < FLOOR - 1)
if short:
    print(f"✗ עדיין {short} כתוביות מתחת ל-{A.min_dur:.2f}s")
yellow = sum(1 for c in out if c["own"] == 1)
gaps = sum(1 for a, b in zip(out, out[1:]) if b["si"] - a["ei"] > 1e-6)
inner = max((b["start_ms"] - a["end_ms"]) / 1000
            for c in out for a, b in zip(c["words"], c["words"][1:])) if len(out) > 1 else 0
lens = sorted((c["ei"] - c["si"]) / US for c in out)
print(f"אורך כתובית: מינימום {lens[0]:.2f}s | חציון {lens[len(lens)//2]:.2f}s")
print(f"{len(out)} כתוביות | צהוב {yellow} | לבן {len(out)-yellow} | מרווחים {gaps} | "
      f"נמתחו לתחילת קליפ {pulled} | פער פנימי מקסימלי {inner:.2f}s")
_line_w = lambda c: max(w100(ln) for ln in c["text"].split("\n"))          # noqa: E731
print("הכי רחבה:", max(out, key=_line_w)["text"].replace("\n", " / "))
json.dump(out, open(CACHE + "-caps.json", "w"), ensure_ascii=False)
for c in out[:10]:
    print(f"  {c['start']:6.2f}-{c['end']:6.2f} [{'צ' if c['own']==1 else 'ל'}] {c['text']}")
if not A.write:
    print("(יבש — בלי --write לא נכתב כלום)")
    sys.exit()

# ---------------------------------------------------------------- inject
pid = capcut._capcut_pid()
if pid and f"{DST}/" in capcut._capcut_open_files(pid):
    sys.exit("✗ CapCut מחזיק את הפרויקט — לסגור ולהריץ שוב")


def _shape(m):
    """What actually decides how a caption renders, as one comparable key."""
    st = json.loads(m["content"])["styles"][0]
    return (
        (st.get("effectStyle") or {}).get("id"),
        bool(st.get("useLetterColor")),
        round(float(m.get("border_width") or 0), 4),
        (m.get("background_color") or ""),
        bool(json.loads(m["content"]).get("styles", [{}])[0].get("strokes")),
        bool(json.loads(m["content"]).get("styles", [{}])[0].get("shadows")),
    )


def donor_styles():
    """One prototype per colour from the donor's caption track.

    ⚠️ Take the **modal** material for each colour, never "whichever segment came
    last". On «פרויקט-דוגמה N רילס» exactly one of 262 captions carries no text
    effect, and it happened to be the last white one — so every caption I
    injected into 0830 came out with no house effect, a black `background_color`
    box behind the text, `border_width` 0.036 instead of 0.08, and `strokes`/
    `shadows` written into `content`. Alon saw it in the first frame.

    With a text effect applied the effect OWNS the outline and the shadow;
    injecting strokes/shadows beside it is the thing that must never happen.
    """
    by = {}
    for s in dcap["segments"]:
        m = dtm[s["material_id"]]
        col = tuple(json.loads(m["content"])["styles"][0]["fill"]["content"]["solid"]["color"])
        b = by.setdefault(col, {"by_shape": {}, "n": 0})
        b["n"] += 1
        sh = b["by_shape"].setdefault(_shape(m), {"mat": m, "seg": s, "n": 0})
        sh["n"] += 1
    for col, b in by.items():
        best = max(b["by_shape"].values(), key=lambda v: v["n"])
        b["mat"], b["seg"] = best["mat"], best["seg"]
        odd = b["n"] - best["n"]
        if odd:
            print(f"  ⚠️ בצבע {col}: {odd} מתוך {b['n']} כתוביות בתורם בסגנון חורג — "
                  f"נלקח הרוב ({best['n']})")
    top = sorted(by.items(), key=lambda kv: -kv[1]["n"])[:2]
    warm = [kv for kv in top if kv[0][2] < 0.3]
    cool = [kv for kv in top if kv[0][2] >= 0.3]
    if A.all_white and cool:
        return cool[0][1], cool[0][1]
    if not warm or not cool:
        sys.exit("✗ לא נמצאו שני צבעי כתובית בפרויקט התורם")
    return warm[0][1], cool[0][1]


yel_src, wht_src = donor_styles()
# The prototype is the whole deliverable's look — print it, and refuse a
# prototype that contradicts itself (effect present AND strokes injected).
for _lbl, _src in (("צהוב", yel_src), ("לבן", wht_src)):
    _eff, _ulc, _bw, _bg, _stk, _shd = _shape(_src["mat"])
    print(f"  סגנון תורם {_lbl}: אפקט {_eff} · useLetterColor {_ulc} · "
          f"border {_bw} · background {_bg or 'ריק'} · strokes {_stk} · shadows {_shd}")
    if _eff and (_stk or _shd):
        sys.exit(f"✗ תורם {_lbl} סותר את עצמו: יש אפקט טקסט וגם strokes/shadows "
                 "ב-content. האפקט הוא הבעלים — לבחור תורם אחר.")
    if _eff and _bg:
        sys.exit(f"✗ תורם {_lbl} נושא background_color «{_bg}» ליד אפקט — "
                 "זו הקופסה השחורה שאלון פסל.")
shutil.copy2(DST / "draft_info.json", DST / "draft_info.json.precaps-backup")
before = json.loads((DST / "draft_info.json").read_text())      # live state, re-read
d = json.loads(json.dumps(before))
olds = [t for t in d["tracks"] if t.get("name") == A.track_name]
if olds and not A.add:
    if not A.replace:
        sys.exit("✗ כבר יש טראק כתוביות — להריץ עם --replace")
    kill = {s["material_id"] for t in olds for s in t["segments"]}
    kill |= {r for t in olds for s in t["segments"] for r in s.get("extra_material_refs", [])}
    d["tracks"] = [t for t in d["tracks"] if t.get("name") != A.track_name]
    for b, v in list(d["materials"].items()):
        if isinstance(v, list):
            d["materials"][b] = [m for m in v if not (isinstance(m, dict) and m.get("id") in kill)]
    print(f"הוסר טראק כתוביות קודם ({sum(len(t['segments']) for t in olds)} כתוביות)")

didx = capcut._materials_index(donor)
segs = []
for c in out:
    src = yel_src if c["own"] == 1 else wht_src
    m = copy.deepcopy(src["mat"]); m["id"] = capcut._new_id()
    a0 = c["si"] / US
    capcut._set_text(m, c["text"], [{**w,
                                     "start_ms": w["start_ms"] + int((c["start"] - a0) * 1000),
                                     "end_ms": w["end_ms"] + int((c["start"] - a0) * 1000)}
                                    for w in c["words"]])
    if A.cap_size:
        m["font_size"] = A.cap_size
        for field in ("content", "base_content"):
            if m.get(field):
                p = json.loads(m[field])
                for st in p.get("styles", []):
                    st["size"] = A.cap_size
                m[field] = json.dumps(p, ensure_ascii=False)
    # ⚠️ `fixed_width` is a cached, ABSOLUTE-pixel box width carried verbatim from
    # the donor's own canvas/font_size — it does not rescale for a different
    # canvas or a longer line. Left alone, CapCut re-wraps INSIDE our own `\n`
    # lines against that stale, too-narrow box, splitting a word mid-way («בד» /
    # «רך») — the very thing wrap_lines() exists to prevent. Recompute it from
    # the actual widest rendered line so CapCut's own wrap never has a reason to
    # fire. PX_PER_SIZE_UNIT is the CapCut font_size → PIL point-size calibration
    # for this font (references/capcut-json.md: ascent+descent/1920 == 0.046 at
    # font_size 20, on this bamberger-grunge-bold-fm.ttf).
    if m.get("fixed_width", -1) not in (None, -1):
        PX_PER_SIZE_UNIT = 4.416
        px_scale = (A.cap_size or m.get("font_size") or 20) * PX_PER_SIZE_UNIT / 100
        widest_px = max(w100(ln) for ln in c["text"].split("\n")) * px_scale
        m["fixed_width"] = round(widest_px * 1.25 + 40, 1)
    if A.shadow_white and c["own"] == 2:
        m.update(has_shadow=True, shadow_color="#000000", shadow_alpha=0.9,
                 shadow_distance=7.0, shadow_smoothing=0.45, shadow_angle=-45.0,
                 shadow_point={"x": 0.6363961030678928, "y": -0.6363961030678927},
                 border_width=max(m.get("border_width", 0.08), 0.10))
    d["materials"]["texts"].append(m)
    s = copy.deepcopy(src["seg"]); s["id"] = capcut._new_id(); s["material_id"] = m["id"]
    refs = []
    for r in src["seg"].get("extra_material_refs", []):
        if r in didx:
            b, mm = didx[r]
            cc = copy.deepcopy(mm); cc["id"] = capcut._new_id()
            d["materials"].setdefault(b, []).append(cc); refs.append(cc["id"])
    s["extra_material_refs"] = refs
    s["common_keyframes"] = []; s["keyframe_refs"] = []
    s["target_timerange"] = {"start": c["si"], "duration": c["ei"] - c["si"]}
    s["source_timerange"] = None
    s["clip"]["transform"] = {"x": 0.0, "y": A.cap_y}
    segs.append(s)

# His segments keep the render indices CapCut gave them — only the new track is
# renumbered. Tidying 1,2,3 into 0,1,2 is a silent edit to somebody else's cut.
keep = [t for t in d["tracks"] if t.get("name") != A.track_name or A.add]
mx = max(s.get("render_index", 0) for t in keep for s in t["segments"])
for s in segs:
    s["render_index"] = mx + 1
    s["track_render_index"] = len(keep)
d["tracks"].append({**{k: v for k, v in dcap.items() if k != "segments"},
                    "id": capcut._new_id(), "name": A.track_name,
                    "is_default_name": False, "segments": segs})

tmp = DST / "draft_info.json.tmp"
tmp.write_text(json.dumps(d, ensure_ascii=False))
json.loads(tmp.read_text())
tmp.replace(DST / "draft_info.json")

after = json.loads((DST / "draft_info.json").read_text())
untouched = all(json.dumps(a, sort_keys=True, ensure_ascii=False) ==
                json.dumps(b, sort_keys=True, ensure_ascii=False)
                for a, b in zip([t for t in before["tracks"] if t.get("name") != "כתוביות"],
                                [t for t in after["tracks"] if t.get("name") != "כתוביות"]))
print(f"✓ {len(segs)} כתוביות הוזרקו | שאר הטראקים ללא שינוי: {untouched}")
if not untouched:
    print("✗ טראק שלא היה אמור להשתנות — השתנה. לשחזר מ-draft_info.json.precaps-backup")
