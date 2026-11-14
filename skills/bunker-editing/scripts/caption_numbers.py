#!/usr/bin/env python3
"""Numbers in captions, written the way they are read (25.10.2026, Alon: «במקומות שרשום בהם 1,500 וכו זה יוצא שבור»).

The transcript splits a number at its thousands comma («1» «,600», «-100» «,000»), so a card reads «1 ,600» — and in a
right-to-left line CapCut lays the two runs out as «600, 1». This joins them:
  • inside a card:   «1 ,600» / «1⏎,100» → «1,600» / «1,100»;  «מ -24» → «מ-24»
  • across two cards: a card ending in digits + the next starting «,000» → the «,000» moves to the first card
    (same speaker colour, same visibility); an emptied card is removed and its time goes to the first.

    caption_numbers.py "<project>" [--write]          CapCut must be closed for --write.
"""
import argparse, copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

INSIDE = [(re.compile(r"(\d)\s*\n?\s*,(\d{3})"), r"\1,\2"),             # «1 ,600» → «1,600»
          (re.compile(r"(?<![\d,])(\d{1,3}) (\d{3})(?!\d)"), r"\1,\2"),      # «1 500» (16:9 cards lost the comma) → «1,500»
          (re.compile(r"(^|\s)([מבלהוש])\s+-(\d)"), r"\1\2-\3"),              # «מ -24» → «מ-24»
          (re.compile(r"(^|\s)(\d+)\.?\s+\2(?=[.\s]|$)"), r"\1\2")]               # «2. 2. לקוח M» (said twice as a correction) → «2. לקוח M»


def restyle(old_text, new_text, styles):
    """map each style range through the edit (both strings differ only by removed whitespace) — char by char"""
    i = j = 0; mp = {}
    while i < len(old_text):
        if j < len(new_text) and old_text[i] == new_text[j]:
            mp[i] = j; i += 1; j += 1
        else:
            mp[i] = j; i += 1                           # a dropped whitespace maps onto the next kept char
    mp[len(old_text)] = len(new_text)
    out = []
    for s in styles:
        e = copy.deepcopy(s); e["range"] = [mp[s["range"][0]], mp[s["range"][1]]]
        if e["range"][1] > e["range"][0]:
            out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    tm = {m["id"]: m for m in d["materials"]["texts"]}
    st = lambda s: s["target_timerange"]["start"]; en = lambda s: st(s) + s["target_timerange"]["duration"]
    get = lambda s: json.loads(tm[s["material_id"]]["content"])
    def put(s, ct):
        tm[s["material_id"]]["content"] = json.dumps(ct, ensure_ascii=False)
    changes = []
    for tr in d["tracks"]:
        if tr["type"] != "text" or not (tr.get("name") or "").startswith("כתוביות"):
            continue
        segs = sorted(tr["segments"], key=st)
        for s in segs:                                   # inside a card
            ct = get(s); t0 = ct["text"]; t1 = t0
            for rx, rep in INSIDE:
                t1 = rx.sub(rep, t1)
            if t1 != t0:
                ct["styles"] = restyle(t0, t1, ct["styles"]); ct["text"] = t1; put(s, ct); changes.append((round(st(s) / 1e6, 2), t0, t1))
        drop = []
        for x, y in zip(segs, segs[1:]):                 # across two cards
            if x in drop or y in drop or abs(st(y) - en(x)) > 150_000 or abs(x["clip"]["alpha"] - y["clip"]["alpha"]) > 0.1:
                continue
            cx, cy = get(x), get(y)
            if json.dumps(cx["styles"][-1].get("fill")) == json.dumps(cy["styles"][0].get("fill")):
                mx = re.search(r"(^|\s)(\d{1,3})\.?$", cx["text"].rstrip()); my = re.match(r"(\d{3})(?!\d)", cy["text"].lstrip())
                same = re.fullmatch(r"\s*(\d+)\.?\s*", cx["text"]) and re.match(r"\s*" + re.escape(re.fullmatch(r"\s*(\d+)\.?\s*", cx["text"]).group(1)) + r"\b", cy["text"])
                if same:                                 # «2.» then «2. לקוח M…» — the correction said twice: one card
                    y["target_timerange"]["duration"] = en(y) - st(x); y["target_timerange"]["start"] = st(x); drop.append(x)
                    changes.append((round(st(x) / 1e6, 2), cx["text"] + " | " + cy["text"], cy["text"])); continue
                if mx and my:                            # «רמת השרון 2» | «000 שקל» → «רמת השרון» | «2,000 שקל»
                    num = mx.group(2); old_y = cy["text"]
                    cy["text"] = num + "," + cy["text"].lstrip()
                    for e in cy["styles"]:
                        e["range"] = [0 if e["range"][0] == 0 else e["range"][0] + len(num) + 1 - (len(old_y) - len(old_y.lstrip())), e["range"][1] + len(num) + 1 - (len(old_y) - len(old_y.lstrip()))]
                    rest_x = cx["text"].rstrip()[:mx.start(2)].rstrip()
                    if rest_x:
                        cx["text"] = rest_x; cx["styles"][-1]["range"][1] = len(rest_x); put(x, cx)
                        share = int((en(x) - st(x)) * (len(num) + 1) / max(1, len(rest_x) + len(num) + 1))
                        x["target_timerange"]["duration"] -= share; y["target_timerange"]["start"] -= share; y["target_timerange"]["duration"] += share
                    else:
                        y["target_timerange"]["duration"] = en(y) - st(x); y["target_timerange"]["start"] = st(x); drop.append(x)
                    put(y, cy); changes.append((round(st(x) / 1e6, 2), cx["text"] + " | " + old_y, cy["text"])); continue
            m = re.match(r"\s*(,\d{3}[.,?!]*)(\s+|$)", cy["text"])
            if not (re.search(r"\d$", cx["text"].rstrip()) and m):
                continue
            if json.dumps(cx["styles"][-1].get("fill")) != json.dumps(cy["styles"][0].get("fill")):
                continue
            tok = m.group(1); rest = cy["text"][m.end():]
            old_x = cx["text"]; cx["text"] = old_x.rstrip() + tok
            cx["styles"][-1]["range"][1] = len(cx["text"])
            if rest.strip():
                cut = m.end()
                cy["styles"] = [dict(e, range=[max(0, e["range"][0] - cut), e["range"][1] - cut]) for e in cy["styles"] if e["range"][1] > cut]
                cy["text"] = rest; put(y, cy)
                share = int((en(y) - st(y)) * len(tok) / max(1, len(tok) + len(rest)))
                x["target_timerange"]["duration"] += share; y["target_timerange"]["start"] += share; y["target_timerange"]["duration"] -= share
            else:
                x["target_timerange"]["duration"] = en(y) - st(x); drop.append(y)
            put(x, cx); changes.append((round(st(x) / 1e6, 2), old_x + " | " + cy["text"], cx["text"]))
        tr["segments"] = [s for s in tr["segments"] if s not in drop]
    for c in changes:
        print(c)
    print(f"{len(changes)} תיקוני מספרים")
    if a.write and changes:
        if capcut.capcut_running():
            raise SystemExit("⛔ CapCut פתוח")
        capcut._backup(P); capcut._atomic_write(P, d); print("✓ נכתב")


if __name__ == "__main__":
    main()
