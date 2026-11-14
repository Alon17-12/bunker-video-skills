"""Episode transcription in durable 10-minute windows (a sleep or crash loses one window at most)."""
import json
from pathlib import Path
import numpy as np

SR = 16000


def windows(duration: float, size: float = 600, overlap: float = 3) -> list[tuple[float, float]]:
    out, t = [], 0.0
    while t < duration:
        end = min(t + size, duration)
        out.append((t, end))
        if end >= duration:
            break
        t = end - overlap
    return out


def merge(prev: list[dict], new: list[dict], seam: float) -> list[dict]:
    return [w for w in prev if w["start_s"] < seam] + [w for w in new if w["start_s"] >= seam]


def run(audio_path: Path, out_dir: Path, stt, load_audio, duration: float) -> list[dict]:
    out = Path(out_dir) / ".windows.json"           # resume state — never the final transcript
    state = json.loads(out.read_text()) if out.exists() else {"done_until": 0.0, "words": []}
    words = state["words"]
    for t0, t1 in windows(duration):
        if t1 <= state["done_until"]:
            continue
        got = [dict(w, start_s=w["start_s"] + t0, end_s=w["end_s"] + t0)
               for w in stt(load_audio(audio_path, t0, t1))]
        seam = t0 + 1.5 if t0 > 0 else 0.0           # middle of the 3 s overlap
        words = merge(words, got, seam)
        state = {"done_until": t1, "words": words}
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False))
        tmp.replace(out)
    return words


def tag_speakers(words: list[dict], mic_rms: dict, rate: int = 50) -> list[dict]:
    out = []
    for w in words:
        a, b = int(w["start_s"] * rate), max(int(w["end_s"] * rate), int(w["start_s"] * rate) + 1)
        loud = {m: float(np.mean(r[a:b])) if a < r.size else 0.0 for m, r in mic_rms.items()}
        out.append(dict(w, mic=max(loud, key=loud.get)))
    return out


def _ts(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def to_srt(words: list[dict], max_words: int = 7, max_dur: float = 4.5) -> str:
    cues, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["end_s"] - cur[0]["start_s"] > max_dur):
            cues.append(cur); cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    return "\n\n".join(f"{i}\n{_ts(c[0]['start_s'])} --> {_ts(c[-1]['end_s'])}\n"
                       + " ".join(x["text"] for x in c) for i, c in enumerate(cues, 1)) + "\n"
