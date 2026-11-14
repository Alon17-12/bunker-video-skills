"""רילס.json — 10 whole ideas, each ≤ 90 s, opening on a sentence start and closing on a sentence end."""
GAP = 0.35
END = (".", "?", "!")


def _is_sentence_start(words, t):
    """The first word that starts at or after the edge (within 0.6 s) must open a sentence."""
    i = next((k for k, w in enumerate(words) if w["start_s"] >= t - 0.05), None)
    if i is None or words[i]["start_s"] - t > 0.6:
        return False
    return i == 0 or words[i]["start_s"] - words[i - 1]["end_s"] >= GAP or words[i - 1]["text"].endswith(END)


def _is_sentence_end(words, t):
    """The last word that ends at or before the edge (within 0.6 s) must close a sentence."""
    i = next((k for k in range(len(words) - 1, -1, -1) if words[k]["end_s"] <= t + 0.05), None)
    if i is None or t - words[i]["end_s"] > 0.6:
        return False
    return (i == len(words) - 1 or words[i + 1]["start_s"] - words[i]["end_s"] >= GAP
            or words[i]["text"].endswith(END))


def validate_picks(picks: list[dict], words: list[dict], count: int = 10) -> list[str]:
    errs = []
    if len(picks) != count:
        errs.append(f"צריך בדיוק {count} רילס, יש {len(picks)}")
    for p in picks:
        tag, length = f"ריל {p['n']}", p["end"] - p["start"]
        if not 15 <= length <= 90:
            errs.append(f"{tag}: אורך {length:.0f} שניות — חייב להיות בין 15 ל-90")
        if not _is_sentence_start(words, p["start"]):
            errs.append(f"{tag}: מתחיל באמצע משפט")
        if not _is_sentence_end(words, p["end"]):
            errs.append(f"{tag}: נגמר באמצע משפט")
        h = p.get("hook")
        if h and not (p["start"] <= h["start"] < h["end"] <= p["end"]):
            errs.append(f"{tag}: ההוק מחוץ לגבולות הריל")
    ordered = sorted(picks, key=lambda p: p["start"])
    for a, b in zip(ordered, ordered[1:]):
        if b["start"] < a["end"]:
            errs.append(f"ריל {b['n']} חופף לריל {a['n']}")
    return errs


def snap(pick: dict, words: list[dict], lead: float = 0.12, tail: float = 0.2) -> dict:
    """Edges onto word edges without ever cutting a word: an edge that falls inside a word takes that whole word;
    an edge in a gap takes the nearest word edge within 2 s."""
    p = dict(pick)
    inside = lambda t: next((w for w in words if w["start_s"] <= t <= w["end_s"]), None)
    # an edge already sitting `lead` before a word / `tail` after one belongs to that word (re-snapping is a no-op)
    s = next((w for w in words if abs(w["start_s"] - lead - pick["start"]) < 1e-3), None) \
        or inside(pick["start"]) or min(words, key=lambda w: abs(w["start_s"] - pick["start"]))
    e = next((w for w in reversed(words) if abs(w["end_s"] + tail - pick["end"]) < 1e-3), None) \
        or inside(pick["end"]) or min(words, key=lambda w: abs(w["end_s"] - pick["end"]))
    if abs(s["start_s"] - pick["start"]) <= 2:
        p["start"] = s["start_s"] - lead
    if abs(e["end_s"] - pick["end"]) <= 2:
        p["end"] = e["end_s"] + tail
    return p
