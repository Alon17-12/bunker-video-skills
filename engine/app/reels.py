"""Reels-draft builder — create a brand-new 9:16 CapCut draft from moments.

Given a source draft and a list of {start_us, end_us, title} moments, this:
1. copies the draft folder (minus caches/backups) under a new name
2. cuts away everything outside the moments (proven cuts engine)
3. strips the EPISODE's overlays — logos, closing cards, subscribe banners. They
   belong to the long-form video; a reel is not the episode with a logo on it.
4. lays the timeline out as: [title card][reel][title card][reel]… where each
   card is a real 5s white clip ON THE MAIN TRACK carrying the next reel's title
5. flips the canvas to 9:16, fills, and auto-reframes each cut onto the speaker
6. applies the colour/LUT preset, so the reel is graded like the episode
7. registers the new draft in CapCut's root_meta_info.json

The source draft is never touched.

WHY THE CARD IS A CLIP AND NOT A GAP (learned the hard way, 2026-07-14):
v1 opened a 1s HOLE in the main video track and floated a white photo above it.
It built correctly — and then CapCut silently destroyed it. **CapCut's main video
track cannot hold empty gaps**: on open, it ripple-closes them, dragging the
footage and captions left while the floating photos stay put. The result was
white cards landing in the middle of reels and captions drifting out of sync by a
second per junction. Never leave a hole in the main track.
"""
import bisect
import copy
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import capcut
import cuts
import paths
import reframe

US = 1_000_000
CARD_US = 5 * US          # white title card between reels (Alon's spec)
CARD_TITLE_PAD_US = 200_000
FFMPEG = Path(__file__).resolve().parent.parent / "bin/ffmpeg"

# A reels project is DERIVED — it is fully described by its source episode plus a
# list of moments. Storing that recipe inside the draft folder is what lets the
# Captain edit the reel list later ("drop the third one", "add a moment about X")
# and rebuild in seconds, instead of trying to splice new footage into a timeline
# the cuts engine can only ever remove from.
RECIPE_FILE = "ccstudio-reels.json"

_SKIP_COPY = ("Resources", "common_attachment")  # caches; not referenced by the draft json


def _unique_name(base: str) -> str:
    name, n = base, 2
    while (capcut.DRAFTS_DIR / name).exists():
        name = f"{base} {n}"
        n += 1
    return name


def _copy_draft_folder(src: Path, dst: Path) -> None:
    dst.mkdir()
    for item in src.iterdir():
        if item.name in _SKIP_COPY or item.name.startswith(capcut.BACKUP_PREFIX):
            continue
        if item.suffix in (".tmp", ".bak"):
            continue
        if item.is_dir():
            shutil.copytree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)


def _white_card_png(draft_dir: Path) -> Path:
    out = draft_dir / "ccstudio-card.png"
    subprocess.run([str(FFMPEG), "-y", "-f", "lavfi", "-i",
                    "color=white:s=1080x1920", "-frames:v", "1", str(out)],
                   capture_output=True, check=True)
    return out


def _card_style(style: dict) -> dict:
    """The caption style, recoloured for a white card.

    The reel style is white text with a black outline — perfect over footage,
    invisible over a white card. Flip it: near-black fill, no outline, bigger.
    """
    s = json.loads(json.dumps(style))          # deep copy
    mt = s.get("material_template") or {}
    mt["text_color"] = "#111111"
    mt["border_color"] = "#111111"
    mt["font_size"] = max(float(mt.get("font_size") or 10) * 1.6, 15.0)
    for field in ("content", "base_content"):
        raw = mt.get(field)
        if not raw:
            continue
        try:
            c = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for st in c.get("styles", []):
            st["fill"] = {"content": {"solid": {"color": [0.07, 0.07, 0.07]},
                                      "render_type": "solid"}}
            st.pop("strokes", None)            # no outline on a clean white card
            st.pop("shadows", None)
            st["size"] = mt["font_size"]
        mt[field] = json.dumps(c, ensure_ascii=False)
    return s


def _photo_donor() -> tuple[dict, dict, list]:
    """(material, segment, extras) of a photo clip cloned from any draft."""
    for d in capcut.list_drafts():
        try:
            draft = capcut.load_draft(d["id"])
        except (OSError, json.JSONDecodeError):
            continue
        mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
        idx = capcut._materials_index(draft)
        for track in draft.get("tracks", []):
            if track.get("type") != "video":
                continue
            for seg in track.get("segments", []):
                mat = mats.get(seg.get("material_id"))
                if mat and mat.get("type") == "photo" and mat.get("path"):
                    extras = [{"list": idx[r][0], "material": idx[r][1]}
                              for r in seg.get("extra_material_refs", []) if r in idx]
                    return (copy.deepcopy(mat), copy.deepcopy(seg), copy.deepcopy(extras))
    raise ValueError("לא נמצא דונור של תמונה באף פרויקט — הוסף תמונה כלשהי לדרפט אחד ב-CapCut")


def _fill_scale(mat_w: int, mat_h: int, cv_w: int = 1080, cv_h: int = 1920) -> float:
    """CapCut scale=1.0 means fit-inside — this returns the fill (cover) factor."""
    if not mat_w or not mat_h:
        mat_w, mat_h = 1920, 1080
    contain = min(cv_w / mat_w, cv_h / mat_h)
    cover = max(cv_w / mat_w, cv_h / mat_h)
    return cover / contain


def _split_at(draft: dict, times: list[int]) -> None:
    """Cut every clip that straddles a reel boundary in two.

    Two reels that sit back-to-back in the episode leave NOTHING to remove
    between them, so the cuts engine has no reason to split there — and a single
    camera clip ends up spanning both. You then cannot shift it (each reel moves
    by a different amount) or push a card between them. So we split first.

    Text is left alone: captions are already snapped to reel boundaries, and
    splitting one would duplicate its words on screen.
    """
    idx = capcut._materials_index(draft)
    for track in draft.get("tracks", []):
        if track.get("type") == "text":
            continue
        out = []
        for seg in track.get("segments", []):
            tgt = seg["target_timerange"]
            t0 = tgt["start"]
            t1 = t0 + tgt["duration"]
            pts = sorted(t for t in times if t0 < t < t1)
            if not pts:
                out.append(seg)
                continue
            src = seg.get("source_timerange")
            speed = seg.get("speed", 1.0) or 1.0
            edges = [t0] + pts + [t1]
            for i, (a, b) in enumerate(zip(edges, edges[1:])):
                piece = seg if i == 0 else cuts._clone_with_new_ids(draft, seg, idx)
                piece["target_timerange"] = {"start": a, "duration": b - a}
                if src and src.get("duration") is not None:
                    piece["source_timerange"] = {
                        "start": int(src.get("start", 0) + (a - t0) * speed),
                        "duration": int((b - a) * speed),
                    }
                piece["common_keyframes"] = []      # keyframe times no longer valid
                out.append(piece)
        out.sort(key=lambda s: s["target_timerange"]["start"])
        track["segments"] = out


def _registry_add(new_dir: Path, draft_id: str, duration_us: int, source_name: str) -> None:
    """Put the new project on CapCut's home screen (registry backed up first)."""
    reg_path = capcut.DRAFTS_DIR / "root_meta_info.json"
    reg = json.loads(reg_path.read_text())
    backup = capcut.DRAFTS_DIR / f"root_meta_info.ccstudio-backup-{int(time.time())}.json"
    shutil.copy2(reg_path, backup)
    for old in sorted(capcut.DRAFTS_DIR.glob("root_meta_info.ccstudio-backup-*"))[:-capcut.MAX_BACKUPS]:
        old.unlink()

    store = reg.get("all_draft_store", [])
    template = next((e for e in store if e.get("draft_name") == source_name), store[0] if store else None)
    if template is None:
        raise ValueError("registry_empty")
    entry = copy.deepcopy(template)
    now_us = int(time.time() * US)
    entry.update({
        "draft_id": draft_id,
        "draft_name": new_dir.name,
        "draft_fold_path": str(new_dir),
        "draft_json_file": str(new_dir / "draft_info.json"),
        "draft_cover": str(new_dir / "draft_cover.jpg"),
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": duration_us,
    })
    for k in list(entry):
        if k.startswith("tm_draft_cloud") or k.startswith("draft_cloud") or k.startswith("cloud_"):
            v = entry[k]
            entry[k] = 0 if isinstance(v, (int, float)) else ("" if isinstance(v, str) else v)
    store.insert(0, entry)
    tmp = reg_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False))
    json.loads(tmp.read_text())
    tmp.replace(reg_path)


def load_recipe(draft_id: str) -> dict | None:
    """The source episode + moment list a reels project was built from."""
    path = capcut.DRAFTS_DIR / draft_id / RECIPE_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _registry_remove(draft_name: str) -> dict | None:
    """Take a draft out of CapCut's home screen. Returns the removed entry so a
    failed rebuild can put it back exactly as it was."""
    reg_path = capcut.DRAFTS_DIR / "root_meta_info.json"
    reg = json.loads(reg_path.read_text())
    shutil.copy2(reg_path, capcut.DRAFTS_DIR / f"root_meta_info.ccstudio-backup-{int(time.time())}.json")
    store = reg.get("all_draft_store", [])
    removed = next((e for e in store if e.get("draft_name") == draft_name), None)
    reg["all_draft_store"] = [e for e in store if e.get("draft_name") != draft_name]
    tmp = reg_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False))
    json.loads(tmp.read_text())
    tmp.replace(reg_path)
    return removed


def _registry_restore(entry: dict) -> None:
    reg_path = capcut.DRAFTS_DIR / "root_meta_info.json"
    reg = json.loads(reg_path.read_text())
    reg.setdefault("all_draft_store", []).insert(0, entry)
    tmp = reg_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False))
    json.loads(tmp.read_text())
    tmp.replace(reg_path)


def rebuild_reels(draft_id: str, moments: list[dict], style: dict | None,
                  color_preset: dict | None = None) -> dict:
    """Rebuild an existing reels project from a new moment list, same name.

    The old project is copied aside first and put back verbatim if the rebuild
    fails — a half-built reel that has already replaced the good one is the worst
    possible outcome, so it must not be reachable.

    Manual CapCut edits inside the reels project (music, effects) do NOT survive:
    the project is re-derived from its source. The caller is responsible for
    telling the user that before running this.
    """
    if capcut.capcut_running():
        raise RuntimeError("capcut_running")
    recipe = load_recipe(draft_id)
    if not recipe:
        raise ValueError(
            f"\"{draft_id}\" לא נבנה על ידי הקפטן כפרויקט רילס — אין לו מתכון, "
            "ולכן אי אפשר לבנות אותו מחדש. אפשר לבנות פרויקט רילס חדש מהפרק.")
    source_id = recipe["source"]
    if not (capcut.DRAFTS_DIR / source_id).exists():
        raise ValueError(f"הפרק המקורי \"{source_id}\" לא נמצא — אי אפשר לבנות מחדש")

    src_dir = capcut.DRAFTS_DIR / draft_id
    backup_dir = paths.DATA_DIR / "reels_backups" / f"{draft_id} {int(time.time())}"
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, backup_dir)

    entry = _registry_remove(draft_id)
    shutil.rmtree(src_dir, ignore_errors=True)
    try:
        result = create_reels_draft(source_id, moments, style, name=draft_id,
                                    color_preset=color_preset)
    except Exception:
        shutil.rmtree(src_dir, ignore_errors=True)      # clear any partial build
        shutil.copytree(backup_dir, src_dir)            # put the old one back
        if entry:
            _registry_restore(entry)
        raise
    result["rebuilt"] = True
    result["backup"] = str(backup_dir)
    return result


def create_reels_draft(source_id: str, moments: list[dict], style: dict | None,
                       name: str | None = None,
                       color_preset: dict | None = None) -> dict:
    if capcut.capcut_running():
        raise RuntimeError("capcut_running")
    src_dir = capcut.DRAFTS_DIR / source_id
    src_draft = capcut.load_draft(source_id)
    duration = src_draft.get("duration", 0)
    src_canvas = src_draft.get("canvas_config") or {}

    moments = sorted((dict(m) for m in moments), key=lambda m: m["start_us"])
    merged = []
    for m in moments:
        a, b = max(0, int(m["start_us"])), min(duration, int(m["end_us"]))
        if b - a < 500_000:
            continue
        # only merge moments that genuinely OVERLAP. Two reels that happen to be
        # back-to-back in the episode are still two reels — merging them on touch
        # silently glued four separate ideas into one 96-second lump.
        if merged and a < merged[-1]["end_us"]:
            merged[-1]["end_us"] = max(merged[-1]["end_us"], b)
        else:
            merged.append({"start_us": a, "end_us": b, "title": str(m.get("title", ""))})
    if not merged:
        raise ValueError("אין רגעים תקינים לבניית רילס")

    new_name = _unique_name(name or f"{source_id} — רילס")
    dst_dir = capcut.DRAFTS_DIR / new_name
    _copy_draft_folder(src_dir, dst_dir)
    try:
        # --- keep only the moments (complement cut) ---
        complement, pos = [], 0
        for m in merged:
            if m["start_us"] > pos:
                complement.append([pos, m["start_us"]])
            pos = m["end_us"]
        if pos < duration:
            complement.append([pos, duration])
        if complement:
            cuts.apply_cuts(new_name, complement)

        draft = capcut.load_draft(new_name)
        lens = [m["end_us"] - m["start_us"] for m in merged]

        # --- strip the EPISODE's overlays -----------------------------------
        # Logos, closing cards, subscribe banners: they belong to the long-form
        # video. A reel is not the episode with a logo stuck on it, and Alon never
        # asked for them. Drop every still, then drop the tracks left empty.
        video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
        for track in draft.get("tracks", []):
            if track.get("type") != "video":
                continue
            track["segments"] = [
                s for s in track["segments"]
                if (video_mats.get(s.get("material_id")) or {}).get("type") != "photo"]
        draft["tracks"] = [t for t in draft["tracks"]
                           if t.get("type") != "video" or t.get("segments")]

        main = next((t for t in draft["tracks"] if t.get("type") == "video"), None)
        if main is None:
            raise ValueError("לא נמצא טראק וידאו בפרק המקורי")

        # --- lay out [card][reel][card][reel]… ------------------------------
        # A card per reel, INCLUDING before the first — so every reel carries its
        # own title, and the timeline can be sliced straight into separate videos.
        bounds = [0]                       # cut-time start of each moment
        for ln in lens:
            bounds.append(bounds[-1] + ln)

        _split_at(draft, bounds[1:-1])     # no clip may straddle two reels

        def shift_for(start_us: int) -> int:
            """Every moment is pushed right by one card per card that precedes it."""
            k = max(0, bisect.bisect_right(bounds, start_us) - 1)
            k = min(k, len(lens) - 1)
            return (k + 1) * CARD_US

        for track in draft.get("tracks", []):
            for seg in track.get("segments", []):
                tgt = seg["target_timerange"]
                tgt["start"] += shift_for(tgt["start"])

        # captions inherit the gap-free stretch from the episode, so the last one
        # of a reel can now run over the card that follows it — clamp it back
        new_ends = [bounds[i + 1] + (i + 1) * CARD_US for i in range(len(lens))]
        for track in draft.get("tracks", []):
            if track.get("type") != "text":
                continue
            for seg in track.get("segments", []):
                tgt = seg["target_timerange"]
                end = tgt["start"] + tgt["duration"]
                limit = next((e for e in new_ends if e > tgt["start"]), None)
                if limit and end > limit:
                    tgt["duration"] = max(100_000, limit - tgt["start"])

        draft["duration"] = sum(lens) + CARD_US * len(lens)

        # --- the title cards: REAL clips on the MAIN track -------------------
        # Not a gap with a photo floating above it: CapCut ripple-closes gaps on
        # the main track the moment the project is opened, which silently wrecked
        # the whole timeline (see the module docstring).
        png = _white_card_png(dst_dir)
        donor_mat, donor_seg, donor_extras = _photo_donor()
        mats = draft.setdefault("materials", {})
        card_ids = set()
        for i in range(len(lens)):
            mat = copy.deepcopy(donor_mat)
            mat.update({"id": capcut._new_id(), "path": str(png),
                        "material_name": "ccstudio-card.png",
                        "width": 1080, "height": 1920})
            mats.setdefault("videos", []).append(mat)
            refs = []
            for ex in donor_extras:
                clone = copy.deepcopy(ex["material"])
                clone["id"] = capcut._new_id()
                mats.setdefault(ex["list"], []).append(clone)
                refs.append(clone["id"])
            seg = copy.deepcopy(donor_seg)
            seg.update({"id": capcut._new_id(), "material_id": mat["id"],
                        "extra_material_refs": refs,
                        "target_timerange": {"start": bounds[i] + i * CARD_US,
                                             "duration": CARD_US},
                        "source_timerange": {"start": 0, "duration": CARD_US},
                        "common_keyframes": [], "volume": 1.0})
            seg.setdefault("clip", {})["scale"] = {"x": 1.0, "y": 1.0}
            seg["clip"]["transform"] = {"x": 0.0, "y": 0.0}
            card_ids.add(seg["id"])
            main["segments"].append(seg)
        main["segments"].sort(key=lambda s: s["target_timerange"]["start"])

        # --- 9:16 canvas + fill-scale the footage ---------------------------
        draft["canvas_config"] = {"ratio": "9:16", "width": 1080, "height": 1920,
                                  "background": None}
        video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
        for track in draft.get("tracks", []):
            if track.get("type") != "video":
                continue
            for seg in track.get("segments", []):
                if seg["id"] in card_ids:
                    continue                       # the card is already 1080x1920
                mat = video_mats.get(seg.get("material_id")) or {}
                w, h = mat.get("width", 0), mat.get("height", 0)
                if h and w and w <= h:
                    continue  # already vertical — leave as is
                f = _fill_scale(w, h)
                clip = seg.setdefault("clip", {})
                clip["scale"] = {"x": f, "y": f}
                clip["transform"] = {"x": 0.0, "y": 0.0}

        draft["id"] = capcut._new_id()
        capcut._atomic_write(dst_dir, draft)

        # --- auto-reframe: pan each cut onto its speaker instead of a blind
        # centre-crop. Needs the source footage; if it isn't reachable we keep
        # the centred fallback rather than failing the whole build.
        reframe_result = None
        try:
            plan = reframe.plan_reframe(new_name)
            reframe.apply_plan_to_draft(draft, plan)
            capcut._atomic_write(dst_dir, draft)
            reframe_result = {"moved": plan["moved"], "centered": plan["centered"],
                              "two_shots": plan["two_shots"]}
        except (ValueError, RuntimeError, OSError) as e:
            reframe_result = {"error": str(e)}

        # --- the title, ON its white card ------------------------------------
        # White-on-white would be invisible, so the card uses a dark variant of
        # the caption style.
        if style:
            titles = []
            for i, m in enumerate(merged):
                if not m["title"]:
                    continue
                titles.append({"text": m["title"],
                               "start_us": bounds[i] + i * CARD_US + CARD_TITLE_PAD_US,
                               "duration_us": CARD_US - 2 * CARD_TITLE_PAD_US,
                               "words": []})
            if titles:
                capcut.inject_captions(new_name, titles, _card_style(style),
                                       replace_existing=False)

        # --- colour / LUT: a reel should be graded like the episode ----------
        color_result = None
        if color_preset:
            try:
                capcut.apply_color(new_name, color_preset)
                # apply_color grades EVERY video segment — including the white
                # cards, which a LUT would tint off-white. Cards are graphics, not
                # footage: take the grade back off them.
                graded = capcut.load_draft(new_name)
                gmats = {m["id"]: m for m in graded["materials"]["videos"]}
                lut_ids = {e["id"] for e in graded["materials"].get("effects", [])
                           if isinstance(e, dict) and e.get("type") == "lut"}
                for track in graded["tracks"]:
                    if track.get("type") != "video":
                        continue
                    for seg in track["segments"]:
                        mat = gmats.get(seg.get("material_id")) or {}
                        if mat.get("material_name") != "ccstudio-card.png":
                            continue
                        seg["enable_lut"] = False
                        seg["extra_material_refs"] = [
                            r for r in seg.get("extra_material_refs", [])
                            if r not in lut_ids]
                capcut._atomic_write(dst_dir, graded)
                color_result = "applied"
            except (ValueError, RuntimeError, OSError, KeyError) as e:
                color_result = f"failed: {e}"

        # --- folder meta + CapCut registry ---
        meta_id = capcut._new_id()
        meta_path = dst_dir / "draft_meta_info.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            now_us = int(time.time() * US)
            meta.update({"draft_id": meta_id, "draft_name": new_name,
                         "draft_fold_path": str(dst_dir),
                         "tm_draft_create": now_us, "tm_draft_modified": now_us,
                         "tm_duration": draft["duration"]})
            meta_path.write_text(json.dumps(meta, ensure_ascii=False))
        # the recipe: what this project IS, so it can be edited and rebuilt later
        (dst_dir / RECIPE_FILE).write_text(json.dumps(
            {"source": source_id, "moments": merged, "card_us": CARD_US,
             "built_us": int(time.time() * US)}, ensure_ascii=False))
        _registry_add(dst_dir, meta_id, draft["duration"], source_id)
    except Exception:
        shutil.rmtree(dst_dir, ignore_errors=True)
        raise

    return {"name": new_name, "duration_us": draft["duration"],
            "moments": len(merged), "reframe": reframe_result,
            "color": color_result, "card_s": CARD_US / US}
