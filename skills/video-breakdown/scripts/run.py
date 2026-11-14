#!/usr/bin/env python3
"""Run the measurement pipeline over a batch of links, resumably.

    run.py <batch_dir> <url> [<url> ...]
    run.py <batch_dir>            # reads <batch_dir>/sources.txt, one URL per line

Each video gets its own folder. Every stage checks for its own output and
skips itself, so re-running after a failure — or after adding two links —
costs only the missing work. Ends with summary.json and a table of the measured
numbers, which is the skeleton comparison.md is written from.

Instagram public reels download without login. A cookies.txt at
~/.config/video-breakdown/instagram-cookies.txt (picked up automatically) is
recommended: it unlocks the proper API path and full metadata.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES = (  # (name, output that proves it ran)
    ("measure", "evidence/shots.json"),
    ("audio", "evidence/audio.json"),
    ("transcript", "evidence/transcript.json"),
)


def _slug(index: int, url: str) -> str:
    platform = "yt" if re.search(r"youtu\.?be", url) else "ig" if "instagram" in url else "src"
    ident = re.search(r"(?:v=|shorts/|reel/|p/|youtu\.be/)([\w-]+)", url)
    return f"{index:02d}-{platform}-{ident.group(1)[:16] if ident else 'video'}"


def _run(cmd, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _process(url: str, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    row = {"url": url, "dir": folder.name, "status": "ok"}

    if not (folder / "source.mp4").exists() or not (folder / "evidence" / "meta.json").exists():
        fetch = _run([str(HERE / "fetch.sh"), url, str(folder)])
        if fetch.returncode != 0:
            # yt-dlp prints the real reason on an ERROR line; the last line is
            # usually just our own "no source.mp4" wrapper around it.
            lines = fetch.stdout.strip().splitlines()
            reason = next((l for l in lines if "ERROR" in l), lines[-1] if lines else "no output")
            row["status"] = "fetch failed: " + reason[:160]
            return row

    video = folder / "source.mp4"
    for stage, proof in STAGES:
        if (folder / proof).exists():
            continue
        args = [str(folder)] if stage == "transcript" else [str(video), str(folder)]
        script = f"{stage}.py"
        # No platform captions (Instagram) → local Whisper via the caption studio.
        if stage == "transcript" and not list(folder.glob("source.*.vtt")):
            script = "transcribe_local.py"
        result = _run([sys.executable, str(HERE / script), *args])
        if result.returncode != 0:
            row["status"] = f"{stage} failed: " + result.stdout.strip().splitlines()[-1][:120]
            return row

    meta = _load(folder / "evidence" / "meta.json")
    shots = _load(folder / "evidence" / "shots.json")
    audio = _load(folder / "evidence" / "audio.json")
    words = _load(folder / "evidence" / "transcript.json")
    row.update({
        "creator": meta.get("creator"), "views": meta.get("views"), "likes": meta.get("likes"),
        "audio": "yes" if meta.get("audio_present", True) else "SILENT",
        "duration_s": shots.get("duration_s"), "shots": shots.get("shot_count"),
        "avg_shot_s": shots.get("avg_shot_s"), "longest_shot_s": shots.get("longest_shot_s"),
        "cuts_per_min": shots.get("cuts_per_minute"),
        "framing": shots.get("framing_counts"), "hook": shots.get("hook"),
        "caption_changes": _load(folder / "evidence" / "captions.json").get("change_count"),
        "wpm": words.get("wpm"), "bpm": audio.get("tempo_bpm"),
        "bed_db": audio.get("bed_under_speech_db"), "hits_per_min": audio.get("hits_per_minute"),
        "hits_on_cuts": (audio.get("hits_on_cuts") or {}).get("share"),
        "warning": shots.get("warning"),
    })
    return row


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    batch = Path(sys.argv[1]).expanduser()
    urls = sys.argv[2:]
    if not urls:
        src = batch / "sources.txt"
        if not src.exists():
            raise SystemExit(f"no URLs given and {src} does not exist")
        urls = [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    batch.mkdir(parents=True, exist_ok=True)
    (batch / "sources.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    rows = []
    for i, url in enumerate(urls, start=1):
        folder = batch / _slug(i, url)
        print(f"[{i}/{len(urls)}] {folder.name}", flush=True)
        rows.append(_process(url, folder))
        print(f"      {rows[-1]['status']}", flush=True)

    (batch / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    cols = ("dir", "creator", "duration_s", "audio", "shots", "avg_shot_s", "cuts_per_min",
            "caption_changes", "wpm", "bpm", "bed_db", "hits_per_min", "hits_on_cuts")
    print("\n| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for row in rows:
        # Creator names carry "|" (Instagram bios); it would split the table.
        print("| " + " | ".join("—" if row.get(c) is None else str(row.get(c)).replace("|", "/")[:40] for c in cols) + " |")
    bad = [r for r in rows if r["status"] != "ok"]
    if bad:
        print("\nnot analysed:")
        for r in bad:
            print(f"  {r['dir']}: {r['status']}")


if __name__ == "__main__":
    main()
