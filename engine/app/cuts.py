"""Silence detection + timeline cutting for CapCut drafts.

detect_silences: VAD over the rebuilt timeline audio → removable intervals.
apply_cuts: removes intervals from the timeline — every track's segments are
intersected with the kept ranges and shifted left, sources re-mapped through
each segment's speed. Same safety story as caption injection: backup + atomic
write, blocked while CapCut runs.
"""
import copy
import json

import capcut
import transcribe as stt

US = 1_000_000


def detect_silences(draft_id: str, min_silence_s: float = 0.7,
                    pad_s: float = 0.15) -> dict:
    """Silence intervals on the timeline, padded so speech never gets clipped."""
    draft = capcut.load_draft(draft_id)
    plan = capcut.audio_plan(draft, draft_id)
    if not plan:
        raise ValueError("אין אודיו בפרויקט")
    audio, warnings = stt.build_timeline_audio(plan, draft.get("duration", 0))
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    speech = get_speech_timestamps(
        audio, VadOptions(min_silence_duration_ms=int(min_silence_s * 500),
                          speech_pad_ms=100))
    duration_us = draft.get("duration", 0)
    pad = int(pad_s * US)
    silences = []
    prev_end = 0
    regions = [(int(s["start"] / stt.SAMPLE_RATE * US),
                int(s["end"] / stt.SAMPLE_RATE * US)) for s in speech]
    for start, end in regions + [(duration_us, duration_us)]:
        gap_start, gap_end = prev_end + pad, start - pad
        if gap_end - gap_start >= min_silence_s * US:
            silences.append({"start_us": gap_start, "end_us": gap_end,
                             "duration_us": gap_end - gap_start})
        prev_end = max(prev_end, end)
    total_cut = sum(s["duration_us"] for s in silences)
    return {"silences": silences, "duration_us": duration_us,
            "total_cut_us": total_cut, "warnings": warnings}


# ---------------------------------------------------------------- remap

def _keep_intervals(duration_us: int, cuts: list[list[int]]) -> list[list[int]]:
    cuts = sorted([list(c) for c in cuts])
    keep, pos = [], 0
    for start, end in cuts:
        start, end = max(start, 0), min(end, duration_us)
        if start > pos:
            keep.append([pos, start])
        pos = max(pos, end)
    if pos < duration_us:
        keep.append([pos, duration_us])
    return keep


def _clone_with_new_ids(draft: dict, seg: dict, idx: dict) -> dict:
    """Deep-copy a segment including its material + extra materials."""
    mats = draft["materials"]
    clone = copy.deepcopy(seg)
    clone["id"] = capcut._new_id()
    hit = idx.get(seg.get("material_id"))
    if hit:
        mat = copy.deepcopy(hit[1])
        mat["id"] = capcut._new_id()
        mats.setdefault(hit[0], []).append(mat)
        clone["material_id"] = mat["id"]
    refs = []
    for ref in seg.get("extra_material_refs", []):
        h = idx.get(ref)
        if h:
            m = copy.deepcopy(h[1])
            m["id"] = capcut._new_id()
            mats.setdefault(h[0], []).append(m)
            refs.append(m["id"])
    clone["extra_material_refs"] = refs
    return clone


def apply_cuts(draft_id: str, cuts: list[list[int]]) -> dict:
    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = capcut.DRAFTS_DIR / draft_id
    draft = capcut.load_draft(draft_id)
    backup = capcut._backup(draft_dir)
    duration_us = draft.get("duration", 0)
    keep = _keep_intervals(duration_us, cuts)
    idx = capcut._materials_index(draft)

    # new position of an old timeline point = kept time before it
    def remap(t: int) -> int:
        out = 0
        for ks, ke in keep:
            if t <= ks:
                break
            out += min(t, ke) - ks
        return out

    for track in draft.get("tracks", []):
        new_segments = []
        for seg in track.get("segments", []):
            tgt = seg.get("target_timerange") or {}
            t0, dur = tgt.get("start", 0), tgt.get("duration", 0)
            t1 = t0 + dur
            src = seg.get("source_timerange")
            speed = seg.get("speed", 1.0) or 1.0
            first = True
            for ks, ke in keep:
                a, b = max(t0, ks), min(t1, ke)
                if b - a <= 0:
                    continue
                piece = seg if first else _clone_with_new_ids(draft, seg, idx)
                first = False
                piece["target_timerange"] = {"start": remap(a), "duration": b - a}
                if src and src.get("duration") is not None:
                    piece["source_timerange"] = {
                        "start": int(src.get("start", 0) + (a - t0) * speed),
                        "duration": int((b - a) * speed),
                    }
                piece["common_keyframes"] = []  # keyframe times no longer valid
                new_segments.append(piece)
        new_segments.sort(key=lambda s: s["target_timerange"]["start"])
        track["segments"] = new_segments

    new_duration = sum(ke - ks for ks, ke in keep)
    draft["duration"] = new_duration

    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    path = capcut._draft_file(draft_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(draft, ensure_ascii=False, separators=(",", ":")))
    json.loads(tmp.read_text())
    tmp.replace(path)
    return {"backup": backup.name, "removed_us": duration_us - new_duration,
            "new_duration_us": new_duration}


# ---------------------------------------------------------------- auto-ducking

def speech_regions(draft_id: str) -> list[list[int]]:
    """Merged speech intervals on the timeline (μs), via the same VAD."""
    draft = capcut.load_draft(draft_id)
    plan = capcut.audio_plan(draft, draft_id)
    if not plan:
        raise ValueError("אין אודיו בפרויקט")
    audio, _ = stt.build_timeline_audio(plan, draft.get("duration", 0))
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    speech = get_speech_timestamps(
        audio, VadOptions(min_silence_duration_ms=400, speech_pad_ms=150))
    out = []
    for s in speech:
        a = int(s["start"] / stt.SAMPLE_RATE * US)
        b = int(s["end"] / stt.SAMPLE_RATE * US)
        if out and a - out[-1][1] < 600_000:  # merge close bursts — no pumping
            out[-1][1] = b
        else:
            out.append([a, b])
    return out


def _kf(time_offset: int, value: float) -> dict:
    return {"id": capcut._new_id(), "curveType": "Line", "graphID": "",
            "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
            "string_value": "", "time_offset": int(time_offset), "values": [value]}


def apply_ducking(draft_id: str, duck_ratio: float = 0.25,
                  ramp_ms: int = 300) -> dict:
    """Music dives under speech: KFTypeVolume keyframes on every music/SFX
    segment, hugging the VAD speech map. time_offset is in SOURCE time —
    src = src.start + (t - tgt.start) * speed (verified on real drafts)."""
    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    speech = speech_regions(draft_id)
    if not speech:
        return {"segments": 0, "detail": "no_speech"}
    draft_dir = capcut.DRAFTS_DIR / draft_id
    draft = capcut.load_draft(draft_id)
    backup = capcut._backup(draft_dir)
    audio_mats = {m["id"]: m for m in draft.get("materials", {}).get("audios", [])}
    ramp = ramp_ms * 1000
    touched = 0
    for track in draft.get("tracks", []):
        if track.get("type") != "audio":
            continue
        for seg in track.get("segments", []):
            mat = audio_mats.get(seg.get("material_id"))
            if not mat or capcut._is_speech_audio(mat):
                continue  # duck only music / SFX — never the voice itself
            tgt = seg.get("target_timerange") or {}
            t0, t1 = tgt.get("start", 0), tgt.get("start", 0) + tgt.get("duration", 0)
            src = seg.get("source_timerange") or {}
            speed = seg.get("speed", 1.0) or 1.0
            base = seg.get("volume", 1.0) or 1.0
            low = base * duck_ratio

            def to_src(t):  # timeline → source time, clamped into the segment
                t = min(max(t, t0), t1)
                return int(src.get("start", 0) + (t - t0) * speed)

            events = []  # (timeline_t, value)
            for a, b in speech:
                if b <= t0 or a >= t1:
                    continue
                events += [(a - ramp, base), (a, low), (b, low), (b + ramp, base)]
            if not events:
                continue
            kfs, last_src = [], None
            for t, v in sorted(events):
                s_t = to_src(t)
                if last_src is not None and s_t <= last_src:
                    s_t = last_src + 1000
                kfs.append(_kf(s_t, v))
                last_src = s_t
            seg["common_keyframes"] = [
                k for k in (seg.get("common_keyframes") or [])
                if k.get("property_type") != "KFTypeVolume"
            ] + [{"id": capcut._new_id(), "material_id": "",
                  "property_type": "KFTypeVolume", "keyframe_list": kfs}]
            touched += 1
    capcut._atomic_write(draft_dir, draft)
    return {"segments": touched, "speech_regions": len(speech), "backup": backup.name}
