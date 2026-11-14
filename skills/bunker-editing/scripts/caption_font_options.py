#!/usr/bin/env python3
"""Font options for Alon to choose from (25.10.2026: «אני רוצה להחליף את הפונט — שים בסרטון הראשון 3 שכבות של כתוביות
אופציונאליות, עדיף מהחדשות ביותר שהורדנו»). The captions of one video are copied onto one track per font, each track
HIDDEN (eye off, attribute 2) so he turns one on at a time; the size is matched so a line keeps its width.

    caption_font_options.py "<project>" T_END "Name=file.ttf" … [--write]
"""
import copy, json, sys
from pathlib import Path
from PIL import ImageFont
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

FONTS = Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts"
name, t_end = sys.argv[1], float(sys.argv[2]); opts = [x.split("=", 1) for x in sys.argv[3:] if "=" in x]
P = capcut.DRAFTS_DIR / name; d = json.loads(capcut._draft_file(P).read_text())
tm = {m["id"]: m for m in d["materials"]["texts"]}
allm = {x["id"]: k for k, v in d["materials"].items() if isinstance(v, list) for x in v if isinstance(x, dict) and "id" in x}
main = next(t for t in d["tracks"] if t["type"] == "text" and t.get("name") == "כתוביות")
segs = sorted([s for s in main["segments"] if s["target_timerange"]["start"] < t_end * 1e6], key=lambda s: s["target_timerange"]["start"])
sample = " ".join(json.loads(tm[s["material_id"]]["content"])["text"].replace("\n", " ") for s in segs[:40])
cur_font = tm[segs[0]["material_id"]]["font_path"]
width = lambda f: ImageFont.truetype(f, 60).getlength(sample)
w0 = width(cur_font)
d["tracks"] = [t for t in d["tracks"] if not (t["type"] == "text" and (t.get("name") or "").startswith("אפשרות פונט"))]
at = d["tracks"].index(main) + 1
for k, (label, file) in enumerate(opts, 1):
    fp = str(FONTS / file); assert Path(fp).exists(), fp
    ratio = max(0.8, min(1.45, w0 / width(fp)))
    tr = {"attribute": 2, "flag": 0, "id": capcut._new_id(), "is_default_name": False, "name": f"אפשרות פונט {k} · {label}", "segments": [], "type": "text"}
    for s in segs:
        n = copy.deepcopy(s); n["id"] = capcut._new_id()
        m = copy.deepcopy(tm[s["material_id"]]); m["id"] = capcut._new_id(); m["font_path"] = fp
        m["font_size"] = round(m.get("font_size", 11) * ratio, 2)
        ct = json.loads(m["content"])
        for st in ct["styles"]:
            st["font"] = {"path": fp, "id": ""}; st["size"] = round(st.get("size", m["font_size"]) * ratio, 2)
        m["content"] = json.dumps(ct, ensure_ascii=False)
        for key in ("font_id", "font_resource_id", "font_name", "font_title"):
            if key in m: m[key] = ""
        d["materials"]["texts"].append(m); n["material_id"] = m["id"]
        refs = []
        for r in s.get("extra_material_refs", []):
            lst = allm.get(r)
            if lst:
                e = copy.deepcopy(next(x for x in d["materials"][lst] if x["id"] == r)); e["id"] = capcut._new_id(); d["materials"][lst].append(e); refs.append(e["id"])
        n["extra_material_refs"] = refs
        tr["segments"].append(n)
    d["tracks"].insert(at, tr); at += 1
    print(f"{tr['name']}: {len(tr['segments'])} כתוביות, גודל ×{ratio:.2f}")
if "--write" in sys.argv:
    if capcut.capcut_running():
        raise SystemExit("⛔ CapCut פתוח")
    capcut._backup(P); capcut._atomic_write(P, d); print("✓ נכתב")
