#!/usr/bin/env python3
"""Camera flashes in a reels project — find, and fix into a new version (Alon, אלון+אייל+דולב 21.10.2026: «קפיצה של הפריים
בצורה לא נקייה וחדה — חשוב שלא יהיו קפיצות כאלה»).

    capcut_flash_fix.py "<project>"                      # report only
    capcut_flash_fix.py "<project>" "<new project>"      # copy + fix (CapCut closed)

What is on screen at t: the split (track «מסך משולב») if a split clip covers t, else camera 1 if its clip on the
«מצלמה 1» track has opacity 1, else camera 2 (main track); photos on the main track = divider cards.
A run of one camera shorter than --flash (0.5 s) between two runs of the other camera, or between a split / card and the
other camera, takes the camera around it — by setting the camera-1 clip's opacity on the clips under that run.
Exit 1 when the report finds a flash.
"""
import argparse, json, os, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402
import reels  # noqa: E402

US = 1_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst", nargs="?"); ap.add_argument("--flash", type=float, default=0.5)
    ap.add_argument("--in-place", action="store_true", help="write into the project itself (only a version of ours he has not opened)")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.src
    d = json.loads(capcut._draft_file(P).read_text())
    mats = {m["id"]: m for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
    vt = [t for t in d["tracks"] if t["type"] == "video"]
    top = next(t for t in vt if (t.get("name") or "").startswith("מצלמה 1"))
    main_t = next(t for t in vt if not t.get("name"))
    split = next((t for t in vt if t.get("name") == "מסך משולב"), {"segments": []})
    st = lambda s: s["target_timerange"]["start"]
    en = lambda s: st(s) + s["target_timerange"]["duration"]
    edges = sorted({x for t in (top, main_t, split) for s in t["segments"] for x in (st(s), en(s))})

    import bisect

    def index(segs, keep=lambda s: True):
        ss = sorted((s for s in segs if keep(s)), key=st)
        return ss, [st(s) for s in ss]
    SP = index(split["segments"], lambda s: s["clip"]["alpha"] > 0.5)
    CARD = index(main_t["segments"], lambda s: mats.get(s["material_id"], {}).get("type") == "photo")
    TOP = index(top["segments"])

    def at(ix, t):
        ss, keys = ix
        i = bisect.bisect_right(keys, t) - 1
        return ss[i] if i >= 0 and t < en(ss[i]) else None

    def view(t):
        if at(SP, t):
            return "split"
        if at(CARD, t):
            return "card"
        s = at(TOP, t)
        if s:
            return 1 if s["clip"]["alpha"] > 0.5 else 2
        return 2

    def runs():
        out = []
        for x, y in zip(edges, edges[1:]):
            v = view((x + y) // 2)
            if out and out[-1][0] == v:
                out[-1][2] = y
            else:
                out.append([v, x, y])
        return out

    # a camera cut within 0.1 s of a split's edge moves onto the edge (merged builds drifted 1–2 frames: «שעת צילום» v4 —
    # 1 frame of camera 2 before the split, 2 after). The cut moves, not the split: the split clip is rendered to its exact length.
    edges_sp = sorted({x for s in split["segments"] for x in (st(s), en(s))})
    moved = 0
    for e in edges_sp:
        for tr in (top, main_t):
            ss = sorted(tr["segments"], key=st)
            for p_, q_ in zip(ss, ss[1:]):
                c = st(q_)
                if c != e and abs(c - e) <= 100_000 and abs(en(p_) - c) < 1000:
                    dlt = e - c
                    p_["target_timerange"]["duration"] += dlt; p_["source_timerange"]["duration"] += dlt
                    q_["target_timerange"]["start"] += dlt; q_["target_timerange"]["duration"] -= dlt
                    q_["source_timerange"]["start"] += dlt; q_["source_timerange"]["duration"] -= dlt
                    moved += 1
    if moved:
        print(f"קאטים הוזזו לקצה המסך המשולב: {moved}")
        TOP = index(top["segments"]); CARD = index(main_t["segments"], lambda s: mats.get(s["material_id"], {}).get("type") == "photo")
        edges = sorted({x for t in (top, main_t, split) for s in t["segments"] for x in (st(s), en(s))})
    found, stuck = [], set()
    changed = True
    while changed and len(found) < 500:
        changed = False
        rr = runs()
        for i, (v, x, y) in enumerate(rr):
            if x in stuck:
                continue
            if v not in (1, 2) or y - x >= a.flash * US:
                continue
            p = rr[i - 1][0] if i else None
            n = rr[i + 1][0] if i + 1 < len(rr) else None
            p = p if p in (1, 2) else None
            n = n if n in (1, 2) else None
            take = p if p and (p == n or n is None) else (n if p is None and n else None)
            if not take or take == v:
                continue
            hit = [s for s in top["segments"] if st(s) < y and en(s) > x]
            if not hit or view((x + y) // 2) == take:
                stuck.add(x); continue
            found.append({"t": round(x / US, 3), "frames": round((y - x) / US * 30), "cam": v, "to": take})
            for s in hit:
                s["clip"]["alpha"] = 1.0 if take == 1 else 0.0
            if view((x + y) // 2) != take:            # the layer under it decides (no camera-1 clip there) — report, don't loop
                stuck.add(x); found[-1]["unfixed"] = True
            changed = True
            break
    # every video clip on the 30 fps grid (a clip edge between two frames = one frame of the layer under it)
    grid = 0
    for t in vt:
        for s in t["segments"]:
            a0, b0 = st(s), en(s)
            g0, g1 = int(round(round(a0 * 30 / US) * US / 30)), int(round(round(b0 * 30 / US) * US / 30))
            if (g0, g1) != (a0, b0):
                grid += 1
                s["source_timerange"]["start"] = max(0, s["source_timerange"]["start"] + g0 - a0)
                s["target_timerange"] = {"start": g0, "duration": g1 - g0}
                s["source_timerange"]["duration"] = g1 - g0
    print(json.dumps({"project": a.src, "off_grid_clips": grid, "flashes": found}, ensure_ascii=False, indent=1))
    if a.in_place:
        if capcut.capcut_running():
            raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
        capcut._atomic_write(P, d)
        print(json.dumps({"project": a.src, "written": True}, ensure_ascii=False))
        return
    if not a.dst:
        sys.exit(1 if found or grid else 0)
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    name = reels._unique_name(a.dst)
    dst = capcut.DRAFTS_DIR / name
    dst.mkdir()                                    # media hard-linked (6 GB of cameras, same disk), the rest copied
    for item in P.iterdir():
        if item.name.startswith(capcut.BACKUP_PREFIX) or item.suffix in (".tmp", ".bak"):
            continue
        if item.name == "ccstudio-media":
            (dst / item.name).mkdir()
            for f in item.iterdir():
                os.link(f, dst / item.name / f.name)
        elif item.is_dir():
            shutil.copytree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)
    d = json.loads(json.dumps(d).replace(str(P) + "/", str(dst) + "/"))
    capcut._atomic_write(dst, d)
    meta_p = dst / "draft_meta_info.json"
    meta = json.loads(meta_p.read_text()); meta_id = capcut._new_id(); now = int(time.time() * US)
    meta.update({"draft_id": meta_id, "draft_name": name, "draft_fold_path": str(dst), "tm_draft_create": now, "tm_draft_modified": now})
    meta_p.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta_id, int(d["duration"]), a.src)
    print(json.dumps({"project": name, "fixed": len(found)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
