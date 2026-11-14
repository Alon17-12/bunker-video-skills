#!/usr/bin/env python3
"""Caption hygiene on a finished project (25.10.2026): no two visible captions at once, none over a separator card, none on
screen for under 0.25 s (it joins its neighbour of the same speaker colour; a split continuation of the same text just
merges). Hidden (alpha 0) parts under designed texts are left alone.

    caption_tidy.py "<project>" [--write]
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

name = sys.argv[1]; P = capcut.DRAFTS_DIR / name; d = json.loads(capcut._draft_file(P).read_text())
tm = {m["id"]: m for m in d["materials"]["texts"]}; vids = {m["id"]: m for m in d["materials"]["videos"]}
st = lambda s: s["target_timerange"]["start"]; en = lambda s: st(s) + s["target_timerange"]["duration"]
ct = lambda s: json.loads(tm[s["material_id"]]["content"])
col = lambda s: json.dumps(ct(s)["styles"][0].get("fill")) if ct(s)["styles"] else ""
tall = d["canvas_config"]["height"] > d["canvas_config"]["width"]
base = next(t for t in d["tracks"] if t["type"] == "video" and not t.get("name")) if tall else d["tracks"][0]
photos = [(st(s), en(s)) for s in base["segments"] if vids.get(s["material_id"], {}).get("type") == "photo"]
log = []
def join(a, b, a_first):
    """text of b goes into a (before or after), styles kept"""
    A, Bc = ct(a), ct(b)
    ta, tb = A["text"].replace("\n", " "), Bc["text"].replace("\n", " ")
    if ta.strip() == tb.strip():
        text, sty = A["text"], A["styles"]
    else:
        first, second = (A, Bc) if a_first else (Bc, A)
        t1, t2 = first["text"].replace("\n", " "), second["text"].replace("\n", " ")
        text = t1 + " " + t2
        sty = [dict(e) for e in first["styles"]]; sty[-1] = dict(sty[-1], range=[sty[-1]["range"][0], sty[-1]["range"][1] + 1])
        sty += [dict(e, range=[e["range"][0] + len(t1) + 1, e["range"][1] + len(t1) + 1]) for e in second["styles"]]
        if len(text) > 18 and ("\n" in A["text"] or "\n" in Bc["text"]):
            sp = [i for i, ch in enumerate(text) if ch == " "]
            k = min(sp, key=lambda i: abs(i - len(text) / 2)); text = text[:k] + "\n" + text[k + 1:]
    A["text"] = text; A["styles"] = sty; tm[a["material_id"]]["content"] = json.dumps(A, ensure_ascii=False)
    s0, e0 = min(st(a), st(b)), max(en(a), en(b)); a["target_timerange"] = {"start": s0, "duration": e0 - s0}
for tr in d["tracks"]:
    if tr["type"] != "text" or not (tr.get("name") or "").startswith("כתוביות"):
        continue
    changed = True
    while changed:
        changed = False
        vis = sorted([s for s in tr["segments"] if s["clip"]["alpha"] > 0.5], key=st)
        for i, s in enumerate(vis):
            if en(s) - st(s) >= 250_000:
                continue
            prv = vis[i - 1] if i and st(s) - en(vis[i - 1]) < 100_000 and col(vis[i - 1]) == col(s) else None
            nxt = vis[i + 1] if i + 1 < len(vis) and st(vis[i + 1]) - en(s) < 100_000 and col(vis[i + 1]) == col(s) else None
            if prv is not None and any(p0 <= en(prv) - 1 < p1 or p0 < st(s) + 1 <= p1 for p0, p1 in photos):
                prv = None
            if en(s) - st(s) < 100_000:                  # a sliver of a word the cut left behind — gone, not merged
                log.append(f"{st(s)/1e6:7.2f} «{ct(s)['text']}» ({(en(s)-st(s))/1e6:.2f}) — נמחקה"); tr["segments"].remove(s); changed = True; break
            if prv is not None and re.search(r"[.?!]$", ct(prv)["text"].strip()):
                prv = None                                 # sentences never share a card
            tgt = prv if prv is not None and len(ct(prv)["text"]) + len(ct(s)["text"]) <= 34 else nxt if nxt is not None and len(ct(nxt)["text"]) + len(ct(s)["text"]) <= 34 else prv or nxt
            if tgt is None:
                continue
            log.append(f"{st(s)/1e6:7.2f} «{ct(s)['text']}» ({(en(s)-st(s))/1e6:.2f}) → «{ct(tgt)['text']}»")
            join(tgt, s, tgt is prv); tr["segments"].remove(s); changed = True; break
    vis = sorted([s for s in tr["segments"] if s["clip"]["alpha"] > 0.5], key=st)
    for a, b in zip(vis, vis[1:]):
        if en(a) > st(b):
            log.append(f"{st(b)/1e6:7.2f} חפיפה «{ct(a)['text']}» / «{ct(b)['text']}» — קוצר"); a["target_timerange"]["duration"] = st(b) - st(a)
    for s in vis:
        for p0, p1 in photos:
            if st(s) < p0 < en(s):
                log.append(f"{st(s)/1e6:7.2f} «{ct(s)['text']}» נכנסה לכרטיס — קוצרה"); s["target_timerange"]["duration"] = p0 - st(s)
            elif st(s) < p1 < en(s) and st(s) >= p0:
                log.append(f"{st(s)/1e6:7.2f} «{ct(s)['text']}» התחילה על כרטיס — הוזזה"); s["target_timerange"] = {"start": p1, "duration": en(s) - p1}
for x in log:
    print(x)
print(f"{len(log)} תיקונים")
if "--write" in sys.argv and log:
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח")
    capcut._backup(P); capcut._atomic_write(P, d); print("✓ נכתב")
