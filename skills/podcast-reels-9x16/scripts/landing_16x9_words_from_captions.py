"""Carry approved caption text onto a fresh transcription.

A re-transcription of the same audio drifts by a word here and there («ראיון איתי» → «רעיון בהחלט
איתי», «ה-15» → «חמש עשרה»), and every one of those is a caption Alon already corrected once. The
approved text lives in the source project's caption track, so align the new word list to it and
take the approved token wherever the two disagree one-for-one.

    WORK=… DRAFT_SRC=0919 python landing_16x9_words_from_captions.py    # rewrites <WORK>/0919_words_fixed.json

Prints every substitution. Where the alignment is not one-for-one (an inserted or dropped word) the
new transcription is kept and the spot is listed for a human look.
"""
import difflib, json, os, re, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut

WORK = os.path.expanduser(os.environ.get("WORK", "~/Movies/reel-captions-work/landing-16x9"))
SRC = os.environ.get("DRAFT_SRC", "0919"); US = 1e6
def core(t): return re.sub(r"[^\w%₪]+", "", t).lower()

d = capcut.load_draft(SRC)
cap = next(t for t in d["tracks"] if t.get("name") == "כתוביות")
tm = {m["id"]: m for m in d["materials"]["texts"]}
cards = sorted(((s["target_timerange"]["start"] / US, json.loads(tm[s["material_id"]]["content"])["text"]) for s in cap["segments"]), key=lambda x: x[0])
W = json.load(open(f"{WORK}/0919_words_fixed.json"))
total_sub, unresolved = 0, []
for v in W["videos"]:
    A, B = v["A"] / US, v["B"] / US
    approved = [tok for t, txt in cards if A - 0.01 <= t < B for tok in txt.split()]
    new = [w["text"] for w in v["words"]]
    sm = difflib.SequenceMatcher(None, [core(x) for x in new], [core(x) for x in approved], autojunk=False)
    for op, i0, i1, j0, j1 in sm.get_opcodes():
        if op == "equal": continue
        if op == "replace" and (i1 - i0) == (j1 - j0):
            for k in range(i1 - i0):
                old = v["words"][i0 + k]["text"]; nw = approved[j0 + k]
                if core(old) != core(nw):
                    v["words"][i0 + k]["text"] = nw; total_sub += 1; print(f"  {A + v['words'][i0 + k]['start_s']:7.2f}  {old!r} → {nw!r}")
        else:
            unresolved.append((round(A + v["words"][min(i0, len(v["words"]) - 1)]["start_s"], 2), " ".join(new[i0:i1]), " ".join(approved[j0:j1])))
json.dump(W, open(f"{WORK}/0919_words_fixed.json", "w"), ensure_ascii=False, indent=0)
print(f"{total_sub} tokens taken from the approved captions; {len(unresolved)} spots not one-for-one:")
for t, a, b in unresolved[:40]: print(f"  {t:7.2f}  new {a!r}  |  approved {b!r}")
