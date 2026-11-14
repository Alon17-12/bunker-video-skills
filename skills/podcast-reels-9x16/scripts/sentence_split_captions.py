"""Sentence-aware captions (born on 0910): never let a card run across a sentence end, and keep the
question/exclamation mark on the card that asks it. Periods and commas stay off-screen
(house style). Splits use the word timings from the Whisper cache; card text is the
QA-corrected text already in the draft (the cache still has the raw ASR words)."""
import os
import sys, json, copy, re, difflib
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
if len(sys.argv) < 3: raise SystemExit("usage: sentence_split_captions.py <project> <words.json>")
NAME = sys.argv[1]; WORDS = sys.argv[2]; US = 1_000_000; MIN_CARD = 0.30
pid = capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if capcut.capcut_running(): raise SystemExit("CapCut running")
d = capcut.load_draft(NAME); tm = {m["id"]: m for m in d["materials"]["texts"]}
tt = max((t for t in d["tracks"] if t["type"] == "text"), key=lambda t: len(t["segments"])); ws = json.load(open(WORDS))   # the caption track = the largest text track (0923: the first text track was the titles)
norm = lambda t: re.sub(r"[^\w]", "", t.replace("־", "")).lower()
def text_of(seg): return json.loads(tm[seg["material_id"]]["content"])["text"]
def set_text(mat, txt):
    c = json.loads(mat["content"]); c["text"] = txt
    for st in c["styles"]: st["range"] = [0, len(txt)]
    mat["content"] = json.dumps(c, ensure_ascii=False)
    toks = txt.split(" "); n = sum(len(t) for t in toks) or 1; dur_ms = None
    mat["_toks"] = toks  # filled below once the duration is known
def set_words(mat, seg):
    toks = mat.pop("_toks", None) or json.loads(mat["content"])["text"].split(" ")
    dur = seg["target_timerange"]["duration"] / 1000; n = sum(len(t) for t in toks) or 1
    st, en, tx, t = [], [], [], 0.0
    for i, tok in enumerate(toks):
        w = dur * len(tok) / n; st.append(int(t)); en.append(int(t + w)); tx.append(tok); t += w
        if i < len(toks) - 1: st.append(int(t)); en.append(int(t)); tx.append(" ")
    mat["words"] = {"start_time": st, "end_time": en, "text": tx}
segs = sorted(tt["segments"], key=lambda s: s["target_timerange"]["start"])
split_n = q_n = merged = skipped = 0; out = []
i = 0
while i < len(segs):
    s = segs[i]; st, en = s["target_timerange"]["start"]/US, (s["target_timerange"]["start"]+s["target_timerange"]["duration"])/US
    mat = tm[s["material_id"]]; c = json.loads(mat["content"]); txt = c["text"].replace("\n", " ")
    toks = txt.split(" ")
    inside = [w for w in ws if st - 0.02 <= (w["start_s"]+w["end_s"])/2 < en + 0.02]
    ends = [w for w in inside if w["text"][-1:] in ".?!"]
    if not ends or len(c["styles"]) > 1:
        if len(c["styles"]) > 1 and ends: skipped += 1
        out.append(s); i += 1; continue
    # align whisper words → card tokens
    a = [norm(w["text"]) for w in inside]; b = [norm(t) for t in toks]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False); w2t = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): w2t[blk.a + k] = blk.b + k
    def tok_index(wi):
        if wi in w2t: return w2t[wi]
        prev = [k for k in w2t if k < wi]
        return (w2t[max(prev)] + (wi - max(prev))) if prev else wi
    cur_seg, cur_mat, cur_toks, cur_st = s, mat, toks, st
    for w in ends:
        wi = inside.index(w); ti = tok_index(wi)
        if ti >= len(cur_toks): ti = len(cur_toks) - 1
        mark = w["text"][-1] if w["text"][-1] in "?!" else ""
        if ti == len(cur_toks) - 1:            # sentence ends where the card ends — just the mark
            if mark and not cur_toks[-1].endswith(mark): cur_toks[-1] += mark; q_n += 1
            continue
        nxt = next((x for x in ws if x["start_s"] >= w["end_s"] - 0.01 and x is not w), None)
        t_split = min(w["end_s"] + 0.04, (w["end_s"] + nxt["start_s"]) / 2 if nxt else w["end_s"] + 0.04)
        t_split = max(cur_st + MIN_CARD, min(t_split, en - MIN_CARD))
        if t_split - cur_st < MIN_CARD or en - t_split < MIN_CARD:
            # no room for a second card: keep the mark, skip the split
            if mark and not cur_toks[ti].endswith(mark): cur_toks[ti] += mark; q_n += 1
            continue
        part1 = cur_toks[:ti+1]; part2 = cur_toks[ti+1:]
        if mark and not part1[-1].endswith(mark): part1[-1] += mark; q_n += 1
        # first half keeps the material; second half is a fresh clone
        cur_seg["target_timerange"]["duration"] = int(t_split*US) - cur_seg["target_timerange"]["start"]
        cur_seg["source_timerange"] = {"start": 0, "duration": cur_seg["target_timerange"]["duration"]}
        set_text(cur_mat, " ".join(part1)); set_words(cur_mat, cur_seg)
        m2 = copy.deepcopy(cur_mat); m2["id"] = capcut._new_id(); d["materials"]["texts"].append(m2); tm[m2["id"]] = m2
        s2 = copy.deepcopy(cur_seg); s2["id"] = capcut._new_id(); s2["material_id"] = m2["id"]
        s2["target_timerange"] = {"start": int(t_split*US), "duration": int(en*US) - int(t_split*US)}
        s2["source_timerange"] = {"start": 0, "duration": s2["target_timerange"]["duration"]}
        set_text(m2, " ".join(part2)); set_words(m2, s2)
        out.append(cur_seg); split_n += 1
        cur_seg, cur_mat, cur_toks, cur_st = s2, m2, part2, t_split
        # re-index tokens for the remainder
        w2t = {k: v - (ti+1) for k, v in w2t.items() if v > ti}
    if cur_seg is s:
        set_text(mat, " ".join(cur_toks)); set_words(mat, s)
    else:
        set_text(cur_mat, " ".join(cur_toks)); set_words(cur_mat, cur_seg)
    out.append(cur_seg); i += 1
tt["segments"] = sorted(out, key=lambda s: s["target_timerange"]["start"])
# integrity
ov = [(a["target_timerange"]["start"]/US) for a, b in zip(tt["segments"], tt["segments"][1:]) if a["target_timerange"]["start"]+a["target_timerange"]["duration"] > b["target_timerange"]["start"]+1]
short = [s["target_timerange"]["duration"]/US for s in tt["segments"] if s["target_timerange"]["duration"] < MIN_CARD*US - 1]
print(f"cards {len(segs)} → {len(tt['segments'])} | splits {split_n} | marks added {q_n} | mixed-font cards skipped {skipped} | overlaps {len(ov)} | short {short}")
for s in tt["segments"][:6]: print(f"   {s['target_timerange']['start']/US:6.2f}  {text_of(s)}")
qs = [(round(s['target_timerange']['start']/US,2), text_of(s)) for s in tt["segments"] if "?" in text_of(s)]
print("question cards:", qs)
capcut._backup(capcut.DRAFTS_DIR/NAME); capcut._atomic_write(capcut.DRAFTS_DIR/NAME, d); print("written")
