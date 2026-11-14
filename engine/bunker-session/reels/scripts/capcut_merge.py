#!/usr/bin/env python3
r"""Append one reels project to another → ONE CapCut project, ONE export (Alon, אלון+אייל+דולב 21.10.2026: «למה פיצלת את
הרילס לשני פרויקטים שונים?» — 3 speakers on 2 cameras were built as two pair sub-sessions).

    $PY reels/scripts/capcut_merge.py "<base project>" "<project to append>" "<session>" "<sub-session A>" "<sub-session B>"

The appended project's tracks go after the base's last frame, each onto the base track with the same type + name (n-th of
that name); its media files are hard-linked into the base's ccstudio-media under a prefix and every path is rewritten.
The two sub-sessions' capcut-layout.json become one layout in <session>/רילס/capcut-layout.json (bsession deliver cuts
the one export by it). The appended project is then taken off CapCut's home screen and moved to the Trash.
CapCut must be closed.
"""
import json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402
import reels  # noqa: E402

DONOR = "2.7.26 צומת 20 - אורח L טיזר ורילס"


def rewrite(o, old, new):
    if isinstance(o, str):
        return o.replace(old, new) if old in o else o
    if isinstance(o, list):
        return [rewrite(x, old, new) for x in o]
    if isinstance(o, dict):
        return {k: rewrite(v, old, new) for k, v in o.items()}
    return o


def main():
    base_name, add_name, session, sub_a, sub_b = sys.argv[1:6]
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    A, B = capcut.DRAFTS_DIR / base_name, capcut.DRAFTS_DIR / add_name
    da, db = json.loads(capcut._draft_file(A).read_text()), json.loads(capcut._draft_file(B).read_text())
    shift = int(da["duration"])
    # a prefix per appended project: a constant «ב - » made the 2nd–7th merge of תוכן הבונקר לממומן (24.10.2026) keep the
    # FIRST appended project's cam1/cam2 under the same names → wrong picture, black past its end
    import zlib
    prefix = f"{zlib.crc32(add_name.encode()) % 100000:05d} - "
    clash = [f.name for f in (B / "ccstudio-media").iterdir() if (A / "ccstudio-media" / (prefix + f.name)).exists()]
    if clash:
        raise SystemExit(f"⛔ כבר קיימים בפרויקט הבסיס: {clash[:3]}")
    # media: hard links (same disk, no space), names prefixed so cam1.mp4 of one pair never meets the other's
    for f in (B / "ccstudio-media").iterdir():
        if f.name.startswith("._"):
            continue
        dst = A / "ccstudio-media" / (prefix + f.name)
        if not dst.exists():
            os.link(f, dst)
    db = rewrite(db, str(B / "ccstudio-media") + "/", str(A / "ccstudio-media") + "/" + prefix)
    assert str(B) not in json.dumps(db, ensure_ascii=False), "a path into the appended project is left"
    for k, v in db["materials"].items():
        if isinstance(v, list):
            da["materials"].setdefault(k, []).extend(v)
    if isinstance(db.get("keyframes"), dict):
        for k, v in db["keyframes"].items():
            if isinstance(v, list):
                da.setdefault("keyframes", {}).setdefault(k, []).extend(v)
    seen = {}
    for t in db["tracks"]:
        key = (t["type"], t.get("name", ""))
        n = seen.get(key, 0); seen[key] = n + 1
        same = [x for x in da["tracks"] if (x["type"], x.get("name", "")) == key]
        for s in t["segments"]:
            s["target_timerange"]["start"] += shift
        if n < len(same):
            same[n]["segments"].extend(t["segments"])
        else:
            t["id"] = capcut._new_id(); da["tracks"].append(t)
    da["duration"] = shift + int(db["duration"])
    capcut._atomic_write(A, da)
    meta_p = A / "draft_meta_info.json"
    meta = json.loads(meta_p.read_text()); meta["tm_duration"] = da["duration"]; meta["tm_draft_modified"] = int(time.time() * 1e6)
    meta_p.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_remove(base_name)
    reels._registry_add(A, meta["draft_id"], da["duration"], DONOR)
    # one layout for the one export
    la = json.loads((Path(sub_a) / "רילס/capcut-layout.json").read_text())
    lb = json.loads((Path(sub_b) / "רילס/capcut-layout.json").read_text())
    off = shift / 1e6
    rs = la["reels"] + [dict(r, start=round(r["start"] + off, 6), end=round(r["end"] + off, 6)) for r in lb["reels"]]
    (Path(session) / "רילס/capcut-layout.json").write_text(json.dumps({"project": base_name, "reels": rs}, ensure_ascii=False, indent=1), encoding="utf-8")
    # the appended project: off the home screen, into the Trash (recoverable)
    reels._registry_remove(add_name)
    subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{B}"'], check=True, capture_output=True)
    print(json.dumps({"project": base_name, "duration_s": round(da["duration"] / 1e6, 1), "reels": len(rs), "tracks": len(da["tracks"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
