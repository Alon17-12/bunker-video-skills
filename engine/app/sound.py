"""Sound engines — speaker balancing and voice loudness normalization.

balance_voices: measures the actual speech level of every speech-carrying
segment and evens them out by adjusting segment volume only (no rendering,
fully reversible via backup).

normalize_voice: renders the full voice timeline at 48kHz, normalizes it to
a podcast-standard loudness (EBU R128 via ffmpeg loudnorm), writes the result
into the draft folder and swaps it in as a baked voice track — original
speech segments are muted (volume 0), everything reversible via backup.
"""
import copy
import json
import math
import subprocess
from pathlib import Path

import numpy as np

import capcut
import transcribe as stt

US = 1_000_000
VOICE_SR = 48_000
VOICE_FILE = "ccstudio-voice-master.m4a"


# ---------------------------------------------------------------- shared

def _speech_segments(draft: dict, draft_id: str) -> list[tuple[dict, list[dict]]]:
    """(segment, plan_entries) for every speech-carrying segment — the same
    filtering rules as capcut.audio_plan, but keeping the segment reference
    so we can write its volume back."""
    video_mats = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    audio_mats = {m["id"]: m for m in draft.get("materials", {}).get("audios", [])}
    mc_idx = None
    out = []
    for track in draft.get("tracks", []):
        ttype = track.get("type")
        if ttype not in ("video", "audio"):
            continue
        for seg in track.get("segments", []):
            if seg.get("volume", 1.0) == 0:
                continue
            src = seg.get("source_timerange") or {}
            tgt = seg.get("target_timerange") or {}
            if not tgt.get("duration"):
                continue
            entries = []
            if ttype == "video":
                mat = video_mats.get(seg.get("material_id"))
                if not mat or mat.get("has_audio") is False:
                    continue
                if not mat.get("path") and mat.get("multi_camera_info"):
                    if mc_idx is None:
                        mc_idx = capcut._multicam_index(capcut.DRAFTS_DIR / draft_id)
                    entries = capcut._multicam_entries(seg, mat, mc_idx)
                elif mat.get("path") and mat.get("type") != "photo" \
                        and Path(mat["path"]).suffix.lower() not in capcut._STILL_EXTS:
                    entries = [_entry(seg, mat)]
            else:
                mat = audio_mats.get(seg.get("material_id"))
                if mat and mat.get("path") and capcut._is_speech_audio(mat):
                    entries = [_entry(seg, mat)]
            if entries:
                out.append((seg, entries))
    return out


def _entry(seg: dict, mat: dict) -> dict:
    src = seg.get("source_timerange") or {}
    tgt = seg.get("target_timerange") or {}
    return {"path": mat["path"],
            "source_start_us": src.get("start", 0),
            "source_duration_us": src.get("duration", tgt.get("duration", 0)),
            "target_start_us": tgt.get("start", 0),
            "target_duration_us": tgt.get("duration", 0),
            "speed": seg.get("speed", 1.0) or 1.0,
            "volume": seg.get("volume", 1.0)}


def _speech_rms_db(audio: np.ndarray) -> float | None:
    """Robust speech level: RMS of the loudest half of 250ms windows —
    ignores in-segment pauses so we measure the voice, not the silence."""
    win = int(0.25 * stt.SAMPLE_RATE)
    if len(audio) < win * 2:
        return None
    n = len(audio) // win
    rms = np.sqrt(np.mean(audio[:n * win].reshape(n, win) ** 2, axis=1))
    rms = rms[rms > 1e-4]  # drop dead-silent windows
    if len(rms) < 2:
        return None
    top = np.sort(rms)[len(rms) // 2:]
    return float(20 * math.log10(np.mean(top)))


# ---------------------------------------------------------------- balance

def balance_voices(draft_id: str, max_gain_db: float = 9.0) -> dict:
    """Even out speech levels across segments by writing segment volumes."""
    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = capcut.DRAFTS_DIR / draft_id
    draft = capcut.load_draft(draft_id)
    pairs = _speech_segments(draft, draft_id)
    if not pairs:
        raise ValueError("לא נמצאו סגמנטים של דיבור")

    measured = []  # (seg, level_db)
    for seg, entries in pairs:
        tgt = seg.get("target_timerange") or {}
        if tgt.get("duration", 0) < 1 * US:
            continue  # too short to measure reliably
        dur = tgt["duration"]
        audio, _ = stt.build_timeline_audio(
            [dict(e, target_start_us=e["target_start_us"] - tgt["start"]) for e in entries], dur)
        level = _speech_rms_db(audio)
        if level is not None:
            measured.append((seg, level))
    if len(measured) < 2:
        return {"adjusted": 0, "detail": "אין מספיק סגמנטים מדידים"}

    target = float(np.median([lv for _, lv in measured]))
    backup = capcut._backup(draft_dir)
    adjusted, max_adj = 0, 0.0
    for seg, level in measured:
        gain_db = max(-max_gain_db, min(max_gain_db, target - level))
        if abs(gain_db) < 0.75:
            continue
        base = seg.get("volume", 1.0) or 1.0
        seg["volume"] = round(min(4.0, max(0.15, base * (10 ** (gain_db / 20)))), 4)
        seg["last_nonzero_volume"] = seg["volume"]
        adjusted += 1
        max_adj = max(max_adj, abs(gain_db))
    if not adjusted:
        return {"adjusted": 0, "detail": "הרמות כבר מאוזנות"}
    capcut._atomic_write(draft_dir, draft)
    return {"adjusted": adjusted, "measured": len(measured),
            "target_db": round(target, 1), "max_adjustment_db": round(max_adj, 1),
            "backup": backup.name}


# ---------------------------------------------------------------- normalize

def _render_voice(plan: list[dict], duration_us: int) -> np.ndarray:
    """48kHz mono render of the speech timeline (quality bake, not STT)."""
    total = int(duration_us / US * VOICE_SR) + VOICE_SR
    audio = np.zeros(total, dtype=np.float32)
    for seg in plan:
        src = Path(seg["path"])
        if not src.exists():
            continue
        cmd = [stt.FFMPEG, "-v", "error",
               "-ss", f"{seg['source_start_us'] / US:.6f}",
               "-t", f"{seg['source_duration_us'] / US:.6f}",
               "-i", str(src), "-vn", "-ac", "1", "-ar", str(VOICE_SR)]
        if abs(seg.get("speed", 1.0) - 1.0) > 1e-3:
            cmd += ["-af", stt._atempo_chain(seg["speed"])]
        cmd += ["-f", "f32le", "-"]
        out = subprocess.run(cmd, capture_output=True)
        if out.returncode != 0 or not out.stdout:
            continue
        chunk = np.frombuffer(out.stdout, dtype=np.float32) * seg.get("volume", 1.0)
        start = int(seg["target_start_us"] / US * VOICE_SR)
        end = min(start + len(chunk), total)
        audio[start:end] += chunk[:end - start]
    np.clip(audio, -1.0, 1.0, out=audio)
    return audio


def _audio_donor() -> tuple[dict, dict, list]:
    """(material, segment, extras) of a plain audio clip from any draft."""
    for d in capcut.list_drafts():
        try:
            draft = capcut.load_draft(d["id"])
        except (OSError, json.JSONDecodeError):
            continue
        mats = {m["id"]: m for m in draft.get("materials", {}).get("audios", [])}
        idx = capcut._materials_index(draft)
        for track in draft.get("tracks", []):
            if track.get("type") != "audio":
                continue
            for seg in track.get("segments", []):
                mat = mats.get(seg.get("material_id"))
                if mat and mat.get("path"):
                    extras = [{"list": idx[r][0], "material": idx[r][1]}
                              for r in seg.get("extra_material_refs", []) if r in idx]
                    return (copy.deepcopy(mat), copy.deepcopy(seg), copy.deepcopy(extras))
    raise ValueError("לא נמצא דונור אודיו באף פרויקט")


def _unbake_voice(draft: dict) -> bool:
    """Remove a previously baked voice-master track and un-mute the originals,
    so mastering can be re-run with different options. Returns True if one was
    found. Only the segments *we* muted (volume 0 with a stored last_nonzero)
    are restored."""
    mats = draft.setdefault("materials", {})
    master_ids = {m["id"] for m in mats.get("audios", [])
                  if (m.get("material_name") or "").startswith("ccstudio-voice")}
    if not master_ids:
        return False
    dead = set(master_ids)
    kept = []
    for track in draft.get("tracks", []):
        segs = track.get("segments", [])
        if track.get("type") == "audio" and segs and \
                all(s.get("material_id") in master_ids for s in segs):
            for s in segs:
                dead.update(s.get("extra_material_refs", []))
            continue
        kept.append(track)
    draft["tracks"] = kept
    for lname, lst in mats.items():
        if isinstance(lst, list):
            mats[lname] = [m for m in lst
                           if not (isinstance(m, dict) and m.get("id") in dead)]
    for track in draft.get("tracks", []):
        if track.get("type") not in ("video", "audio"):
            continue
        for seg in track.get("segments", []):
            if seg.get("volume", 1.0) == 0 and seg.get("last_nonzero_volume", 0):
                seg["volume"] = seg["last_nonzero_volume"]
    return True


def master_voice(draft_id: str, denoise: bool = False, denoise_db: float = 12.0,
                 normalize: bool = True, target_lufs: float = -14.0) -> dict:
    """Unified voice bake: render the speech timeline once, run it through the
    requested chain (denoise and/or loudness normalization), and swap it in as a
    voice-master track with the originals muted.

    Re-runnable: an existing voice master is removed and the originals restored
    before re-rendering, so options can be changed without stacking bakes."""
    if not denoise and not normalize:
        raise ValueError("לא נבחר שום שיפור סאונד")
    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = capcut.DRAFTS_DIR / draft_id
    draft = capcut.load_draft(draft_id)
    duration = draft.get("duration", 0)

    rebaked = _unbake_voice(draft)  # so we always render from the real sources
    pairs = _speech_segments(draft, draft_id)
    plan = [e for _, entries in pairs for e in entries]
    if not plan:
        raise ValueError("לא נמצאו סגמנטים של דיבור")

    audio = _render_voice(plan, duration)
    if float(np.abs(audio).max()) < 1e-4:
        raise ValueError("האודיו ריק — ייתכן שחומרי הגלם על כונן לא מחובר")
    raw = audio.tobytes()
    out_path = draft_dir / VOICE_FILE

    # ---- build the chain
    pre = []
    if denoise:
        # rumble/hum out first, then adaptive spectral noise reduction — afftdn
        # learns the noise floor itself, so it is safe on speech
        nr = max(3.0, min(40.0, float(denoise_db)))
        pre.append("highpass=f=80")
        pre.append(f"afftdn=nr={nr:g}:nf=-28:tn=1")
    pre_chain = ",".join(pre)

    if normalize:
        target_lufs = max(-24.0, min(-9.0, float(target_lufs)))
        comp = "acompressor=threshold=-22dB:ratio=3:attack=8:release=150:makeup=3dB"
        base = f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
        measure = ",".join(filter(None, [pre_chain, comp, f"{base}:print_format=json"]))
        p1 = subprocess.run(
            [stt.FFMPEG, "-f", "f32le", "-ar", str(VOICE_SR), "-ac", "1", "-i", "pipe:",
             "-af", measure, "-f", "null", "-"],
            input=raw, capture_output=True)
        stderr = p1.stderr.decode(errors="replace")
        try:
            block = stderr[stderr.rindex("{"):]
            m = json.loads(block[:block.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"loudnorm measure failed: {stderr[-200:]}")
        chain = ",".join(filter(None, [
            pre_chain, comp,
            (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
             f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
             f":offset={m['target_offset']}:linear=true"),
            "alimiter=level_in=1:level_out=1:limit=0.841:attack=5:release=60:level=false"]))
    else:
        chain = pre_chain

    p2 = subprocess.run(
        [stt.FFMPEG, "-v", "error", "-y",
         "-f", "f32le", "-ar", str(VOICE_SR), "-ac", "1", "-i", "pipe:",
         "-af", chain, "-ar", str(VOICE_SR), "-c:a", "aac", "-b:a", "192k", str(out_path)],
        input=raw, capture_output=True)
    if p2.returncode != 0:
        raise RuntimeError(f"sound bake failed: {p2.stderr.decode()[:200]}")

    donor_mat, donor_seg, donor_extras = _audio_donor()
    backup = capcut._backup(draft_dir)
    mats = draft.setdefault("materials", {})
    mat = copy.deepcopy(donor_mat)
    mat.update({"id": capcut._new_id(), "path": str(out_path),
                "name": VOICE_FILE, "material_name": VOICE_FILE,
                "duration": duration, "type": "extract_music"})
    mats.setdefault("audios", []).append(mat)
    refs = []
    for ex in donor_extras:
        clone = copy.deepcopy(ex["material"])
        clone["id"] = capcut._new_id()
        mats.setdefault(ex["list"], []).append(clone)
        refs.append(clone["id"])
    seg = copy.deepcopy(donor_seg)
    seg.update({"id": capcut._new_id(), "material_id": mat["id"],
                "extra_material_refs": refs, "volume": 1.0, "speed": 1.0,
                "target_timerange": {"start": 0, "duration": duration},
                "source_timerange": {"start": 0, "duration": duration},
                "common_keyframes": []})
    draft["tracks"].append({
        "attribute": 0, "flag": 0, "id": capcut._new_id(),
        "is_default_name": True, "name": "", "segments": [seg], "type": "audio",
    })
    muted = 0
    for orig_seg, _entries in pairs:
        orig_seg["volume"] = 0.0
        orig_seg["last_nonzero_volume"] = orig_seg.get("last_nonzero_volume") or 1.0
        muted += 1
    capcut._atomic_write(draft_dir, draft)
    return {"muted_originals": muted, "denoise": denoise,
            "denoise_db": denoise_db if denoise else None,
            "target_lufs": target_lufs if normalize else None,
            "normalized": normalize, "rebaked": rebaked,
            "file": VOICE_FILE, "backup": backup.name}


def unbake(draft_id: str) -> bool:
    """Drop an existing voice-master track and restore the original speech
    volumes. Needed before balance_voices, which only sees unmuted segments."""
    if capcut.draft_locked(draft_id):
        raise RuntimeError("capcut_running")
    draft_dir = capcut.DRAFTS_DIR / draft_id
    draft = capcut.load_draft(draft_id)
    if not _unbake_voice(draft):
        return False
    capcut._backup(draft_dir)
    capcut._atomic_write(draft_dir, draft)
    return True


def normalize_voice(draft_id: str, target_lufs: float = -14.0) -> dict:
    """Loudness master only (kept for the existing chat op)."""
    return master_voice(draft_id, denoise=False, normalize=True,
                        target_lufs=target_lufs)


def denoise_voice(draft_id: str, denoise_db: float = 12.0) -> dict:
    """Noise reduction only — no loudness change."""
    return master_voice(draft_id, denoise=True, denoise_db=denoise_db,
                        normalize=False)
