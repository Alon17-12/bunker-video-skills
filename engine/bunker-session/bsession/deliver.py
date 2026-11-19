"""Approved versions → מסירה/ with the version in the file name."""
import json, math, re, shutil, subprocess
from pathlib import Path

V = re.compile(r"^v(\d+)\.mp4$")


def latest_version(reel_dir: Path):
    vs = [(int(m.group(1)), p) for p in Path(reel_dir).iterdir() if (m := V.match(p.name))]
    return max(vs) if vs else None


def stage_delivery(session: Path, client: str) -> list[Path]:
    s, out_dir = Path(session), Path(session) / "מסירה"
    manifest, out = [], []
    for reel in sorted(p for p in (s / "רילס").iterdir() if p.is_dir()):
        lv = latest_version(reel)
        if not lv:
            continue
        ver, src = lv
        nn, title = reel.name.split(" - ", 1)
        prefix = f"{client} - ריל {nn} - {title} - v"
        for old in out_dir.glob(f"{glob_escape(prefix)}*.mp4"):
            old.unlink()
        dst = out_dir / f"{prefix}{ver}.mp4"
        shutil.copy2(src, dst)
        manifest.append({"file": dst.name, "source": str(src.relative_to(s)), "version": ver})
        out.append(dst)
    ep = s / "פרק/פרק.mp4"
    if ep.exists():
        dst = out_dir / f"{client} - פרק.mp4"; shutil.copy2(ep, dst); out.append(dst)
        manifest.append({"file": dst.name, "source": "פרק/פרק.mp4", "version": 1})
    ch = s / "פרק/פרקים-ליוטיוב.txt"
    if ch.exists():
        shutil.copy2(ch, out_dir / ch.name); out.append(out_dir / ch.name)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    return out


def glob_escape(s: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", s)


FF = str(Path.home() / "ffmpeg-bin/ffmpeg")
FP = str(Path.home() / "ffmpeg-bin/ffprobe")
DRAFTS = (Path(__import__("os").environ["BUNKER_CAPCUT_DRAFTS"]) if __import__("os").environ.get("BUNKER_CAPCUT_DRAFTS") else (Path(__import__("os").environ.get("LOCALAPPDATA", "")) / "CapCut/User Data/Projects/com.lveditor.draft" if __import__("os").name == "nt" else Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft"))
FOLDERS = ("חומרי גלם", "הפרק השלם", "רילס")       # the Bunker Express delivery, folder for folder (Alon 18.10.2026)


def split_plan(layout: dict, export_s: float, tol: float = 2.0) -> list[tuple[str, float, float]]:
    """The reels project exports as ONE file; the layout (capcut_reels.py) says where each reel sits in it."""
    last = max(r["end"] for r in layout["reels"])
    if abs(last - export_s) > tol:
        raise ValueError(f"הייצוא של הרילס ({export_s:.1f} שנ׳) לא תואם לפרויקט ({last:.1f} שנ׳) — לייצא שוב את כל הפרויקט")
    fps = 30.0       # the layout keeps CapCut's exact microseconds; a reel starts on its first WHOLE frame, so no divider frame leaks in
    return [(r["dir"], math.ceil(r["start"] * fps - 1e-6) / fps, math.floor(min(r["end"], export_s) * fps + 1e-6) / fps)
            for r in layout["reels"]]


def layout_from_draft(draft: dict, dirs: list[str]) -> dict:
    """Where the reels really are in the CapCut project NOW — Alon edits it by hand, so the layout written at build time
    can be stale. A reel runs from the end of its white divider to the start of the next one (or the project's end)."""
    names = {m["id"]: m.get("material_name", "") for m in draft["materials"].get("videos", [])}
    segs = sorted(draft["tracks"][0]["segments"], key=lambda x: x["target_timerange"]["start"])
    rng = lambda x: (x["target_timerange"]["start"], x["target_timerange"]["start"] + x["target_timerange"]["duration"])
    div = [rng(x) for x in segs if names.get(x["material_id"]) == "divider.png"]
    if len(div) != len(dirs):
        raise ValueError(f"בפרויקט הקאפקאט {len(div)} חוצצים אבל {len(dirs)} רילס — לבנות את הפרויקט מחדש או לעדכן את הרילס")
    end = max(rng(x)[1] for x in segs)
    return {"reels": [{"id": f"r{d.split(' - ')[0].lstrip('0') or '0'}", "dir": d, "start": round(div[i][1] / 1e6, 6),
                       "end": round((div[i + 1][0] if i + 1 < len(div) else end) / 1e6, 6)} for i, d in enumerate(dirs)]}


def _fps(p: Path) -> float:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True).stdout.strip()
    a, b = (r.split("/") + ["1"])[:2]
    return float(a) / float(b)


def _probe(p: Path) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def _loudness(src: Path) -> tuple[float, float]:
    r = subprocess.run([FF, "-hide_banner", "-i", str(src), "-vn", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
    return float(j["input_i"]), float(j["input_tp"])


def _mp3(src: Path, dst: Path, target: float = -16.0, ceiling: float = -1.5, tmp: Path | None = None) -> None:
    """The episode as a podcast mp3 at −16 LUFS. One-pass loudnorm is held back by the true-peak ceiling when speech is
    quiet and has sharp peaks (the pilot came out at −17.1). So: measure → gain → limit the peaks under the ceiling,
    repeated until the loudness is within 0.3 LU (limiting peaks lowers the loudness a little each round), then encode."""
    tmp = Path(tmp or dst.parent)                            # never the delivery folder: a killed run would leave 1.4 GB there
    tmp.mkdir(parents=True, exist_ok=True)
    work = [tmp / f"{dst.stem}.a.wav", tmp / f"{dst.stem}.b.wav"]
    cur = src
    try:
        for k in range(4):
            i, tp = _loudness(cur)
            if abs(i - target) <= 0.3 and tp <= ceiling + 0.2:
                break
            af = f"volume={target - i:.2f}dB,alimiter=limit={10 ** ((ceiling - 0.3) / 20):.4f}:level=disabled:attack=1:release=60"
            subprocess.run([FF, "-v", "error", "-y", "-i", str(cur), "-vn", "-af", af, "-c:a", "pcm_f32le", str(work[k % 2])], check=True)
            cur = work[k % 2]
        subprocess.run([FF, "-v", "error", "-y", "-i", str(cur), "-vn", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", str(dst)], check=True)
    finally:
        for w in work:
            w.unlink(missing_ok=True)


def safe_name(name: str) -> str:
    """A file name from a show or reel title: "/" (and ":" for the Finder) would split or break the path."""
    return re.sub(r"[/:\\]", "-", name).strip()


def stage_express(session: Path, drafts_dir: Path = DRAFTS) -> list[Path]:
    """מסירה/ exactly like the Bunker delivery's three folders: the episode mp4 + an mp3 of it + the YouTube texts,
    every reel cut out of the one CapCut export (re-encoded so each starts on its first frame), חומרי גלם left for the raw."""
    s = Path(session)
    spec = json.loads((s / "אפיון.json").read_text(encoding="utf-8"))
    show = safe_name(spec.get("show") or spec["client"])
    root = s / "מסירה"
    for f in FOLDERS:
        (root / f).mkdir(parents=True, exist_ok=True)
    out, ep_dir, rl_dir = [], root / "הפרק השלם", root / "רילס"
    ep = s / "פרק/פרק.mp4"
    if ep.exists():
        mp4, mp3 = ep_dir / f"{show} - פרק.mp4", ep_dir / f"{show} - פרק.mp3"
        shutil.copy2(ep, mp4)
        _mp3(ep, mp3, tmp=s / ".tmp")
        out += [mp4, mp3]
    yt = s / "פרק/יוטיוב.json"
    if yt.exists():
        y = json.loads(yt.read_text(encoding="utf-8"))
        (ep_dir / "כותרת ליוטיוב.txt").write_text(y["title"].strip() + "\n", encoding="utf-8")
        (ep_dir / "תיאור ליוטיוב.txt").write_text(f"{y['description'].strip()}\n\n{y['chapters'].strip()}\n", encoding="utf-8")
        out += [ep_dir / "כותרת ליוטיוב.txt", ep_dir / "תיאור ליוטיוב.txt"]
    exp, lay = s / "רילס/ייצוא.mp4", s / "רילס/capcut-layout.json"
    if exp.exists() and lay.exists():
        layout = json.loads(lay.read_text(encoding="utf-8"))
        info = Path(drafts_dir) / layout.get("project", "") / "draft_info.json"
        if layout.get("project") and info.exists():         # the project as it is now, after any hand edits
            layout = layout_from_draft(json.loads(info.read_text(encoding="utf-8")), [r["dir"] for r in layout["reels"]])
        if abs(_fps(exp) - 30) > 0.01:
            raise ValueError(f"הייצוא של הרילס ב-{_fps(exp):.0f} פריימים לשנייה — לייצא ב-30, כמו הפרויקט")
        for old in rl_dir.glob("*.mp4"):                    # a renamed or dropped reel must not be delivered twice
            old.unlink()
        for name, a, b in split_plan(layout, _probe(exp)):
            dst = rl_dir / f"{safe_name(name)}.mp4"
            frames = round((b - a) * 30)                     # an exact frame count: "-t" rounds up and took the next divider's first frame
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", str(exp), "-frames:v", str(frames), "-t", f"{frames / 30:.4f}",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac", "-b:a", "256k",
                            "-movflags", "+faststart", str(dst)], check=True)
            out.append(dst)
    if not out:
        raise ValueError("אין מה למסור — חסרים פרק/פרק.mp4 וגם רילס/ייצוא.mp4 (+ capcut-layout.json). לייצא מקאפקאט קודם")
    return out
