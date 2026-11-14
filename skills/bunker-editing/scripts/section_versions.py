#!/usr/bin/env python3
"""Turn one section of Alon's own project into N versions, in place (תוכן הבונקר לממומן, 24.10.2026: «הוק 1 / הוק 2 /
סגיר 2» markers on one sequence → two finished videos, hook1+body+closing1 and hook2+body+closing2).

    section_versions.py "<project>" <from_s> <to_s> versions.json [--write]

versions.json: {"versions": [[[src_from, src_to, "mark title"?], …], …]} — camera-clock source ranges of the take the
section already uses (cam1 on track 0, cam2 on track 1, the same file pair). The section's clips are replaced by the
versions back to back, one of HIS separator images between them; everything after the section moves by the
difference on every track (adjust layers that span it grow). A source range carrying a mark title gets that mark
(materials.time_marks, the ones he set) so his markers stay on their clips. CapCut must be closed.
"""
import argparse, copy, json, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

US = 1_000_000
fr = lambda t: int(round(round(t * 30) * US / 30))        # 30 fps grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("t_from", type=float); ap.add_argument("t_to", type=float); ap.add_argument("plan")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--clear", action="store_true", help="drop what other tracks hold inside the section (captions/dialogue/arrows) instead of refusing — they are rebuilt after")
    a = ap.parse_args()
    P = capcut.DRAFTS_DIR / a.project
    d = json.loads(capcut._draft_file(P).read_text())
    mats = d["materials"]
    vids = {m["id"]: m for m in mats["videos"]}
    marks = {it["title"]: m["id"] for m in mats.get("time_marks", []) for it in m.get("mark_items", [])}
    mark_ids = set(marks.values())
    by_list = {e["id"]: k for k, v in mats.items() if isinstance(v, list) for e in v if isinstance(e, dict) and "id" in e}
    A, B = int(a.t_from * US), int(a.t_to * US)
    t0, t1 = d["tracks"][0], d["tracks"][1]
    st = lambda s: s["target_timerange"]["start"]
    is_img = lambda s: vids.get(s["material_id"], {}).get("type") == "photo"
    sec0 = [s for s in t0["segments"] if A - 1000 <= st(s) < B - 1000 and not is_img(s)]
    sec1 = [s for s in t1["segments"] if A - 1000 <= st(s) < B - 1000]
    tpl0, tpl1 = sec0[0], sec1[0]
    sep = next(s for s in sorted(t0["segments"], key=st) if is_img(s) and st(s) >= B - 1000)
    plan = json.loads(Path(a.plan).read_text())["versions"]
    rr = lambda r: r["src"] if isinstance(r, dict) else r

    def clone(tpl, src_from, dur_us, at_us, mark=None):
        s = copy.deepcopy(tpl); s["id"] = capcut._new_id()
        refs = []
        for r in tpl.get("extra_material_refs", []):
            if r in mark_ids:
                continue
            lst = by_list.get(r)
            if not lst:
                continue
            e = copy.deepcopy(next(x for x in mats[lst] if x.get("id") == r)); e["id"] = capcut._new_id(); mats[lst].append(e); refs.append(e["id"])
        if mark:
            refs.append(marks[mark])
        s["extra_material_refs"] = refs
        s["target_timerange"] = {"start": at_us, "duration": dur_us}
        if s.get("source_timerange") is not None:
            s["source_timerange"] = {"start": fr(src_from), "duration": dur_us}
        return s

    new0, new1, t = [], [], A
    for vi, ver in enumerate(plan):
        if vi:
            sd = sep["target_timerange"]["duration"]
            new0.append(clone(sep, 0, sd, t)); new0[-1]["source_timerange"] = copy.deepcopy(sep["source_timerange"]); t += sd
        for rng in ver:
            if isinstance(rng, dict):                 # {"src": [f, g], "mark": "...", "tpl_at": <timeline s of a clip of ANOTHER take>}
                f, g = rng["src"]; mark = rng.get("mark")
                ta = int(rng["tpl_at"] * US)
                pick = lambda tr: next(x for x in tr["segments"] if st(x) <= ta < st(x) + x["target_timerange"]["duration"] and not is_img(x))
                c0, c1 = pick(t0), pick(t1)
            else:
                f, g = rng[0], rng[1]; mark = rng[2] if len(rng) > 2 else None
                c0, c1 = tpl0, tpl1
            du = fr(g) - fr(f)
            new0.append(clone(c0, f, du, t)); new1.append(clone(c1, f, du, t, mark)); t += du
    delta = t - B
    print(json.dumps({"section": [a.t_from, a.t_to], "old_s": round((B - A) / US, 2), "new_s": round((t - A) / US, 2), "shift_after_s": round(delta / US, 2),
                      "versions": [round(sum(fr(rr(r)[1]) - fr(rr(r)[0]) for r in v) / US, 2) for v in plan]}, ensure_ascii=False))
    for m in [(r.get("mark") if isinstance(r, dict) else (r[2] if len(r) > 2 else None)) for v in plan for r in v]:
        if m is None:
            continue
        if m not in marks:
            raise SystemExit(f"⛔ אין סימון בשם «{m}» בפרויקט")
    # nothing else may live inside the section (captions/dialogue/arrows there would be orphaned)
    inside = [s for tr in d["tracks"][2:] if tr["type"] != "adjust" for s in tr["segments"] if A - 1000 <= st(s) < B - 1000]
    if inside and a.clear:
        drop = {s["id"] for s in inside}
        for tr in d["tracks"][2:]:
            tr["segments"] = [s for s in tr["segments"] if s["id"] not in drop]
        print(f"   נוקו {len(drop)} מקטעים בתוך הקטע (ייבנו מחדש)")
    for tr in d["tracks"][2:]:
        for s in tr["segments"]:
            if tr["type"] != "adjust" and A <= st(s) < B:
                raise SystemExit(f"⛔ במסלול {tr['type']} «{tr.get('name')}» יש מקטע בתוך הקטע ({st(s) / US:.2f}) — קודם לבנות גרסאות, אחר כך לערוך")
    if not a.write:
        print("(יבש — בלי --write לא נכתב כלום)"); return
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.")
    gone = {s["id"] for s in sec0 + sec1}
    for tr in d["tracks"]:
        keep = []
        for s in tr["segments"]:
            if s["id"] in gone:
                continue
            if st(s) >= B - 1000:
                s["target_timerange"]["start"] += delta
            elif tr["type"] == "adjust" and st(s) + s["target_timerange"]["duration"] >= B - 1000:
                s["target_timerange"]["duration"] += delta
            keep.append(s)
        tr["segments"] = keep
    t0["segments"] = sorted(t0["segments"] + new0, key=st)
    t1["segments"] = sorted(t1["segments"] + new1, key=st)
    for tr in (t0,):
        for p, q in zip(tr["segments"], tr["segments"][1:]):
            assert st(p) + p["target_timerange"]["duration"] <= st(q) + 1000, f"overlap at {st(q) / US:.2f}"
    d["duration"] = int(d["duration"]) + delta
    capcut._backup(P); capcut._atomic_write(P, d)
    print("✓ נכתב")


if __name__ == "__main__":
    main()
