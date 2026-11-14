#!/usr/bin/env python3
"""First pass over a full episode transcript: which sentences could carry a teaser.

    moments.py <words.json> [--srt suggestions.srt] [--audio episode.wav] [--top 40] > candidates.md

words.json: [{"w"|"word"|"text": str, "t"|"start": sec, "end"?: sec}, …] — the episode transcript (Whisper word level).
--srt:   the client's/editor's suggested moments; every cue becomes a candidate whatever its score, marked ★.
--audio: the episode audio; adds loudness peaks (laughter, raised voice) as a signal.

It only ranks. Choosing is editorial: read the top candidates IN CONTEXT (±20 s) and pick by the rules in
references/podcast-teaser.md §בחירת רגעים — a hook that opens a question, a number, a confession, a clash, a laugh,
and a last line that stops mid-thought. Scores are hints, not the selection.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

# signals measured on the @hakolpodcast teasers: what their opening lines are made of
NUM = re.compile(r"\d|אחוז|מיליון|מיליארד|אלף|שקל|דולר")
STRONG = ["האמת", "אף אחד", "אף פעם", "כולם", "הכי", "סוד", "שקר", "משקרים", "הורג", "מסוכן", "טעות", "לעולם", "בחיים לא",
          "חייב", "אסור", "פחדתי", "פחד", "בכיתי", "נשבר", "פשטתי", "חוב", "מיליונים", "סם", "מוות", "מתים", "בעיה",
          # from the 29 Hakol episode openings (10.10.2026)
          "אי אפשר", "מחיר", "סיכון", "פי ", "נוכל", "הלוואות", "קיבלתי טלפון", "ככל ש", "באמת", "אמיתית"]
TURN = ["אבל", "דווקא", "פתאום", "ואז", "בסוף"]


def load_words(p: Path):
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw = raw.get("words", raw) if isinstance(raw, dict) else raw
    out = []
    for w in raw:
        text = w.get("w") or w.get("word") or w.get("text") or ""
        t = w.get("t", w.get("start"))
        out.append({"text": text.strip(), "t": float(t), "end": float(w.get("end", t + 0.3))})
    return out


def sentences(words):
    cur, out = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["t"] - w["end"] if i + 1 < len(words) else 9
        if re.search(r"[.?!]$", w["text"]) or gap > 0.9 or len(cur) >= 28:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def loudness(audio: Path):
    raw = subprocess.run([str(Path.home() / "ffmpeg-bin/ffmpeg"), "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    import numpy as np
    x = np.frombuffer(raw, dtype=np.float32)
    n = len(x) // 8000
    rms = np.sqrt(np.square(x[: n * 8000].reshape(n, 8000)).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    return (db - np.median(db)) / (db.std() + 1e-9)  # z per second


def parse_srt(p: Path):
    cues = []
    for block in re.split(r"\n\s*\n", p.read_text(encoding="utf-8-sig").strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", block)
        if m:
            g = list(map(int, m.groups()))
            cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000))
    return cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("--srt")
    ap.add_argument("--audio")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    words = load_words(Path(a.words))
    loud = loudness(Path(a.audio)) if a.audio else None
    marked = parse_srt(Path(a.srt)) if a.srt else []
    rows = []
    for s in sentences(words):
        text = " ".join(w["text"] for w in s)
        t0, t1 = s[0]["t"], s[-1]["end"]
        why, score = [], 0.0
        if len(s) < 3 and not any(a_ < s[-1]["end"] and s[0]["t"] < b for a_, b in marked):
            continue  # "אהלן?" is not a moment
        if NUM.search(text): score += 2; why.append("מספר")
        if text.rstrip().endswith("?"): score += 1.5; why.append("שאלה")
        hits = [k for k in STRONG if k in text]
        if hits: score += 1.5 * len(hits); why.append("מילים חזקות: " + ", ".join(hits))
        if any(text.startswith(k) or f" {k} " in text for k in TURN): score += 0.7; why.append("תפנית")
        n = len(s)
        if 5 <= n <= 18: score += 1; why.append("אורך טוב")
        elif n > 24: score -= 1
        if loud is not None:
            seg = loud[int(t0): int(t1) + 1]
            if len(seg) and seg.max() > 1.6: score += 1.2; why.append("שיא עוצמה (צחוק/קול מורם)")
        star = any(t0 < b and t1 > a_ for a_, b in marked)
        if star: score += 100; why.insert(0, "★ סומן ב-SRT")
        rows.append((score, t0, t1, text, why))
    rows.sort(key=lambda r: -r[0])
    print(f"# מועמדים לטיזר — {len(rows)} משפטים, מוצגים {a.top}\n")
    for score, t0, t1, text, why in rows[: a.top]:
        mm = lambda x: f"{int(x // 60)}:{x % 60:05.2f}"
        print(f"- `{mm(t0)}–{mm(t1)}` ({t1 - t0:.1f}s) **{text}**  \n  {' · '.join(why)}")


if __name__ == "__main__":
    main()
