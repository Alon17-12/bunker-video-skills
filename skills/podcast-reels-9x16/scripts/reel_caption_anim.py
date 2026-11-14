# -*- coding: utf-8 -*-
"""Give every caption card an entrance animation from CapCut's own cache (text_anim_donors.json) — the
"animated captions" Alon asked for on 0923 r8 («לא הכנסת בכלל הנפשה לכתוביות»). One wrapper per segment
(fresh ids), `duration` in µs; a card shorter than the animation gets a proportionally shorter one.

    python reel_caption_anim.py "<project>" [--in Grow] [--dur 0.14] [--track כתוביות] [--write]

Kinds cached on this machine for text: Grow · Fade In · Showing Up · Dissolve. Grow = a quick pop, the
karaoke-adjacent feel without word-level timing. Idempotent: existing animation refs on the track are
replaced. Read-only without --write.
"""
import argparse, copy, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000; SP = os.path.dirname(os.path.abspath(__file__)); AN = json.load(open(os.path.join(SP, "..", "references", "text_anim_donors.json")))
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--in", dest="kind", default="Grow"); ap.add_argument("--dur", type=float, default=0.14); ap.add_argument("--track", default="כתוביות"); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); mats = d["materials"]; nid = lambda: str(uuid.uuid4()).upper()
key = f"in:{A.kind}"; assert key in AN["anims"], f"no cached animation {key}; have {list(AN['anims'])}"
assert os.path.exists(AN["anims"][key]["path"]), "donor cache missing on disk — use it once in CapCut to re-cache"
track = next(t for t in d["tracks"] if t.get("name") == A.track); mats.setdefault("material_animations", [])
old = {r for s in track["segments"] for r in s.get("extra_material_refs", [])}
anim_ids = {m["id"] for m in mats["material_animations"]}; dead = old & anim_ids
mats["material_animations"] = [m for m in mats["material_animations"] if m["id"] not in dead]
n = 0
for s in track["segments"]:
    s["extra_material_refs"] = [r for r in s.get("extra_material_refs", []) if r not in dead]
    w = copy.deepcopy(AN["wrapper"]); w["id"] = nid(); a = copy.deepcopy(AN["anims"][key]); a["duration"] = int(min(A.dur, 0.6 * s["target_timerange"]["duration"] / US) * US); w["animations"] = [a]
    mats["material_animations"].append(w); s["extra_material_refs"].append(w["id"]); n += 1
print(f"{A.kind} {A.dur}s on {n} cards of {A.track!r} (replaced {len(dead)} old wrappers)")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
