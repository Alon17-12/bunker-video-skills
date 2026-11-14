"""Section export for a promo cut into teasers by white cards (0910 pattern).

  python3 section_export.py plan  <draft folder> <plan.json>        # section ranges = main-track camera runs (white cards excluded)
  python3 section_export.py srt   <draft folder> <out.srt> [track]  # full-coverage SRT from the draft's caption track (default 'כתוביות')
  python3 section_export.py split <full.mp4> <full.srt|-> <plan.json> <out dir>
        # "<out>/<name>/<name>.mp4" + "<out>/<name>/<name>.srt" per section; SRT cues clipped to the range and shifted to 0

Why a separate SRT per section: the client-facing deliverable is eight standalone teasers, and each one is
uploaded on its own — a subtitle file whose first cue starts at 00:03:24 is useless on a 20s file. Times are
shifted by −start, cues straddling a boundary are clipped, and the file is written utf-8-sig so Hebrew
opens correctly in every player. If CapCut's SRT export is missing (it only exports what CapCut marks as
subtitles — kinetic word stacks are not in it) build the SRT from the draft with `srt` instead.
Video cuts are re-encoded (libx264 CRF 15, aac 256k) because a stream copy can only cut on keyframes and
the boundaries are exact card edges."""
import json, os, re, subprocess, sys
FF = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
def _ts(t):
    t = max(t, 0.0); h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    if ms == 1000: s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def parse_srt(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n"); cues = []
    for blk in re.split(r"\n\s*\n", raw.strip()):
        lines = blk.strip().split("\n")
        if len(lines) < 2: continue
        ti = 0 if "-->" in lines[0] else 1
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lines[ti])
        if not m: continue
        v = [int(x) for x in m.groups()]; text = "\n".join(lines[ti + 1:]).strip()
        if text: cues.append((v[0]*3600 + v[1]*60 + v[2] + v[3]/1000, v[4]*3600 + v[5]*60 + v[6] + v[7]/1000, text))
    return sorted(cues)
def merge_overlaps(cues):
    """CapCut's SRT export includes kinetic text clips as overlapping cues (one per word / line). Fold every
    overlapping cluster into one cue: single-word members join with spaces (a word stack), longer members
    stack as lines. Players disagree on how to show simultaneous cues, so the deliverable has none."""
    out = []
    for a, b, t in cues:
        if out and a < out[-1][1] - 0.01:
            pa, pb, pt = out[-1]; grp = pt + [t]; out[-1] = (pa, max(pb, b), grp)
        else: out.append((a, b, [t]))
    res = []
    for a, b, grp in out:
        res.append((a, b, " ".join(grp) if all(len(g.split()) == 1 for g in grp) and len(grp) > 1 else "\n".join(grp)))
    return res
def write_srt(cues, path, start=0.0, end=1e9):
    n = 0
    with open(path, "w", encoding="utf-8-sig") as f:
        for a, b, text in cues:
            if b <= start + 0.05 or a >= end - 0.05: continue
            a2, b2 = max(a, start) - start, min(b, end) - start
            if b2 - a2 < 0.08: continue
            n += 1; f.write(f"{n}\n{_ts(a2)} --> {_ts(b2)}\n{text}\n\n")
    return n
def load(draft): return json.load(open(os.path.join(draft, "draft_info.json")))
def cues_from_draft(draft, track_name="כתוביות"):
    d = load(draft); texts = {m["id"]: m for m in d["materials"]["texts"]}; cues = []
    for t in d["tracks"]:
        if t.get("type") != "text" or t.get("name") != track_name: continue
        for s in t["segments"]:
            c = texts[s["material_id"]]["content"]
            try: txt = json.loads(c)["text"]
            except Exception: txt = re.sub(r"<[^>]+>", "", c)
            a = s["target_timerange"]["start"] / 1e6; cues.append((a, a + s["target_timerange"]["duration"] / 1e6, txt.strip()))
    return sorted(cues)
def plan_from_draft(draft):
    """Camera runs on the main video track; a photo material (white card) ends a run."""
    d = load(draft); vids = {m["id"]: m for m in d["materials"]["videos"]}; runs = []; cur = None
    for s in d["tracks"][0]["segments"]:
        a = s["target_timerange"]["start"] / 1e6; b = a + s["target_timerange"]["duration"] / 1e6
        if vids[s["material_id"]].get("type") == "photo": cur = None; continue
        if cur is None: cur = [a, b]; runs.append(cur)
        else: cur[1] = b
    return [{"name": f"{i:02d}", "start": round(a, 3), "end": round(b, 3)} for i, (a, b) in enumerate(runs, 1)]
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        plan = plan_from_draft(sys.argv[2]); json.dump(plan, open(sys.argv[3], "w"), ensure_ascii=False, indent=1); print(json.dumps(plan, ensure_ascii=False))
    elif cmd == "srt":
        cues = cues_from_draft(sys.argv[2], *(sys.argv[4:5])); print(write_srt(cues, sys.argv[3]), "cues →", sys.argv[3])
    elif cmd == "split":
        src, srt, plan, out = sys.argv[2:6]; cues = merge_overlaps(parse_srt(srt)) if srt != "-" else []
        for p in json.load(open(plan)):
            os.makedirs(f"{out}/{p['name']}", exist_ok=True); dst = f"{out}/{p['name']}/{p['name']}.mp4"
            subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{p['start']:.3f}", "-to", f"{p['end']:.3f}", "-i", src, "-c:v", "libx264", "-preset", "slow", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", dst], check=True)
            n = write_srt(cues, f"{out}/{p['name']}/{p['name']}.srt", p["start"], p["end"]) if cues else 0
            print(f"cut {p['name']}: {p['end']-p['start']:.2f}s, {n} cues", flush=True)
