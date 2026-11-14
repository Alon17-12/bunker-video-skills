"""Self-check a rendered reel: frames around every cut, captions vs what is actually said, clean ends."""
import difflib, re, subprocess
from pathlib import Path

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
NORM = re.compile(r"[\u0591-\u05C7.,!?;:\"'״׳\-־–—…]")


def _n(w: str) -> str:
    return NORM.sub("", w).strip()


def caption_diff(captions: list[str], heard: list[str]) -> list[dict]:
    a, b = [_n(w) for w in captions], [_n(w) for w in heard]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        out.append({"caption": " ".join(captions[i1:i2]).strip(".,?!"),
                    "heard": " ".join(heard[j1:j2]), "index": i1})
    return out


def boundary_report(words: list[dict], duration: float) -> list[str]:
    if not words:
        return ["אין דיבור ברינדור"]
    errs = []
    if words[0]["start_s"] > 0.6:
        errs.append(f"שקט של {words[0]['start_s']:.1f} שניות בפתיחה")
    if words[-1]["end_s"] > duration - 0.05:
        errs.append("הריל נחתך באמצע המילה האחרונה")
    elif duration - words[-1]["end_s"] > 1.0:
        errs.append(f"שקט של {duration - words[-1]['end_s']:.1f} שניות בסיום")
    return errs


def contact_sheet(video: Path, times: list[float], out: Path) -> Path:
    shots = sorted({round(max(t + d, 0), 3) for t in times for d in (-0.12, 0.12)})
    expr = "+".join(f"between(t\\,{t - 0.017}\\,{t + 0.017})" for t in shots)
    rows = max(1, -(-len(shots) // 6))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(video), "-vf",
                    f"select='{expr}',scale=270:-1,tile=6x{rows}", "-frames:v", "1",
                    "-vsync", "vfr", str(out)], check=True)
    return Path(out)
