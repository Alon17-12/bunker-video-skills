"""0910 — no wrapped lines: split any card wider than the wrap threshold CapCut showed
(«סטארט אפ ישראלי חושף» wrapped at ~385px@60 in PIL units) on the last word's start time,
and set fixed_width=-1 (auto box, the convention in his own subtitle materials)."""
import os
import sys, json, copy
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
from PIL import ImageFont
NAME = "0910"; US = 1_000_000; LIMIT = 385; MIN = 0.30
WORDS = json.load(open(os.path.expanduser("~/Movies/reel-captions-work/0910-words.json")))
pid = capcut._capcut_pid()
if pid and f"{capcut.DRAFTS_DIR/NAME}/" in capcut._capcut_open_files(pid): raise SystemExit("draft open in CapCut")
if capcut.capcut_running(): raise SystemExit("CapCut running")
d = capcut.load_draft(NAME); tm = {m["id"]: m for m in d["materials"]["texts"]}
tt = next(t for t in d["tracks"] if t["type"] == "text"); segs = sorted(tt["segments"], key=lambda s: s["target_timerange"]["start"])
def width(c):
    w = 0
    for st in c["styles"]:
        f = ImageFont.truetype(st["font"]["path"], int(60*st["size"]/20)); a, b = st["range"]; w += f.getlength(c["text"][a:b])
    return w
def set_text(m, txt):
    c = json.loads(m["content"]); c["text"] = txt
    for st in c["styles"]: st["range"] = [0, len(txt)]
    m["content"] = json.dumps(c, ensure_ascii=False)
def set_words(m, seg):
    toks = json.loads(m["content"])["text"].split(" "); dur = seg["target_timerange"]["duration"]/1000; n = sum(len(t) for t in toks) or 1
    st, en, tx, t = [], [], [], 0.0
    for i, tok in enumerate(toks):
        w = dur*len(tok)/n; st.append(int(t)); en.append(int(t+w)); tx.append(tok); t += w
        if i < len(toks)-1: st.append(int(t)); en.append(int(t)); tx.append(" ")
    m["words"] = {"start_time": st, "end_time": en, "text": tx}
out = []; n_split = 0
for s in segs:
    m = tm[s["material_id"]]; m["fixed_width"] = -1.0; c = json.loads(m["content"]); toks = c["text"].split(" ")
    if width(c) <= LIMIT or len(toks) < 2 or len(c["styles"]) > 1: out.append(s); continue
    st, en = s["target_timerange"]["start"]/US, (s["target_timerange"]["start"]+s["target_timerange"]["duration"])/US
    # split before the last word (or before the last two if still too wide), at that word's start time from the cache
    k = len(toks) - 1
    while k > 1 and width({"text": " ".join(toks[:k]), "styles": [dict(c["styles"][0], range=[0, len(" ".join(toks[:k]))])]}) > LIMIT: k -= 1
    inside = [w for w in WORDS if st - 0.02 <= (w["start_s"]+w["end_s"])/2 < en + 0.02]
    t_split = inside[k]["start_s"] - 0.03 if len(inside) == len(toks) else st + (en-st)*k/len(toks)
    t_split = max(st + MIN, min(t_split, en - MIN))
    if en - t_split < MIN or t_split - st < MIN: out.append(s); continue
    s["target_timerange"]["duration"] = int(t_split*US) - s["target_timerange"]["start"]; s["source_timerange"] = {"start": 0, "duration": s["target_timerange"]["duration"]}
    set_text(m, " ".join(toks[:k])); set_words(m, s)
    m2 = copy.deepcopy(m); m2["id"] = capcut._new_id(); d["materials"]["texts"].append(m2)
    s2 = copy.deepcopy(s); s2["id"] = capcut._new_id(); s2["material_id"] = m2["id"]
    s2["target_timerange"] = {"start": int(t_split*US), "duration": int(en*US) - int(t_split*US)}; s2["source_timerange"] = {"start": 0, "duration": s2["target_timerange"]["duration"]}
    set_text(m2, " ".join(toks[k:])); set_words(m2, s2)
    out += [s, s2]; n_split += 1
    print(f"  split {st:7.2f}: «{' '.join(toks[:k])}» | «{' '.join(toks[k:])}» @ {t_split:.2f}")
tt["segments"] = sorted(out, key=lambda s: s["target_timerange"]["start"])
ov = sum(1 for a, b in zip(tt["segments"], tt["segments"][1:]) if a["target_timerange"]["start"]+a["target_timerange"]["duration"] > b["target_timerange"]["start"]+1)
print(f"cards {len(segs)} → {len(tt['segments'])} | splits {n_split} | overlaps {ov} | fixed_width=-1 on all")
capcut._backup(capcut.DRAFTS_DIR/NAME); capcut._atomic_write(capcut.DRAFTS_DIR/NAME, d); print("written")
