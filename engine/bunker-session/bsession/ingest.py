"""Card → session: find the RODECaster files, check nothing is missing or truncated, measure clocks."""
import re, shutil, subprocess
from pathlib import Path
import numpy as np

FFPROBE = str(Path.home() / "ffmpeg-bin" / "ffprobe")
CAM = re.compile(r"וידי?או\s*(\d)")
CAM_FOLDER = re.compile(r"(?:וידי?או|^מצלמה\s*\d)")          # "<name> - וידאו/" or a session's "מצלמה N/"
CAM_IN_FOLDER = re.compile(r"(?:[-|]\s*|\s|^)(\d)\.(?:mp4|mov)$", re.I)  # "<name> - 1.mp4" / SSD "<name> | 1.mp4" / older "<name> 1.mp4"
MIC = re.compile(r"אודיו\s*(\d)\.wav$")
MIC_ANY = re.compile(r"\.wav$", re.I)                           # any wav in an audio/source folder: "1_COMBO-1.wav"


def classify(paths: list[Path]) -> dict:
    out = {"cam1": None, "cam2": None, "source": None, "mics": [], "ignored": [], "duplicates": []}

    def put(role, p):
        if out[role] is not None and role not in out["duplicates"]:
            out["duplicates"].append(role)           # two recordings on one card — never pick one silently
        out[role] = p

    for p in sorted(paths):
        name = p.name
        if name.startswith("._") or name == ".DS_Store":
            continue
        if "Live-Mix" in name:
            out["ignored"].append(p)
        elif "מקור" in name and p.suffix.lower() in (".mp4", ".mov"):
            put("source", p)
        elif (m := CAM.search(name)) and p.suffix.lower() in (".mp4", ".mov"):
            put(f"cam{m.group(1)}", p)
        elif CAM_FOLDER.search(p.parent.name) and (m := CAM_IN_FOLDER.search(name)):
            put(f"cam{m.group(1)}", p)
        elif MIC.search(name) or (MIC_ANY.search(name) and re.search(r"אודיו|מקור", p.parent.name)):
            out["mics"].append(p)
        else:
            out["ignored"].append(p)
    return out


LABEL = {"cam1": "מצלמה 1", "cam2": "מצלמה 2"}


def completeness(durations: dict) -> list[str]:
    src = durations.get("source")
    if not src:
        return ["חסר קובץ «מקור»"]
    probs = []
    for k in ("cam1", "cam2"):
        d = durations.get(k)
        if d is not None and d < src - 2.0:
            probs.append(f"{LABEL[k]} קצרה מ«מקור» ב-{src - d:.0f} שניות — ייתכן שהקובץ קטוע")
    if durations.get("cam1") is None:
        probs.append("חסרה מצלמה 1")
    return probs


SILENT_DB = -70.0


def drop_silent(mics: list[Path], mean_db: dict) -> tuple[list[Path], list[Path]]:
    """A mic input nobody spoke into (an unused USB channel) is digital silence — never a speaker."""
    kept = [m for m in mics if mean_db.get(m.name, 0.0) > SILENT_DB]
    return kept, [m for m in mics if m not in kept]


def mean_volume(path: Path) -> float:
    r = subprocess.run([FFPROBE.replace("ffprobe", "ffmpeg"), "-hide_banner", "-i", str(path), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else -120.0


def probe_problems(classified: dict, durations: dict) -> list[str]:
    """A file that is on the card but has no readable duration is corrupt (a cut-off recording)."""
    names = {"source": "«מקור»", **LABEL}
    return [f"{names[k]} פגום או קטוע (לא ניתן לקרוא את האורך): {classified[k].name}"
            for k in ("source", "cam1", "cam2") if classified.get(k) is not None and durations.get(k) is None]


def cam_sync_problem(offsets: dict, tol: float = 1 / 30) -> str | None:
    """reels_build seeks both cameras at the same time, so their clocks must agree within a frame."""
    if offsets.get("cam2") is None:
        return None
    d = offsets["cam2"] - offsets["cam1"]
    return None if abs(d) <= tol else f"מצלמה 2 לא מסונכרנת למצלמה 1 ({d:+.3f} שניות) — צריך לחתוך את מצלמה 2 לפני העריכה"


def _envelope(x: np.ndarray, sr: int, rate: int = 50) -> np.ndarray:
    hop = sr // rate
    n = x.size // hop
    e = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    return (e - e.mean()) / (e.std() + 1e-9)


def measure_offset(ref: np.ndarray, other: np.ndarray, sr: int) -> float:
    a, b = _envelope(ref, sr), _envelope(other, sr)
    n = 1 << int(np.ceil(np.log2(a.size + b.size)))
    corr = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    lag = int(np.argmax(corr))
    if lag > n // 2:
        lag -= n
    return lag / 50.0


def offsets_agree(values: list[float], tol: float = 0.04) -> bool:
    return max(values) - min(values) <= tol


def probe_duration(path: Path) -> float | None:
    if path is None:
        return None
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


DEST = {"cam1": "חומרי גלם/מצלמה 1", "cam2": "חומרי גלם/מצלמה 2", "source": "חומרי גלם/מקור"}


def copy_card(classified: dict, session: Path, journal, in_place: bool = False) -> dict:
    if in_place:   # Bunker Express: the session works straight off the SSD — the internal disk has no room for a copy
        for key in ("cam1", "cam2", "source"):
            if classified.get(key) is not None:
                journal.log("ingest", f"{DEST[key]}: {classified[key].name} (במקום, בלי העתקה)")
        out = {k: (Path(v).resolve() if isinstance(v, Path) else v) for k, v in classified.items() if k != "mics"}
        return dict(out, mics=[Path(m).resolve() for m in classified.get("mics", [])])   # absolute: ingest.json is read from anywhere
    out = dict(classified, mics=[])
    session = Path(session)
    for key, rel in DEST.items():
        src = classified.get(key)
        if src is None:
            continue
        dst = Path(session) / rel / src.name
        if not (dst.exists() and dst.stat().st_size == src.stat().st_size):
            shutil.copy2(src, dst)
        assert dst.stat().st_size == src.stat().st_size, f"copy size mismatch: {dst}"
        out[key] = dst
        journal.log("ingest", f"{rel}: {src.name} ({src.stat().st_size / 1e9:.1f}GB)")
    for m in classified.get("mics", []):
        dst = Path(session) / "חומרי גלם/מקור" / m.name
        if not (dst.exists() and dst.stat().st_size == m.stat().st_size):
            shutil.copy2(m, dst)
        assert dst.stat().st_size == m.stat().st_size, f"copy size mismatch: {dst}"
        out["mics"].append(dst)
    return out
