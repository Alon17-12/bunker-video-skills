"""Small, proven pieces for the devices Alon uses in his own drafts (measured 22.09.26 with
scan_drafts_devices.py). Import from a build script; each helper returns material ids the caller
puts on a segment. Nothing here writes a draft.

    from devices import blur_effect
    seg["extra_material_refs"].append(blur_effect(mats, 0.5))          # the Blur video effect, intensity 0..1

Only effects whose cache exists on this machine can be injected. `Blur` (effect_id 752523) is cached
and used in 8 drafts; every other video effect and every "ART …" text effect is not — Alon applies it
once in any project and it becomes cloneable (harvest it the way text_anim_donors.json was built).
"""
import copy, glob, json, os, sys, uuid
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut

_BLUR_DONOR = None


def _find_blur_donor():
    """the first Blur video_effect material whose cache file is on disk, from any draft"""
    global _BLUR_DONOR
    if _BLUR_DONOR: return _BLUR_DONOR
    for di in sorted(glob.glob(str(capcut.DRAFTS_DIR / "*" / "draft_info.json")), key=os.path.getmtime, reverse=True):
        try: d = json.load(open(di))
        except Exception: continue
        for m in d["materials"].get("video_effects", []) or []:
            if m.get("name") == "Blur" and m.get("path") and os.path.exists(m["path"]):
                _BLUR_DONOR = m; return m
    raise RuntimeError("no cached Blur effect on this machine — apply Blur once in any CapCut project, then retry")


def blur_effect(mats, amount=0.5):
    """clone the cached Blur effect with `amount` (0..1 — Alon's own uses: 0.1 under a plain caption,
    0.5 behind a headline, 0.75 for a full plate under glowing words); returns the material id"""
    m = copy.deepcopy(_find_blur_donor()); m["id"] = str(uuid.uuid4()).upper()
    for p in m.get("adjust_params", []):
        if p["name"] == "effects_adjust_blur": p["value"] = float(amount)
    m["apply_target_type"] = 0; m["time_range"] = None; m["apply_time_range"] = None; m["common_keyframes"] = []
    mats.setdefault("video_effects", []).append(m); return m["id"]


def blur_donor_info():
    m = _find_blur_donor(); return {"effect_id": m.get("effect_id"), "resource_id": m.get("resource_id"), "path": m.get("path")}


if __name__ == "__main__":
    print(json.dumps(blur_donor_info(), ensure_ascii=False, indent=1))
