#!/usr/bin/env python3
"""Ranges of the episode → an EDL with the silences taken out (the ~185 wpm the reference teasers run at).

    tighten_edl.py <words.json> <out_edl.json> --range 625.0-641.2 --range 686.2-693.6 [--gap 0.4] [--air 0.12] [--drop 650.1-652.0]

Inside every range the words are kept and any pause longer than --gap is cut down to --air on each side, so a
breath stays but a search for words does not.

--story (Alon, אלון+אייל+דולב 21.10.2026: «יש רגעים שהשתיקה היא מה שבונה את המתח, והכנסת קאטים חדים ולא נעימים שיוצרים
קפיצה באוזן»): every pause keeps what its place in the sentence needs instead of one --air for all — story_pause().
A question keeps up to 0.75 s, a full stop 0.6 s, a long original beat before a short line (the punch) up to 1.0 s,
a comma 0.4 s, a search for words mid-phrase 0.35 s; a jump between ranges gets 0.25 s after / 0.12 s before; a pause already within 80 ms of that is not cut at all. --drop removes a sub-range (a stutter, an aside). The ranges play in
the order given. Feed the result to build_cut.py.
"""
import argparse
import json
from pathlib import Path


def story_pause(text, gap, nxt_words):
    """how much of a pause to keep, from the word before it and the line after it"""
    t = text.rstrip("\"'”״ ")
    short_next = 0 < len(nxt_words) <= 7 and any(w.rstrip("\"'”״ ").endswith((".", "?", "!")) for w in nxt_words[:7])
    if t.endswith("?"):
        keep = 0.75
    elif t.endswith((".", "!", "...", "…")):
        keep = 1.0 if gap >= 1.1 and short_next else 0.6
    elif t.endswith((",", ":", "-", "—")):
        keep = 0.4
    else:
        keep = 0.35
    return min(gap, keep)


def rng(s):
    a, b = s.split("-")
    return float(a), float(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--range", action="append", type=rng, required=True)
    ap.add_argument("--drop", action="append", type=rng, default=[])
    ap.add_argument("--gap", type=float, default=0.4)
    ap.add_argument("--air", type=float, default=0.12)
    ap.add_argument("--story", action="store_true", help="keep each pause by its place in the sentence (story_pause)")
    a = ap.parse_args()
    W = json.loads(Path(a.words).read_text(encoding="utf-8"))
    clips = []
    for lo, hi in a.range:
        head = 0.12 if a.story else a.air / 2
        ws = [w for w in W if lo - 0.01 <= w["t"] < hi and not any(d0 <= w["t"] < d1 for d0, d1 in a.drop)]
        if not ws:
            continue
        start = ws[0]["t"]
        for i, w in enumerate(ws):
            nxt = ws[i + 1] if i + 1 < len(ws) else None
            gap = (nxt["t"] - w["end"]) if nxt else 99
            dropped_between = nxt and any(w["end"] <= d0 < nxt["t"] for d0, _ in a.drop)
            keep = None
            if a.story and nxt and not dropped_between:
                keep = story_pause(w.get("w", w.get("text", "")), gap, [v.get("w", v.get("text", "")) for v in ws[i + 1:i + 9]])
                if gap <= keep + 0.08:
                    continue                                    # the pause is what the line needs: no cut
            if gap > a.gap or dropped_between or nxt is None or keep is not None:
                # never reach into a word outside the range: the air stops 30 ms short of the neighbouring word
                # (Guest N teaser v2, 13.10.2026 — "כן," / "באופן" / "מה" leaked in as clipped syllables after the last word)
                after = next((v["t"] for v in W if v["t"] >= w["end"] - 0.005 and v is not w and v["t"] > w["t"]), 1e9)
                first = next(v for v in ws if v["t"] >= start - 1e-6)
                before = max((v["end"] for v in W if v["end"] <= first["t"] + 0.005 and v["t"] < first["t"]), default=-1e9)
                tail = 0.6 * keep if keep is not None else (0.25 if a.story and nxt is None else a.air)      # the kept pause: 60 % after this line, 40 % before the next
                clips.append({"from": round(min(start - 0.005, max(start - head, before + 0.03)), 2),
                              "to": round(max(w["end"] + 0.005, min(w["end"] + tail, hi + max(a.air, tail), after - 0.03)), 2)})
                head = 0.4 * keep if keep is not None else a.air / 2
                if nxt:
                    start = nxt["t"]
    total = sum(c["to"] - c["from"] for c in clips)
    Path(a.out).write_text(json.dumps({"cams": {"host": 1, "guest": 2}, "clips": clips}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(clips)} clips · {total:.1f}s (from {sum(h - l for l, h in a.range):.1f}s of ranges)")


if __name__ == "__main__":
    main()
