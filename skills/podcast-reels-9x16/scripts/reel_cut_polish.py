# -*- coding: utf-8 -*-
"""Punch hygiene on the base layer after silence cuts (Alon, 0923 round 3 — «קפיצות מוזרות בפריים», «שהקאט יהיה יותר
אלגנטי»). The framing has exactly two sizes (BASE and PUNCH = BASE × 1.08; the intro zoom-out size is allowed only on
the first piece after a card). Rules, in order:
 0. a partial ramp at a piece edge (shorter than 0.3 s — a silence cut that landed inside a punch) is flattened;
 1. a punch-in followed by another size change within --min-hold s is removed (keys take the pre-punch value);
 2. every footage→footage cut gets a size change: the incoming piece is set to the OTHER size until its first
    change that is ≥ --min-hold s away (an earlier punch is absorbed);
 3. any value outside {BASE, PUNCH, intro} is clamped to the nearest — a repair for anything multiplied twice.
Position keys follow the size (× target/current) so the pan keeps the face. Idempotent.

    python reel_cut_polish.py "<project>" [--min-hold 2.5] [--write]
"""
import argparse, collections, json, os, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import capcut
US = 1_000_000
ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--min-hold", type=float, default=2.5); ap.add_argument("--write", action="store_true")
A = ap.parse_args(); D = capcut.DRAFTS_DIR / A.project; d = json.loads((D / "draft_info.json").read_text()); vm = {m["id"]: m for m in d["materials"]["videos"]}
base = sorted([t for t in d["tracks"] if t["type"] == "video"][0]["segments"], key=lambda s: s["target_timerange"]["start"])
foot = [s for s in base if vm[s["material_id"]].get("type") == "video"]
def groups(s):
    out = {}
    for g in s.get("common_keyframes", []):
        if g["property_type"] == "KFTypeVolume": continue
        seen = {}
        for k in sorted(g["keyframe_list"], key=lambda k: k["time_offset"]): seen[k["time_offset"]] = k      # two keys on one timestamp (a ripple boundary on an existing key): keep the last
        g["keyframe_list"] = list(seen.values()); out[g["property_type"]] = g["keyframe_list"]
    return out
vals = collections.Counter(round(k["values"][0], 4) for s in foot for k in groups(s).get("KFTypeScaleX", []))
BASE = min(vals); PUNCH = max((v for v in vals if abs(v / BASE - 1.08) < 0.01), default=round(BASE * 1.08, 4)); INTRO = [v for v in vals if v not in (BASE, PUNCH)]
print(f"sizes: BASE {BASE} PUNCH {PUNCH} other {INTRO}")
after_card = {s["id"] for p, s in zip(base, base[1:]) if vm[p["material_id"]].get("type") == "photo"}
def setv(g, prop_keys, lo, hi, target):
    """set scale keys in [lo, hi] to target and scale the position keys by the same ratio"""
    sx = g["KFTypeScaleX"]; orig = {k["time_offset"]: k["values"][0] for k in sx}   # the scale BEFORE this edit, per key time — positions scale by target/orig
    for prop, keys in g.items():
        for k in keys:
            if lo - 2000 <= k["time_offset"] <= hi + 2000:                                   # ripple boundary keys sit ±1 µs off the piece edge
                if prop.startswith("KFTypeScale"): k["values"] = [target]
                elif prop.startswith("KFTypePosition"):
                    cur = orig.get(k["time_offset"]) or sx[0]["values"][0]; k["values"] = [k["values"][0] * target / cur]
def changes(keys): return [(k0["time_offset"], k1["time_offset"], k0["values"][0], k1["values"][0]) for k0, k1 in zip(keys, keys[1:]) if abs(k1["values"][0] - k0["values"][0]) > 1e-6]
n0 = n1 = n2 = n3 = 0
for s in foot:
    g = groups(s)
    if "KFTypeScaleX" not in g: continue
    s0 = s["source_timerange"]["start"]; s1 = s0 + s["source_timerange"]["duration"]; sx = g["KFTypeScaleX"]
    # rule 0: partial ramps at the edges
    ch = changes(sx)
    if ch and (ch[0][1] - s0) / US < 0.3 and not (s["id"] in after_card): setv(g, None, s0, ch[0][1], ch[0][3]); n0 += 1          # a ramp ending inside the first 0.3 s: start at its end value
    ch = changes(sx)
    if ch and (s1 - ch[-1][0]) / US < 0.3: setv(g, None, ch[-1][0], s1, ch[-1][2]); n0 += 1                                        # a ramp starting inside the last 0.3 s: keep the value before it
    # rule 1: any size change whose new value holds under --min-hold before the next change or the piece end
    ch = changes(sx)
    for i, (t0, t1, v0, v1) in enumerate(ch):
        nxt = ch[i + 1][0] if i + 1 < len(ch) else s1
        if abs(t0 - s0) <= 2000 and s["id"] in after_card: continue                                                                             # the intro zoom-out stays
        if (nxt - t1) / US < A.min_hold and t0 > s0 + 2000: setv(g, None, t0, nxt, v0); n1 += 1; print(f"  change removed @{(s['target_timerange']['start'] + t0 - s0)/US:.2f} (hold {(nxt - t1)/US:.2f}s)")
# rule 2: a size change on every footage→footage cut
for p, q in zip(base, base[1:]):
    if vm[p["material_id"]].get("type") != "video" or vm[q["material_id"]].get("type") != "video": continue
    gp, gq = groups(p), groups(q)
    if "KFTypeScaleX" not in gp or "KFTypeScaleX" not in gq: continue
    v_out = gp["KFTypeScaleX"][-1]["values"][0]; kq = gq["KFTypeScaleX"]; v_in = kq[0]["values"][0]
    if abs(v_out - v_in) > 1e-6: continue
    target = PUNCH if abs(v_in - BASE) < 1e-6 else BASE; qs0 = q["source_timerange"]["start"]; qend = qs0 + q["source_timerange"]["duration"]
    if (qend - qs0) / US < A.min_hold: continue                       # a piece shorter than the hold keeps the outgoing size; the NEXT cut changes it («מעבר מהיר וחזרה» otherwise)
    until = next((c[0] for c in changes(kq) if (c[0] - qs0) / US >= A.min_hold), qend)
    setv(gq, None, qs0, until, target); n2 += 1; print(f"  cut @{q['target_timerange']['start']/US:.2f}: {v_in:.3f} → {target:.3f} until +{(until - qs0)/US:.2f}s")
# rule 3: clamp stray values
for s in foot:
    g = groups(s)
    if "KFTypeScaleX" not in g: continue
    allowed = [BASE, PUNCH] + ([v for v in INTRO] if s["id"] in after_card else [])
    for k in g["KFTypeScaleX"]:
        v = round(k["values"][0], 4)
        if v not in allowed:
            tgt = min(allowed, key=lambda a: abs(a - v)); setv(g, None, k["time_offset"], k["time_offset"], tgt); n3 += 1
    k0 = g["KFTypeScaleX"][0]; s["clip"]["scale"] = {"x": k0["values"][0], "y": k0["values"][0]}
    for prop, key in (("KFTypePositionX", "x"), ("KFTypePositionY", "y")):
        if prop in g: s["clip"]["transform"][key] = g[prop][0]["values"][0]
# rule 4: the pan follows the size — within a piece pos/scale is one ratio; a key whose ratio strays (a scale edited without its position) is repaired
import statistics; n4 = 0
for s in foot:
    g = groups(s)
    if "KFTypeScaleX" not in g: continue
    sc = {k["time_offset"]: k["values"][0] for k in g["KFTypeScaleX"]}
    for prop in ("KFTypePositionX", "KFTypePositionY"):
        keys = g.get(prop, [])
        if len(keys) < 2: continue
        ratios = [k["values"][0] / sc[k["time_offset"]] for k in keys if k["time_offset"] in sc and sc[k["time_offset"]]]
        if not ratios: continue
        med = statistics.median(ratios)
        for k in keys:
            if k["time_offset"] in sc and abs(k["values"][0] / sc[k["time_offset"]] - med) > 0.02 * max(abs(med), 1e-6): k["values"] = [med * sc[k["time_offset"]]]; n4 += 1
    k0 = g["KFTypeScaleX"][0]; s["clip"]["scale"] = {"x": k0["values"][0], "y": k0["values"][0]}
    for prop, key in (("KFTypePositionX", "x"), ("KFTypePositionY", "y")):
        if prop in g: s["clip"]["transform"][key] = g[prop][0]["values"][0]
print(f"pan keys repaired {n4}")
# rule 5: a zero-length piece (a ripple cut that matched a whole sliver) is dropped
FR = US / d.get("fps", 60.0); zero = 0
for tr in (t for t in d["tracks"] if t["type"] == "video"):
    keep = [s for s in tr["segments"] if s["target_timerange"]["duration"] >= FR]; zero += len(tr["segments"]) - len(keep); tr["segments"] = keep
if zero: print(f"sub-frame pieces dropped {zero}")
print(f"edge ramps flattened {n0} | punches removed {n1} | cuts given a size change {n2} | stray values clamped {n3}")
if not A.write: print("(dry run — add --write)"); sys.exit()
pid = capcut._capcut_pid()
if pid and f"{D}/" in capcut._capcut_open_files(pid): sys.exit("✗ CapCut מחזיק את הפרויקט")
capcut._backup(D); tmp = D / "draft_info.json.tmp"; tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":"))); json.loads(tmp.read_text()); tmp.replace(D / "draft_info.json"); print("✓ written")
