"""Register generated assets in a CapCut project's Media panel.

Writing a file into the draft folder and pointing a segment at it puts the clip on the timeline,
but NOT in the project's media list — so the b-roll you generated is invisible in the Media tab,
cannot be dragged in again, and looks to the editor like it came from nowhere. CapCut keeps that
list in `draft_meta_info.json` → `draft_materials[type 0].value`, separate from `draft_info.json`.
Every asset you attach to a project belongs in both.

    python register_media.py 0919                      # every ccstudio-* asset in the draft folder
    python register_media.py 0919 --glob 'broll-*.mp4'
    python register_media.py 0919 --list               # show what is registered now

Idempotent: a file already listed (by path) is left alone, so it is safe to re-run after every
build. CapCut must be fully closed — it owns this file while it runs and will overwrite you.
"""
import argparse, json, os, re, subprocess, sys, time, uuid
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut, paths

MEDIA_BLOCK = 0                       # draft_materials[].type 0 is the imported-media list
EXT = {".mp4": "video", ".mov": "video", ".m4v": "video",
       ".mp3": "music", ".wav": "music", ".m4a": "music", ".aac": "music",
       ".png": "photo", ".jpg": "photo", ".jpeg": "photo", ".webp": "photo"}


def probe(path):
    """(width, height, duration_us) from ffmpeg's stderr — there is no ffprobe binary here."""
    err = subprocess.run([str(paths.FFMPEG), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    wh = re.search(r" (\d{2,5})x(\d{2,5})[, ]", err)
    dur = int((int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))) * 1e6) if d else 0
    return (int(wh.group(1)), int(wh.group(2)), dur) if wh else (0, 0, dur)


def entry(path, metetype):
    if metetype == "photo":
        from PIL import Image
        w, h = Image.open(path).size
        dur = 5_000_000                                  # CapCut's default still length
    else:
        w, h, dur = probe(path)
        if metetype == "music":
            w = h = 0
    now = int(time.time())
    return {"ai_group_type": "", "create_time": now, "duration": dur, "extra_info": path.name,
            "file_Path": str(path), "height": h, "id": str(uuid.uuid4()).upper(),
            "import_time": now, "import_time_ms": now * 1000, "item_source": 1, "md5": "",
            "metetype": metetype, "roughcut_time_range": {"duration": dur, "start": 0},
            "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": w}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--glob", default="ccstudio-*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prune", action="store_true", help="drop registry entries whose file no longer exists (after replacing a b-roll set)")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    folder = capcut.DRAFTS_DIR / a.draft
    meta_path = folder / "draft_meta_info.json"
    if not meta_path.exists():
        sys.exit(f"no draft_meta_info.json in {folder}")
    meta = json.load(open(meta_path))
    block = next(b for b in meta["draft_materials"] if b.get("type") == MEDIA_BLOCK)
    block.setdefault("value", [])
    # CapCut rewrites the path of any file inside the draft folder to "./name" when it saves, so an
    # absolute path we registered comes back relative after Alon opens the project once. Compare by
    # the resolved path, and fold the duplicates that an earlier run created before this was known.
    def norm(fp): return str(folder / fp[2:]) if fp.startswith("./") else fp
    seen, kept, dropped = set(), [], 0
    for v in block["value"]:
        k = norm(v.get("file_Path", ""))
        if k in seen: dropped += 1; continue
        seen.add(k); kept.append(v)
    block["value"] = kept
    if dropped: print(f"{dropped} duplicate entries folded (same file, './' vs absolute)")
    if a.prune:
        gone = [v for v in kept if not Path(norm(v.get("file_Path", ""))).exists()]
        for v in gone: print(f"  - pruned (file gone): {v.get('extra_info')}")
        block["value"] = kept = [v for v in kept if v not in gone]; dropped += len(gone)
    have = {norm(v.get("file_Path", "")) for v in kept}

    if a.list:
        for v in block["value"]:
            print(f"  {v.get('metetype'):6} {v.get('duration', 0) / 1e6:8.2f}s  {v.get('extra_info')}")
        print(f"{len(block['value'])} items registered")
        return

    found = sorted(p for p in folder.glob(a.glob)
                   if p.suffix.lower() in EXT and not re.search(r"\.(prev|orig|bak)$", p.stem))
    added = []
    for p in found:
        if str(p) in have:
            continue
        added.append(entry(p, EXT[p.suffix.lower()]))
    print(f"{len(found)} files match, {len(have)} already registered, {len(added)} to add")
    for e in added:
        print(f"  + {e['metetype']:6} {e['duration'] / 1e6:6.2f}s {e['width']}x{e['height']}  {e['extra_info']}")
    if not a.write:
        print("dry run — pass --write")
        return
    if capcut._capcut_pid() is not None:
        sys.exit("CapCut is running — it owns draft_meta_info.json and will overwrite this. Quit it first (⌘Q).")
    if not added and not dropped:
        return
    bak = folder / f"draft_meta_info.ccstudio-backup-{int(time.time())}.json"
    bak.write_text(meta_path.read_text())
    block["value"].extend(added)
    meta["draft_timeline_materials_size_"] = meta.get("draft_timeline_materials_size_", 0)
    tmp = meta_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    json.loads(tmp.read_text())
    tmp.replace(meta_path)
    print(f"WRITTEN — {len(added)} assets now in the project's Media panel (backup: {bak.name})")


if __name__ == "__main__":
    main()
