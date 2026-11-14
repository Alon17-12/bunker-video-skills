# -*- coding: utf-8 -*-
"""Give a reel's captions the house stroke + shadow (המלצות הבונקר 646 cards, אורח E, אורח F, לקוח I): a black
outline `strokes[0].width 0.0353` and one hard black shadow `distance 8 · angle −45 · alpha 0.65 · diffuse 0`, written
into `content.styles[]` AND mirrored on the material (`border_width`, `shadow_*`, `shadow_point = d × 0.1272792`).

A caption that carries a CapCut text EFFECT (`styles[].effectStyle`, e.g. 7336838446625082629 on 0923) is owned by
the effect — its outline/shadow cannot be strengthened from the sliders, and strokes injected BESIDE it render as a
double line (0810: «זוועה»). So the effect is REMOVED first: house look = effect OR stroke+shadow, never both
(gotchas: «Verify the style you cloned»). 0923 r10: Alon «דייק את הכתוביות עם הצללה ומסגרת — יותר הפרדה מהרקע».

    python reel_caption_stroke.py "<project>" [--tracks כתוביות] [--stroke 0.0353] [--distance 8] [--alpha 0.65] [--write]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--tracks", default="כתוביות"); ap.add_argument("--stroke", type=float, default=0.035278912633657455)
ap.add_argument("--distance", type=float, default=8.0); ap.add_argument("--alpha", type=float, default=0.649999976158142); ap.add_argument("--angle", type=float, default=-45.0); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); tm = {m["id"]: m for m in d["materials"]["texts"]}
names = [x.strip() for x in A.tracks.split(",")]; K = 0.1272792
BLACK = {"solid": {"color": [0, 0, 0]}, "render_type": "solid"}
stroke = {"width": A.stroke, "mode": 0, "content": BLACK}; shadow = {"diffuse": 0, "angle": A.angle, "content": BLACK, "distance": A.distance, "alpha": A.alpha}
seen = set(); n_eff = n_mat = 0
for t in d["tracks"]:
    if t["type"] != "text" or (t.get("name") or "") not in names: continue
    for s in t["segments"]:
        m = tm[s["material_id"]]
        if m["id"] in seen: continue
        seen.add(m["id"]); c = json.loads(m["content"])
        for st in c["styles"]:
            if st.pop("effectStyle", None) is not None: n_eff += 1
            st["strokes"] = [json.loads(json.dumps(stroke))]; st["shadows"] = [json.loads(json.dumps(shadow))]
        m["content"] = json.dumps(c, ensure_ascii=False)
        m.update({"has_shadow": True, "border_width": A.stroke, "border_color": "#000000", "border_alpha": 1.0, "border_mode": 0,
                  "shadow_color": "#000000", "shadow_alpha": A.alpha, "shadow_angle": A.angle, "shadow_distance": A.distance, "shadow_smoothing": 0.0,
                  "shadow_point": {"x": A.distance * K, "y": -A.distance * K}, "background_style": 0, "background_color": ""})
        n_mat += 1
    print(f"  track {t.get('name')!r}: {len(t['segments'])} segments")
print(f"materials {n_mat} · effectStyle removed from {n_eff} style ranges · stroke {A.stroke:.4f} · shadow d{A.distance:g} a{A.alpha:.2f} ∠{A.angle:g}")
# contradiction check — never an effect next to strokes
bad = [m["id"] for m in tm.values() if m["id"] in seen and any(st.get("effectStyle") for st in json.loads(m["content"])["styles"])]
assert not bad, f"effect still present on {len(bad)}"
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
