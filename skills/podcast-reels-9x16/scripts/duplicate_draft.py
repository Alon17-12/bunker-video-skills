"""Duplicate a CapCut project on disk so a rebuild can be tried without touching the original.

    python duplicate_draft.py "<source folder>" "<new folder / display name>" [--write]

CapCut derives the display name from the FOLDER name on every save, so the new folder IS the new
name. Three identities change: `draft_info.json → id`, `draft_meta_info.json → draft_id`, and the
entry appended to `root_meta_info.json` (which CapCut reads only at launch — so CapCut must be
fully quit, and the copy appears on the home screen after the next start).

The `##_draftpath_placeholder_<uuid>_##` prefix inside media paths is CapCut's constant for "this
draft's own folder" (identical across drafts on this machine), so media that lives in the folder
keeps working in the copy. Backups (`draft_info.ccstudio-backup-*`, `*.prev.mp4`, `*.orig.mp4`)
are not copied.
"""
import argparse, json, os, re, shutil, sys, time, uuid
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut

SKIP = re.compile(r"(draft_info\.ccstudio-backup-.*\.json|\.(prev|orig)\.mp4|draft_meta_info\.ccstudio-backup-.*\.json|\.tmp)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    root = capcut.DRAFTS_DIR; src, dst = root / a.src, root / a.dst
    if not src.is_dir(): sys.exit(f"no such draft folder: {src}")
    if dst.exists(): sys.exit(f"target exists: {dst}")
    files = [p for p in src.rglob("*") if p.is_file() and not SKIP.search(p.name)]
    size = sum(p.stat().st_size for p in files)
    print(f"{len(files)} files, {size / 1e6:.0f} MB → {dst}")
    if not a.write: print("dry run — pass --write"); return
    if capcut._capcut_pid() is not None: sys.exit("CapCut is running — quit it (⌘Q) first; the registry is read at launch.")

    dst.mkdir()
    for p in files:
        q = dst / p.relative_to(src); q.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, q)
    new_id = str(uuid.uuid4()).upper(); now_us = int(time.time() * 1e6)

    di = dst / "draft_info.json"; d = json.loads(di.read_text()); d["id"] = str(uuid.uuid4()).upper()
    di.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))

    mi = dst / "draft_meta_info.json"; m = json.loads(mi.read_text())
    m.update({"draft_id": new_id, "draft_name": a.dst, "draft_fold_path": str(dst), "draft_root_path": str(root),
              "draft_cover": str(dst / "draft_cover.jpg"), "tm_draft_create": now_us, "tm_draft_modified": now_us})
    for k in ("tm_draft_cloud_completed", "tm_draft_cloud_entry_id", "tm_draft_cloud_modified", "tm_draft_cloud_parent_entry_id",
              "tm_draft_cloud_space_id", "tm_draft_cloud_user_id"):
        if k in m: m[k] = "" if isinstance(m[k], str) else -1 if "id" in k else 0
    for blk in m.get("draft_materials") or []:                          # media that lived in the source folder now lives in the copy
        for v in blk.get("value") or []:
            fp = v.get("file_Path", "")
            if fp.startswith(str(src) + "/"): v["file_Path"] = str(dst) + fp[len(str(src)):]
    mi.write_text(json.dumps(m, ensure_ascii=False, indent=2))

    reg = root / "root_meta_info.json"; r = json.loads(reg.read_text())
    (root / f"root_meta_info.ccstudio-backup-{int(time.time())}.json").write_text(reg.read_text())
    e = next(x for x in r["all_draft_store"] if x.get("draft_fold_path") == str(src))
    e = dict(e); e.update({"draft_id": new_id, "draft_name": a.dst, "draft_fold_path": str(dst), "draft_json_file": str(dst / "draft_info.json"),
                           "draft_cover": str(dst / "draft_cover.jpg"), "tm_draft_create": now_us, "tm_draft_modified": now_us,
                           "tm_draft_cloud_entry_id": -1, "tm_draft_cloud_modified": 0, "tm_draft_cloud_parent_entry_id": -1,
                           "tm_draft_cloud_space_id": -1, "tm_draft_cloud_user_id": -1, "tm_draft_cloud_completed": ""})
    r["all_draft_store"].insert(0, e)
    if isinstance(r.get("draft_ids"), int): r["draft_ids"] += 1
    tmp = reg.with_suffix(".json.tmp"); tmp.write_text(json.dumps(r, ensure_ascii=False)); json.loads(tmp.read_text()); tmp.replace(reg)
    print(f"DUPLICATED → {dst}\n  draft_id {new_id}\n  registered in root_meta_info.json (backup taken)")


if __name__ == "__main__":
    main()
