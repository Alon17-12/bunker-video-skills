#!/usr/bin/env python3
"""Camera routing from the mics alone — «מקור» ignored (אורח D 29.10.2026: the live switch was right 61 % of the time,
Alon: «תתעלם לגמרי מקובץ המקור ותשאיר רק את שתי המצלמות הראשיות … חשוב שיראו את 2 כשיש אינפוט ממיקרופונים 2 ו-3»).

    routing_from_mics.py <session> --from 79.1 --to 4147.8 [--mic-cam 1=1,2=2,3=2] [--base 1]
                         [--project "<CapCut project>" --track 2 [--write]]

1. Words of the transcript (source clock, tagged with the loudest mic) → runs per camera (same camera, gaps < --merge s).
2. A run of only backchannel words («כן», «נכון», «וואו») shorter than --min-shot stays off screen; any other speech of a
   listener-camera mic (≥ 0.4 s, or a question) is shown — a short question is held --min-shot s into the answer.
3. Cuts sit in the pause before the new speaker: --lead s before the first word, never before the last word of the
   previous speaker; on the 30 fps grid. A shot shorter than --min-shot takes the camera of the shot before it.
4. Writes <session>/פרק/ניתוב-מיקרופונים.json {shots: [[cam, from, to]], stats} (source clock).
With --project: the camera track --track (index in draft tracks; the camera that is NOT --base) is cut so it is on screen
only on its shots; the base camera track stays whole underneath. Backup first; CapCut must be closed.
"""
import argparse, copy, json, math, sys, uuid
from pathlib import Path

FPS = 30


def frame(t):
    return round(t * FPS) / FPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--from", dest="t0", type=float, required=True)
    ap.add_argument("--to", dest="t1", type=float, required=True)
    ap.add_argument("--mic-cam", default="1=1,2=2,3=2"); ap.add_argument("--base", type=int, default=1)
    ap.add_argument("--merge", type=float, default=1.0)
    ap.add_argument("--lead", type=float, default=0.2); ap.add_argument("--min-shot", type=float, default=1.2)
    ap.add_argument("--project"); ap.add_argument("--track", type=int, default=2); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    S = Path(a.session)
    mc = {int(k): int(v) for k, v in (x.split("=") for x in a.mic_cam.split(","))}
    words = [w for w in json.loads((S / "תמלול/transcript.json").read_text())["words"]
             if a.t0 <= w["start_s"] < a.t1 and w.get("mic") in mc]

    # 1. runs
    runs = []
    for w in words:
        c = mc[w["mic"]]
        if runs and runs[-1][2] == c and w["start_s"] - runs[-1][1] < a.merge:
            runs[-1][1] = max(runs[-1][1], w["end_s"]); runs[-1][3] += 1
        else:
            runs.append([w["start_s"], w["end_s"], c, 1])
    # 1b. a listener mic leading ≥ 2 s with no words (a laugh, unintelligible talk): the audit's 0.5 s mic-lead samples
    aud = S / "פרק/ניתוב.json"
    if aud.exists():
        smp = [x for x in json.loads(aud.read_text())["samples"] if a.t0 <= x["t"] < a.t1]
        cur = None
        for x in smp + [{"t": a.t1, "spk": 0}]:
            if x["spk"] in mc and mc[x["spk"]] != a.base:
                cur = cur or [x["t"], x["t"]]; cur[1] = x["t"] + 0.5
            elif cur:
                if cur[1] - cur[0] >= 2.0 and not any(cur[0] <= w["start_s"] < cur[1] and mc[w["mic"]] == a.base for w in words):
                    runs.append([cur[0], cur[1], [c for c in mc.values() if c != a.base][0], 3])
                cur = None
        runs.sort(key=lambda r: r[0])
    # 2. interjections stay off screen
    def remerge(rs):
        out = []
        for r in rs:
            if out and out[-1][2] == r[2]:
                out[-1][1] = max(out[-1][1], r[1]); out[-1][3] += r[3]
            else:
                out.append(list(r))
        return out
    BACK = {"כן", "וואו", "נכון", "אוקיי", "אה", "מעולה", "יפה", "ברור", "טוב", "ענק", "וואי", "מממ", "אהה", "בדיוק", "לגמרי", "וואלה", "בסדר", "כי", "אז", "רגע"}
    def keep_run(r):
        ws = [w for w in words if r[0] <= w["start_s"] <= r[1] and mc[w["mic"]] == r[2]]
        toks = [w["text"].strip(".,?!") for w in ws]
        if all(t in BACK for t in toks): return r[1] - r[0] >= a.min_shot      # «וואו וואו» is a real reaction, «כן» is not
        return r[1] - r[0] >= 0.6 if len(ws) == 1 else r[1] - r[0] >= 0.4 or any("?" in w["text"] for w in ws)
    runs = remerge([r for r in runs if keep_run(r)])          # also the base speaker's «כן» inside a host's question

    # 3. cuts in the pause before the new speaker
    shots, cur, start = [], runs[0][2] if runs else a.base, a.t0
    for prev, nxt in zip(runs, runs[1:]):
        cut = nxt[0] if nxt[0] <= prev[1] else max(prev[1], nxt[0] - a.lead)
        cut = frame(cut)
        shots.append([cur, start, cut]); cur, start = nxt[2], cut
    shots.append([cur, start, a.t1])
    shots = [s for s in shots if s[2] - s[1] > 1e-6]
    # short shots take the camera before them, then same-camera neighbours merge
    changed = True
    while changed:
        changed = False
        for i, s in enumerate(shots):
            if s[2] - s[1] < a.min_shot - 1e-3 and len(shots) > 1:
                # a short shot of the listener camera (a question) is held longer into the next shot when that one can spare it
                if s[0] != a.base and i + 1 < len(shots) and shots[i + 1][2] - (s[1] + a.min_shot) >= a.min_shot:
                    s[2] = shots[i + 1][1] = math.ceil((s[1] + a.min_shot) * FPS - 1e-6) / FPS
                else:
                    s[0] = shots[i - 1][0] if i > 0 else shots[i + 1][0]
                changed = True
        m = []
        for s in shots:
            if m and m[-1][0] == s[0]: m[-1][2] = s[2]
            else: m.append(list(s))
        if len(m) < len(shots): changed = True
        shots = m

    # stats: how much of each speaker's talking is on his camera
    def cam_at(t):
        for c, x, y in shots:
            if x <= t < y: return c
    cover = {}
    for k in mc:
        ws = [w for w in words if w["mic"] == k]
        tot = sum(w["end_s"] - w["start_s"] for w in ws)
        ok = sum(w["end_s"] - w["start_s"] for w in ws if cam_at((w["start_s"] + w["end_s"]) / 2) == mc[k])
        cover[k] = round(ok / tot * 100, 1) if tot else None
    dur = a.t1 - a.t0
    lens = [y - x for _, x, y in shots]
    stats = {"shots": len(shots), "cuts_per_min": round((len(shots) - 1) / (dur / 60), 2),
             "cam_share_pct": {c: round(sum(y - x for cc, x, y in shots if cc == c) / dur * 100, 1) for c in sorted(set(mc.values()))},
             "speaker_on_own_camera_pct": cover, "shortest": round(min(lens), 2), "longest": round(max(lens), 1)}
    out = S / "פרק/ניתוב-מיקרופונים.json"
    out.write_text(json.dumps({"from": a.t0, "to": a.t1, "mic_cam": mc, "shots": shots, "stats": stats}, ensure_ascii=False, indent=1))
    print(json.dumps(stats, ensure_ascii=False)); print("→", out)

    if not a.project: return
    sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
    import capcut
    import subprocess
    if a.write and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("CapCut is running — quit it first")
    P = capcut.DRAFTS_DIR / a.project
    f = P / "draft_info.json"
    d = json.loads(f.read_text())
    tr = d["tracks"][a.track]
    if len(tr["segments"]) != 1 and not a.write:
        print(f"note: track {a.track} already has {len(tr['segments'])} segments — rebuilding from its first one's material")
    seg0 = min(tr["segments"], key=lambda s: s["target_timerange"]["start"])
    t_in = seg0["source_timerange"]["start"] - seg0["target_timerange"]["start"]   # source = timeline + t_in (µs)
    other = [c for c in sorted(set(mc.values())) if c != a.base][0]
    segs = []
    for c, x, y in shots:
        if c != other: continue
        s = copy.deepcopy(seg0); s["id"] = str(uuid.uuid4()).upper()
        st = int(round(x * 1e6)) - t_in; du = int(round(y * 1e6)) - int(round(x * 1e6))
        s["target_timerange"] = {"start": st, "duration": du}
        s["source_timerange"] = {"start": st + t_in, "duration": du}
        segs.append(s)
    print(f"track {a.track}: {len(segs)} segments of camera {other} (timeline = source − {t_in / 1e6:.3f})")
    if not a.write:
        print("dry run"); return
    import shutil, time
    shutil.copy2(f, P / f"draft_info.before-routing-{time.strftime('%H%M%S')}.json")
    tr["segments"] = segs
    tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(d, ensure_ascii=False)); json.loads(tmp.read_text()); tmp.replace(f)
    print("WRITTEN", f)


if __name__ == "__main__":
    main()
