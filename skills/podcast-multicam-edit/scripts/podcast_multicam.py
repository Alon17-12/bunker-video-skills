# -*- coding: utf-8 -*-
"""Audio-driven multicam routing for CapCut podcast episodes.

A two-person (or N-person) podcast is recorded as ONE multicam clip (each guest
has a camera) plus ONE audio track PER MIC. This tool cuts the multicam to
whoever is speaking, decided by which mic is louder — the same thing a human
editor does by eye, done from the waveform.

Subcommands (all READ the draft to analyze; only `--write` mutates it, and only
when CapCut is CLOSED):

  analyze  <draft>                        learn camera<->mic mapping + cadence, cache envelopes
  route    <draft> [--from S] [--max N]   auto-route from S..end (louder-mic + reaction cutaways)
  maxshot  <draft> --max N [--from S]     enforce a max-shot on the CURRENT draft, keeping every
                                          existing cut/edit (splits only shots longer than N)

Design notes live in ../references/algorithm.md. SAFETY: never writes while the
draft is open in CapCut (draft_locked); always _backup()s first; atomic write.

Usage:
  python podcast_multicam.py analyze "אלון ובן המנוקליק"
  python podcast_multicam.py route   "אלון ובן המנוקליק" --from 214.2 --max 15 --write
  python podcast_multicam.py maxshot "אלון ובן המנוקליק" --max 10 --write
"""
import sys, os, json, copy, subprocess, argparse
import numpy as np

APP = os.path.expanduser("~/bunker-video-engine/app")
sys.path.insert(0, APP)
import capcut, paths

HOP = 0.05                         # envelope hop (s)
SMOOTH = 1.0                       # envelope smoothing (s)
CACHE = os.path.expanduser("~/Desktop/.multicam-cache")   # durable envelope cache

# ---- tunables (match a snappy podcast feel; override per call if needed) ----
MIN_SHOT   = 1.3
HOLD       = 0.35                  # new speaker must dominate this long to switch
MARGIN     = 1.05                  # candidate must be this ratio louder to switch
REACT_MIN  = 1.6                   # shortest reaction cutaway
SNAP_WIN   = 0.6                   # snap a cut to the quietest moment within +-this
SNAP_FLOOR = 1.45                  # keep shots >= this when snapping (anti-flicker)


# ================= draft / folder resolution =================
def resolve_folder(display_name):
    """CapCut's on-disk FOLDER name can differ from the display name (duplicate
    projects become 'name (1)', some are named '0730'). Match by duration."""
    try:
        capcut.load_draft(display_name); return display_name
    except Exception:
        pass
    meta = next((d for d in capcut.list_drafts() if d["name"] == display_name), None)
    if not meta:
        raise SystemExit(f"draft not found in CapCut list: {display_name!r}")
    target = meta.get("duration_us", 0)
    best = None
    for p in capcut.DRAFTS_DIR.iterdir():
        if not p.is_dir():
            continue
        try:
            d = capcut.load_draft(p.name)
        except Exception:
            continue
        if abs(d.get("duration", 0) - target) < 100000:      # 0.1s
            mt = p.stat().st_mtime
            if best is None or mt > best[1]:
                best = (p.name, mt)
    if not best:
        raise SystemExit(f"no on-disk draft_info.json matches {display_name!r}")
    return best[0]


# ================= audio envelopes =================
def mic_tracks(draft):
    """Return [(name, path, src_offset_s)] for each full-length audio track = a mic."""
    auds = {m["id"]: m for m in draft["materials"].get("audios", [])}
    out = []
    for t in draft["tracks"]:
        if t.get("type") == "audio" and t.get("segments"):
            s = t["segments"][0]; m = auds.get(s["material_id"], {})
            out.append((m.get("name", "?"), m.get("path", ""),
                        s["source_timerange"]["start"] / 1e6))
    return out


def envelope(path, off, dur):
    ff = str(paths.FFMPEG)
    cmd = [ff, "-v", "error", "-ss", str(off), "-t", str(dur),
           "-i", path, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    n = int(HOP * 8000); m = len(a) // n
    return np.sqrt((a[:m * n].reshape(m, n) ** 2).mean(axis=1) + 1e-9)


def load_envelopes(folder, draft):
    """RMS envelopes for exactly 2 mics, cached on disk keyed by folder name."""
    os.makedirs(CACHE, exist_ok=True)
    key = os.path.join(CACHE, folder.replace("/", "_"))
    mics = mic_tracks(draft)
    if len(mics) < 2:
        raise SystemExit(f"need 2 mic audio tracks, found {len(mics)}")
    end = draft["duration"] / 1e6
    envs = []
    for i, (nm, pth, off) in enumerate(mics[:2]):
        cf = f"{key}.e{i}.npy"
        if os.path.exists(cf):
            envs.append(np.load(cf))
        else:
            if not os.path.exists(pth):
                raise SystemExit(f"mic file missing: {pth}")
            e = envelope(pth, off, end); np.save(cf, e); envs.append(e)
    L = min(len(envs[0]), len(envs[1]))
    return envs[0][:L], envs[1][:L], mics


def smooth(e):
    w = max(1, int(SMOOTH / HOP)); k = np.ones(w) / w
    return np.convolve(e, k, "same")


# ================= camera model =================
def seg_cam(draft_vids, seg):
    return draft_vids[seg["material_id"]]["multi_camera_info"]["cur_camera_track_id"]


def camera_map(draft, s1, s2):
    """Learn {short_cam_id: 'mic1'|'mic2'} from existing cuts by which mic is
    louder while each camera is shown. Returns (mic1_cam, mic2_cam, cam_full,
    cam_tpl_material, agreement%)."""
    vids = {m["id"]: m for m in draft["materials"]["videos"]}
    vt = next(t for t in draft["tracks"] if t.get("type") == "video")
    segs = sorted(vt["segments"], key=lambda s: s["target_timerange"]["start"])
    tally, cam_full, cam_tpl = {}, {}, {}
    for s in segs:
        full = seg_cam(vids, s); short = full[-12:]
        cam_full[short] = full; cam_tpl[short] = vids[s["material_id"]]
        a = s["target_timerange"]["start"] / 1e6
        b = a + s["target_timerange"]["duration"] / 1e6
        ia, ib = int(a / HOP), int(b / HOP)
        if ib <= ia:
            continue
        r1, r2 = s1[ia:ib].mean(), s2[ia:ib].mean()
        d = tally.setdefault(short, [0.0, 0.0])
        d[0 if r1 > r2 else 1] += (b - a)
    mic1_cam = max(tally, key=lambda c: tally[c][0])
    mic2_cam = max(tally, key=lambda c: tally[c][1])
    return mic1_cam, mic2_cam, cam_full, cam_tpl


# ================= routing core =================
def route(s1, s2, L, a_s, b_s, start_cam, cam_mic1, cam_mic2, floor):
    ia, ib = int(a_s / HOP), min(int(b_s / HOP), L)
    cam = start_cam; cuts = [[ia, cam]]; cand, cand_since = cam, ia; shot_start = ia
    for i in range(ia + 1, ib):
        v1, v2 = s1[i], s2[i]
        if max(v1, v2) < floor:
            cand, cand_since = cam, i; continue
        want = cam_mic1 if v1 > v2 * MARGIN else (cam_mic2 if v2 > v1 * MARGIN else cam)
        if want != cam:
            if want != cand:
                cand, cand_since = want, i
            if (i - cand_since) * HOP >= HOLD and (i - shot_start) * HOP >= MIN_SHOT:
                cam = want; cuts.append([i, cam]); shot_start = i
        else:
            cand, cand_since = cam, i
    out = []
    for j, (fi, c) in enumerate(cuts):
        fe = cuts[j + 1][0] if j + 1 < len(cuts) else ib
        out.append((fi * HOP, fe * HOP, c))
    merged = []
    for seg in out:
        if merged and (seg[1] - seg[0]) < MIN_SHOT:
            merged[-1] = (merged[-1][0], seg[1], merged[-1][2])
        else:
            merged.append(seg)
    final = []
    for seg in merged:
        if final and final[-1][2] == seg[2]:
            final[-1] = (final[-1][0], seg[1], seg[2])
        else:
            final.append(list(seg))
    return [tuple(x) for x in final]


def split_long(a, b, cam, s1, s2, L, cam_mic1, cam_mic2, max_shot):
    """Break [a,b] (camera cam) so no piece exceeds max_shot, inserting reaction
    cutaways to the other camera at listener-present moments. Endpoints fixed."""
    if b - a <= max_shot + 0.01:
        return [(a, b, cam)]
    other = cam_mic2 if cam == cam_mic1 else cam_mic1
    spk = s1 if cam == cam_mic1 else s2
    lis = s2 if cam == cam_mic1 else s1
    out = []; t = a
    while b - t > max_shot:
        hi = min(t + max_shot - 0.5, b - 2.5); lo = max(t + 5.0, hi - 4.0)
        if hi <= lo:
            tc = hi
        else:
            i0, i1 = int(lo / HOP), min(int(hi / HOP), L)
            tc = (i0 + int(np.argmax(lis[i0:i1] - spk[i0:i1]))) * HOP
        tc = min(max(tc, t + 5.0), t + max_shot - 0.5)
        j = int(tc / HOP); r_end = j; lim = min(int((tc + 2.8) / HOP), L - 1)
        while r_end < lim and lis[r_end] > 0.5 * spk[r_end]:
            r_end += 1
        r = max(REACT_MIN, min(2.8, (r_end - j) * HOP))
        if tc + r >= b:
            r = max(0.8, b - tc - 0.5)
        out.append((t, tc, cam)); out.append((tc, tc + r, other)); t = tc + r
    out.append((t, b, cam))
    return snap(out, s1 + s2, L, max_shot, internal_only=True)


def snap(plan, comb, L, max_shot, internal_only=False):
    """Move each cut to the quietest nearby moment (min of s1+s2) so cuts land on
    breaths/pauses. internal_only keeps the very first/last endpoints fixed."""
    p = [list(x) for x in plan]
    rng = range(len(p) - 1)
    for i in rng:
        a_i, t, a_nx = p[i][0], p[i][1], p[i + 1][1]
        lo = max(t - SNAP_WIN, a_i + SNAP_FLOOR, a_nx - max_shot)
        hi = min(t + SNAP_WIN, a_nx - SNAP_FLOOR, a_i + max_shot)
        if hi <= lo:
            continue
        i0, i1 = int(lo / HOP), min(int(hi / HOP), L)
        if i1 <= i0:
            continue
        tn = (i0 + int(np.argmin(comb[i0:i1]))) * HOP
        p[i][1] = tn; p[i + 1][0] = tn
    return [tuple(x) for x in p]


# ================= write helpers =================
def clone_segment(tpl_seg, mat, a_us, b_us, off):
    ns = copy.deepcopy(tpl_seg); ns["id"] = capcut._new_id(); ns["material_id"] = mat["id"]
    ns["target_timerange"] = {"start": a_us, "duration": b_us - a_us}
    ns["source_timerange"] = {"start": int(a_us + off), "duration": b_us - a_us}
    return ns


def write_track(folder, draft, vt, new_segs):
    if capcut.draft_locked(folder):
        raise SystemExit("STILL_LOCKED — close CapCut and re-run")
    new_segs.sort(key=lambda s: s["target_timerange"]["start"])
    for A, B in zip(new_segs, new_segs[1:]):
        ae = A["target_timerange"]["start"] + A["target_timerange"]["duration"]
        assert abs(ae - B["target_timerange"]["start"]) < 1500, f"gap at {ae/1e6:.2f}s"
    vt["segments"] = new_segs
    dd = capcut.DRAFTS_DIR / folder
    capcut._backup(dd); capcut._atomic_write(dd, draft)


# ================= subcommands =================
def cmd_analyze(folder, draft, s1s, s2s, L):
    vids = {m["id"]: m for m in draft["materials"]["videos"]}
    vt = next(t for t in draft["tracks"] if t.get("type") == "video")
    segs = sorted(vt["segments"], key=lambda s: s["target_timerange"]["start"])
    m1, m2, cam_full, _ = camera_map(draft, s1s, s2s)
    print(f"cameras: mic1 -> {m1}   mic2 -> {m2}")
    durs = [s["target_timerange"]["duration"]/1e6 for s in segs]
    print(f"existing cuts: {len(segs)} | shot len min{min(durs):.1f} "
          f"med{np.median(durs):.1f} max{max(durs):.1f}s")
    # agreement of louder-mic vs shown camera
    agree = tot = 0
    for s in segs:
        a = s["target_timerange"]["start"]/1e6; b = a + s["target_timerange"]["duration"]/1e6
        for i in range(int(a/HOP), min(int(b/HOP), L)):
            pred = m1 if s1s[i] > s2s[i] else m2
            agree += (pred == seg_cam(vids, s)[-12:]); tot += 1
    print(f"louder-mic reproduces shown camera: {100*agree/max(tot,1):.1f}%")


def cmd_route(folder, draft, s1s, s2s, L, frm, max_shot, do_write):
    vids = {m["id"]: m for m in draft["materials"]["videos"]}
    vt = next(t for t in draft["tracks"] if t.get("type") == "video")
    segs = sorted(vt["segments"], key=lambda s: s["target_timerange"]["start"])
    m1, m2, cam_full, cam_tpl = camera_map(draft, s1s, s2s)
    floor = 0.4 * np.median(np.maximum(s1s, s2s))
    keep = [s for s in segs if s["target_timerange"]["start"]/1e6 < frm - 0.05]
    if not keep:
        raise SystemExit("nothing kept before --from; refusing to wipe the whole track")
    start_cam = seg_cam(vids, keep[-1])[-12:]
    base = route(s1s, s2s, L, frm, draft["duration"]/1e6, start_cam, m1, m2, floor)
    plan = []
    for a, b, c in base:
        plan.extend(split_long(a, b, c, s1s, s2s, L, m1, m2, max_shot))
    plan = snap(plan, s1s + s2s, L, max_shot)
    plan.sort(key=lambda x: x[0])
    off = keep[-1]["source_timerange"]["start"] - keep[-1]["target_timerange"]["start"]  # 1:1 usually
    # source offset for the generated region: read a segment at/after frm if present
    after = [s for s in segs if s["target_timerange"]["start"]/1e6 >= frm - 0.05]
    if after:
        off = after[0]["source_timerange"]["start"] - after[0]["target_timerange"]["start"]
    tpl_seg = (after or keep)[-1]
    durs = [b - a for a, b, c in plan]
    print(f"route {frm:.0f}..end | {len(plan)} shots | med {np.median(durs):.1f}s "
          f"max {max(durs):.1f}s | keep {len(keep)} before")
    if not do_write:
        print("(dry-run — add --write with CapCut closed)"); return
    new = list(keep)
    start_us = keep[-1]["target_timerange"]["start"] + keep[-1]["target_timerange"]["duration"]
    end_us = int(draft["duration"])
    for idx, (a, b, c) in enumerate(plan):
        a_us = start_us if idx == 0 else int(a * 1e6)
        b_us = end_us if idx == len(plan) - 1 else int(b * 1e6)
        mat = copy.deepcopy(cam_tpl[c]); mat["id"] = capcut._new_id()
        draft["materials"]["videos"].append(mat)
        new.append(clone_segment(tpl_seg, mat, a_us, b_us, off))
    write_track(folder, draft, vt, new)
    print(f"WROTE — {len(new)} video segments")


def cmd_maxshot(folder, draft, s1s, s2s, L, frm, max_shot, do_write):
    vids = {m["id"]: m for m in draft["materials"]["videos"]}
    vt = next(t for t in draft["tracks"] if t.get("type") == "video")
    segs = sorted(vt["segments"], key=lambda s: s["target_timerange"]["start"])
    m1, m2, cam_full, cam_tpl = camera_map(draft, s1s, s2s)
    new = []; nsplit = 0
    for seg in segs:
        a = seg["target_timerange"]["start"]/1e6
        b = a + seg["target_timerange"]["duration"]/1e6
        cam = seg_cam(vids, seg)[-12:]
        if a < frm - 0.05 or (b - a) <= max_shot + 0.01:
            new.append(seg); continue
        pieces = split_long(a, b, cam, s1s, s2s, L, m1, m2, max_shot)
        if len(pieces) == 1:
            new.append(seg); continue
        nsplit += 1
        off = seg["source_timerange"]["start"] - seg["target_timerange"]["start"]
        for pa, pb, pc in pieces:
            if pc == cam:
                mat = copy.deepcopy(vids[seg["material_id"]])
            else:
                mat = copy.deepcopy(cam_tpl[pc])
            mat["id"] = capcut._new_id(); draft["materials"]["videos"].append(mat)
            new.append(clone_segment(seg, mat, int(pa*1e6), int(pb*1e6), off))
    mx = max((s["target_timerange"]["duration"]/1e6 for s in new), default=0)
    print(f"maxshot {max_shot}s: split {nsplit} long shots -> {len(new)} segments | max now {mx:.1f}s")
    if not do_write:
        print("(dry-run — add --write with CapCut closed)"); return
    write_track(folder, draft, vt, new)
    print(f"WROTE — {len(new)} video segments")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["analyze", "route", "maxshot"])
    ap.add_argument("draft")
    ap.add_argument("--from", dest="frm", type=float, default=0.0)
    ap.add_argument("--max", dest="max_shot", type=float, default=None)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    folder = resolve_folder(a.draft)
    draft = capcut.load_draft(folder)
    s1, s2, mics = load_envelopes(folder, draft)
    L = min(len(s1), len(s2))
    s1s, s2s = smooth(s1)[:L], smooth(s2)[:L]
    print(f"draft folder: {folder!r} | {draft['duration']/1e6:.0f}s | mics: "
          f"{mics[0][0]}, {mics[1][0]}")

    if a.cmd == "analyze":
        cmd_analyze(folder, draft, s1s, s2s, L)
    elif a.cmd == "route":
        cmd_route(folder, draft, s1s, s2s, L, a.frm, a.max_shot or 15.0, a.write)
    elif a.cmd == "maxshot":
        if a.max_shot is None:
            raise SystemExit("maxshot needs --max N")
        cmd_maxshot(folder, draft, s1s, s2s, L, a.frm, a.max_shot, a.write)


if __name__ == "__main__":
    main()
