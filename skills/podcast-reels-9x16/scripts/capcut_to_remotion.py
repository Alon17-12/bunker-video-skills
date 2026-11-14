# -*- coding: utf-8 -*-
"""Translate a CapCut reels draft into per-reel layer JSON for the Remotion `DraftReel` component — the edit decisions
(cuts, angle switches, keyframes, b-roll, titles, captions, audio) leave CapCut and render pixel-exact in Remotion.

Why (05.10): Alon, after the Client M reels were rebuilt in Remotion: «לערוך מחדש את הסרטונים שערכנו לי בקאפקאט, הפעם רק
דרך remotion». CapCut cannot be rendered headless and its text/alpha behaviour can't be verified before export;
Remotion can. This keeps every approved decision and only swaps the renderer.

    python capcut_to_remotion.py "<project>" --out <dir> [--public <remotion public subdir>] [--lut-files cam1=…,cam2=…]

Blocks: one reel per footage stretch between the white title cards (photo segments on track 0); the card itself is
dropped (it existed only so he could split the export). Times are reel-local seconds. Geometry stays CapCut's:
fit = min(W/w, H/h), size = w·fit·scale, centre = (W/2 + tx·W/2, H/2 − ty·H/2). Video keyframe `time_offset` is
SOURCE time → converted to segment-local; text keyframes are already segment-local. A Compound clip is expanded into
its inner tracks at the compound's z. Layers under the adjust track get `lut: true` (bake the cube into those files).
CapCut's Remove-background on a segment (`matting.flag`) is exported as a `matte` dir of 8-bit masks named by source µs.
Missing files (library audio that only lives in CapCut's cache) are listed under `missing`, never silently dropped.
"""
import argparse, json, os, sys
US = 1e6
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--out", required=True); A = ap.parse_args()
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text())
W, H = d["canvas_config"]["width"], d["canvas_config"]["height"]

def res(p):
    if p and p.startswith("##_draftpath_placeholder"): return str(D / p.split("_##/", 1)[1])
    return p or ""

def index(draft):
    return {m["id"]: (k, m) for k, v in draft["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}

def keys_of(seg, src0, speed, is_video):
    out = {}
    names = {"KFTypeScaleX": "scale", "KFTypePositionX": "tx", "KFTypePositionY": "ty", "KFTypeRotation": "rot", "KFTypeAlpha": "alpha"}
    for g in seg.get("common_keyframes", []):
        n = names.get(g["property_type"])
        if not n: continue
        ks = []
        for k in g["keyframe_list"]:
            v = k["values"][0]; v = v["value"] if isinstance(v, dict) else v
            t = (k["time_offset"] - src0) / US / speed if is_video else k["time_offset"] / US
            ks.append([round(t, 4), v, k.get("curveType", "Line")])
        out[n] = sorted(ks)
    return out

def anims_of(seg, idx):
    a = []
    for r in seg.get("extra_material_refs", []):
        if r in idx and idx[r][0] == "material_animations":
            for x in idx[r][1].get("animations", []): a.append({"name": x["name"], "type": x["type"], "dur": x["duration"] / US})
        if r in idx and idx[r][0] == "transitions": a.append({"name": idx[r][1].get("name"), "type": "transition", "dur": idx[r][1].get("duration", 0) / US})
    return a

def clip_geom(seg):
    c = seg.get("clip") or {}
    return {"scale": c.get("scale", {}).get("x", 1.0), "tx": c.get("transform", {}).get("x", 0.0), "ty": c.get("transform", {}).get("y", 0.0),
            "rot": c.get("rotation", 0.0), "alpha": c.get("alpha", 1.0), "flipH": c.get("flip", {}).get("horizontal", False)}

# ---- blocks: footage between the white cards on track 0
t0track = d["tracks"][0]; idx0 = index(d)
cards = sorted((s for s in t0track["segments"] if idx0.get(s["material_id"], ("", {}))[1].get("type") == "photo"), key=lambda s: s["target_timerange"]["start"])
ends = [ (c["target_timerange"]["start"] + c["target_timerange"]["duration"]) / US for c in cards]
starts = [c["target_timerange"]["start"] / US for c in cards[1:]] + [d["duration"] / US]
blocks = list(zip(ends, starts))
adj_z = next((i for i, t in enumerate(d["tracks"]) if t["type"] == "adjust"), None)

def walk(draft, z_base, offset, win, R0, subz=0.0):
    """yield layer dicts for one (sub)draft; offset maps this draft's time to the outer timeline"""
    idx = index(draft)
    for ti, t in enumerate(draft["tracks"]):
        z = z_base if draft is not d else ti
        for s in sorted(t["segments"], key=lambda s: s["target_timerange"]["start"]):
            a = s["target_timerange"]["start"] / US + offset; b = a + s["target_timerange"]["duration"] / US
            lo, hi = max(a, win[0]), min(b, win[1])
            if hi - lo < 1e-3: continue
            kind, m = idx.get(s["material_id"], (None, {}))
            speed = s.get("speed", 1.0) or 1.0
            src0 = (s.get("source_timerange") or {}).get("start", 0) / US
            cut_in = lo - a
            base = {"z": z + subz, "track": t.get("name") or t["type"], "t0": round(lo - R0, 4), "t1": round(hi - R0, 4), "segStart": round(a - R0, 4)}
            if t["type"] == "video" and kind == "videos":
                if m.get("type") == "video" and not m.get("path") and any(idx[r][0] == "drafts" for r in s.get("extra_material_refs", []) if r in idx):
                    inner = next(idx[r][1]["draft"] for r in s["extra_material_refs"] if r in idx and idx[r][0] == "drafts")
                    for k, L in enumerate(walk(inner, z, a - src0, (lo, hi), R0, 0.0)):
                        L["z"] = z + 0.01 * (L.pop("_innerz", 0) + 1); L["compound"] = True; yield L
                    continue
                L = dict(base, kind="image" if m.get("type") == "photo" else "video", file=res(m.get("path")), w=m.get("width"), h=m.get("height"),
                         src=round(src0 + cut_in * speed, 4), speed=speed, volume=s.get("volume", 1.0), geom=clip_geom(s),
                         keys=keys_of(s, src0, speed, True), anims=anims_of(s, idx), lut=(draft is d and adj_z is not None and ti < adj_z) or (draft is not d and z < (adj_z or 99)),
                         keyShift=round(cut_in, 4))
                mt = m.get("matting") or {}
                if mt.get("flag"): L["matte"] = res(mt.get("path"))
                if draft is not d: L["_innerz"] = ti
                yield L
            elif t["type"] == "audio" and kind == "audios":
                p = res(m.get("path"))
                yield dict(base, kind="audio", file=p, name=m.get("name"), exists=os.path.exists(p), src=round(src0 + cut_in * speed, 4), speed=speed, volume=s.get("volume", 1.0),
                           fades=[x for x in anims_of(s, idx)], fade=next(({"in": idx[r][1].get("fade_in_duration", 0) / US, "out": idx[r][1].get("fade_out_duration", 0) / US} for r in s.get("extra_material_refs", []) if r in idx and idx[r][0] == "audio_fades"), None))
            elif t["type"] == "text" and kind == "texts":
                c = json.loads(m["content"])
                yield dict(base, kind="text", text=c["text"], styles=[{"range": st.get("range"), "color": st["fill"]["content"]["solid"]["color"], "size": st.get("size"),
                           "font": os.path.basename((st.get("font") or {}).get("path", "")), "stroke": [{"w": x.get("width"), "color": x["content"]["solid"]["color"]} for x in st.get("strokes", [])],
                           "shadow": [{"d": x.get("distance"), "angle": x.get("angle"), "alpha": x.get("alpha"), "color": x["content"]["solid"]["color"]} for x in st.get("shadows", [])]} for st in c.get("styles", [])],
                           fontSize=m.get("font_size"), align=m.get("alignment"), lineMax=m.get("line_max_width"), geom=clip_geom(s), keys=keys_of(s, 0, 1, False), anims=anims_of(s, idx), keyShift=round(cut_in, 4),
                           globalAlpha=m.get("global_alpha", 1.0))

os.makedirs(A.out, exist_ok=True); summary = []
for n, (a, b) in enumerate(blocks, 1):
    layers = list(walk(d, 0, 0.0, (a, b), a))
    vis = [L for L in layers if L["kind"] in ("video", "image")]
    # sound carried by video segments (the camera mic) becomes an audio layer of its own
    for L in vis:
        if L["kind"] == "video" and (L.get("volume") or 0) > 0.01:
            layers.append({"kind": "audio", "z": L["z"], "track": L["track"] + " (video audio)", "t0": L["t0"], "t1": L["t1"], "file": L["file"], "exists": os.path.exists(L["file"]),
                           "src": L["src"], "speed": L["speed"], "volume": L["volume"], "fade": None, "fades": [], "fromVideo": True})
    missing = sorted({(L.get("name") or os.path.basename(L["file"])) for L in layers if L["kind"] == "audio" and not L.get("exists")})
    out = {"id": n, "dur": round(b - a, 4), "width": W, "height": H, "layers": layers, "missing": missing}
    json.dump(out, open(os.path.join(A.out, f"reel{n}.json"), "w"), ensure_ascii=False, indent=0)
    cnt = {}
    for L in layers: cnt[L["kind"]] = cnt.get(L["kind"], 0) + 1
    print(f"reel {n}: {a:.2f}–{b:.2f} ({b - a:.2f}s) layers {cnt} · missing {missing}")
