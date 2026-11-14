"""Episode QA (black / frozen frames, loudness) and YouTube chapters."""
import re, subprocess
from pathlib import Path

FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")


def parse_black(err: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]


def parse_freeze(err: str) -> list[tuple[float, float]]:
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def parse_loudness(err: str) -> float:
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(m[-1]) if m else float("nan")


def _t(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def qa_report(video: Path) -> str:
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(video), "-vf",
                        "blackdetect=d=0.5,freezedetect=n=0.003:d=2", "-af", "ebur128",
                        "-f", "null", "-"], capture_output=True, text=True)
    err = r.stderr
    lufs = parse_loudness(err)
    lines = ["# בקרת איכות — פרק", ""]
    lines += [f"- פריים שחור {_t(a)}–{_t(b)}" for a, b in parse_black(err)]
    lines += [f"- פריים קפוא {_t(a)}–{_t(b)}" for a, b in parse_freeze(err)]
    flag = "" if abs(lufs + 16) <= 1.5 else "  ⚠ מחוץ לטווח (−16 ±1.5)"
    lines.append(f"- עוצמה: {lufs:.1f} LUFS{flag}")
    return "\n".join(lines) + "\n"


def shift_chapters(chapters: list[tuple[float, str]], trim_in: float) -> list[tuple[float, str]]:
    """Source-clock chapters → trimmed-episode clock: subtract the trim, drop the pre-roll, first at 0."""
    out = [(t - trim_in, title) for t, title in chapters if t - trim_in >= 0]
    return [(0, out[0][1])] + out[1:] if out else []


def format_chapters(chapters: list[tuple[float, str]]) -> str:
    if len(chapters) < 3:
        raise ValueError("יוטיוב דורש לפחות 3 פרקים")
    if chapters[0][0] != 0:
        raise ValueError("הפרק הראשון חייב להתחיל ב-0:00")
    for (a, _), (b, title) in zip(chapters, chapters[1:]):
        if b - a < 10:
            raise ValueError(f"כל פרק חייב להיות לפחות 10 שניות («{title}»)")
    return "\n".join(f"{_t(t)} {title}" for t, title in chapters)
