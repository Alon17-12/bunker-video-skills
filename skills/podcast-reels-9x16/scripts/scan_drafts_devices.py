"""Scan every CapCut draft on this machine for the devices a new build may reuse — and for the ones
that need a cache or a click before they can be injected.

    python scan_drafts_devices.py                 # summary to stdout
    python scan_drafts_devices.py --json out.json # plus a machine-readable dump

Reports, per device, which drafts use it and how it is layered:
  * matting  — "Remove background" on a video material (`videos[].matting.flag`), and whether a text /
               sticker / photo layer sits BETWEEN the matted copy and an unmatted copy of the same
               source ("behind the figure").
  * blur     — the Blur video effect on a segment, and what text is on screen over it.
  * external — photos / videos imported from outside the draft folder and outside the camera drives:
               logos, screenshots, articles, downloaded images. Names and where they came from.
  * stickers, text templates, effect tracks, text effects (name + on disk or not).
The point is measuring how Alon already uses these, so a build copies his composition instead of
inventing one (the split-screen lesson, again).
"""
import argparse, collections, glob, json, os, re, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut

ROOT = capcut.DRAFTS_DIR; US = 1e6
CAMERA_DIRS = ("/Volumes/", "RODECASTER")
PH = re.compile(r"^##_draftpath_placeholder_[^#]*_##")
KIND = [("logo", r"logo|לוגו"), ("screenshot", r"screen ?shot|צילום מסך|Screenshot|מסך"), ("article", r"article|כתבה|news|ynet|globes|calcalist|themarker|haaretz|walla|mako"),
        ("photo", r"\.(jpe?g|png|webp|heic)$"), ("download", r"/Downloads/")]


def classify(path):
    name = os.path.basename(path)
    for k, rx in KIND:
        if re.search(rx, name if k != "download" else path, re.I): return k
    return "other"


def overlaps(a, b): return a[0] < b[1] and b[0] < a[1]


def scan(folder):
    di = folder / "draft_info.json"
    try: d = json.load(open(di))
    except Exception: return None
    mats = d["materials"]; out = {"name": folder.name, "canvas": (d.get("canvas_config") or {}).get("width"), "matting": [], "blur": [], "external": [], "stickers": 0, "text_templates": 0, "effect_tracks": 0, "text_effects": collections.Counter()}
    vids = {m["id"]: m for m in mats.get("videos", []) or []}
    tracks = d["tracks"]
    # every segment with its track order and time span
    segs = []
    for ti, t in enumerate(tracks):
        if t["type"] == "effect": out["effect_tracks"] += 1
        for s in t["segments"]:
            a = s["target_timerange"]["start"] / US; segs.append((ti, t["type"], t.get("name") or "", s, (a, a + s["target_timerange"]["duration"] / US)))
    texts_by_time = [(ti, span, s) for ti, typ, nm, s, span in segs if typ in ("text", "sticker")]
    # matting
    for ti, typ, nm, s, span in segs:
        if typ != "video": continue
        m = vids.get(s["material_id"]);
        if not m: continue
        mt = m.get("matting") or {}
        if mt.get("flag"):
            src = PH.sub("", m.get("path", ""))
            below_text = [(tj, s2["material_id"]) for tj, sp2, s2 in texts_by_time if tj < ti and overlaps(span, sp2)]
            below_same = [tj for tj, typ2, nm2, s2, sp2 in segs if tj < ti and typ2 == "video" and s2["material_id"] != s["material_id"] and PH.sub("", vids.get(s2["material_id"], {}).get("path", "")) == src and overlaps(span, sp2)]
            out["matting"].append({"t": round(span[0], 1), "dur": round(span[1] - span[0], 1), "track": ti, "flag": mt.get("flag"), "behind_text_layers": len(below_text), "unmatted_copy_below": bool(below_same), "src": os.path.basename(src)})
    # blur
    fx = {m["id"]: m for m in mats.get("video_effects", []) or []}
    for ti, typ, nm, s, span in segs:
        if typ == "video":
            for r in s.get("extra_material_refs", []):
                e = fx.get(r)
                if e and e.get("name") == "Blur":
                    over_text = sum(1 for tj, sp2, s2 in texts_by_time if tj > ti and overlaps(span, sp2))
                    out["blur"].append({"t": round(span[0], 1), "dur": round(span[1] - span[0], 1), "amount": next((p["value"] for p in e.get("adjust_params", []) if p["name"] == "effects_adjust_blur"), None), "text_over": over_text, "on_disk": os.path.exists(e.get("path", ""))})
        elif typ == "effect":
            e = fx.get(s["material_id"])
            if e and e.get("name") == "Blur": out["blur"].append({"t": round(span[0], 1), "dur": round(span[1] - span[0], 1), "amount": next((p["value"] for p in e.get("adjust_params", []) if p["name"] == "effects_adjust_blur"), None), "text_over": "effect-track", "on_disk": os.path.exists(e.get("path", ""))})
    # external assets
    used = {s["material_id"] for *_, s, span in segs}
    for m in mats.get("videos", []) or []:
        p = m.get("path", "")
        if not p or p.startswith("##") or str(folder) in p or any(c in p for c in CAMERA_DIRS): continue
        if m["id"] not in used: continue
        out["external"].append({"kind": classify(p), "type": m.get("type"), "name": os.path.basename(p), "dir": os.path.basename(os.path.dirname(p)), "w": m.get("width"), "h": m.get("height"), "exists": os.path.exists(p)})
    out["stickers"] = sum(1 for *_, s, span in segs if s["material_id"] in {m["id"] for m in mats.get("stickers", []) or []})
    out["text_templates"] = len(mats.get("text_templates", []) or [])
    for m in mats.get("effects", []) or []:
        if m.get("type") == "text_effect": out["text_effects"][(m.get("name"), os.path.exists(m.get("path", "")))] += 1
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); a = ap.parse_args()
    rows = [r for r in (scan(f) for f in sorted(ROOT.iterdir()) if f.is_dir()) if r]
    print(f"{len(rows)} drafts scanned\n")
    mt = [r for r in rows if r["matting"]]
    print(f"== matting (Remove background): {len(mt)} drafts, {sum(len(r['matting']) for r in mt)} segments")
    for r in mt:
        behind = [x for x in r["matting"] if x["behind_text_layers"]]
        print(f"  {r['name'][:38]:38} {len(r['matting']):3} segs | behind-the-figure text: {len(behind):2} | unmatted copy below: {sum(x['unmatted_copy_below'] for x in r['matting'])}")
    bl = [r for r in rows if r["blur"]]
    print(f"\n== blur: {len(bl)} drafts, {sum(len(r['blur']) for r in bl)} uses")
    for r in bl:
        print(f"  {r['name'][:38]:38} " + ", ".join(f"{x['t']}s×{x['dur']}s a={x['amount']} text_over={x['text_over']}" for x in r["blur"][:4]))
    ex = [r for r in rows if r["external"]]
    kinds = collections.Counter(x["kind"] for r in ex for x in r["external"])
    print(f"\n== external assets: {len(ex)} drafts, {sum(kinds.values())} files  {dict(kinds)}")
    for r in sorted(ex, key=lambda r: -len(r["external"]))[:40]:
        print(f"  {r['name'][:38]:38} " + " | ".join(f"{x['kind']}:{x['name'][:34]}" for x in r["external"][:6]))
    te = collections.Counter()
    for r in rows: te.update(r["text_effects"])
    print("\n== text effects:", [(n, "✓" if ok else "✗", c) for (n, ok), c in te.most_common(12)])
    print("== stickers:", sum(r["stickers"] for r in rows), "| text templates:", sum(r["text_templates"] for r in rows), "| effect tracks:", sum(r["effect_tracks"] for r in rows))
    if a.json:
        for r in rows: r["text_effects"] = [{"name": n, "on_disk": ok, "count": c} for (n, ok), c in r["text_effects"].items()]
        json.dump(rows, open(a.json, "w"), ensure_ascii=False, indent=1, default=str); print("dump:", a.json)


if __name__ == "__main__":
    main()
