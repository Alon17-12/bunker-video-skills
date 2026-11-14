import json, os, sys, subprocess, numpy as np
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import paths, transcribe
SP = os.path.expanduser(os.environ.get("WORK", "~/Movies/reel-captions-work/landing-16x9")); os.makedirs(SP, exist_ok=True)   # word caches live in a durable work dir, never the session scratchpad
p = os.path.expanduser(f"~/Movies/CapCut/User Data/Projects/com.lveditor.draft/{os.environ.get('DRAFT', '0919')}/draft_info.json")
d = json.load(open(p)); SR = 16000; US = 1e6
mats = {m["id"]: (k, m) for k, arr in d["materials"].items() if isinstance(arr, list) for m in arr if isinstance(m, dict) and "id" in m}
drafts = {dr["id"]: dr["draft"] for dr in d["materials"]["drafts"]}
def audio_file(seg):
    m = mats[seg["material_id"]][1]
    for r in seg["extra_material_refs"]:
        if r in drafts:
            nd = drafts[r]
            nm = {mm["id"]: mm for k, arr in nd["materials"].items() if isinstance(arr, list) for mm in arr if isinstance(mm, dict) and "id" in mm}
            best = max(((t, s) for t in nd["tracks"] for s in t["segments"]), key=lambda ts: ts[1].get("volume", 0))
            return nm[best[1]["material_id"]]["path"], best[1].get("volume", 1.0)
    return None, 1.0
def grab(path, ss, dur):
    cmd = [paths.FFMPEG, "-v", "error", "-ss", f"{ss:.6f}", "-t", f"{dur:.6f}", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
out = {"videos": []}
main = d["tracks"][0]["segments"]
groups = []
for s in main:
    f, vol = audio_file(s)
    if f is None: continue
    if groups and groups[-1]["file"] == f: groups[-1]["segs"].append(s)
    else: groups.append({"file": f, "vol": vol, "segs": [s]})
for gi, g in enumerate(groups):
    A = min(s["target_timerange"]["start"] for s in g["segs"]); B = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in g["segs"])
    buf = np.zeros(int((B - A) / US * SR) + SR, np.float32)
    for s in g["segs"]:
        ts = s["target_timerange"]["start"] / US; du = s["target_timerange"]["duration"] / US; ss = s["source_timerange"]["start"] / US
        x = grab(g["file"], ss, du); i0 = int(round((ts - A / US) * SR)); n = min(len(x), len(buf) - i0); buf[i0:i0 + n] = x[:n]
    buf = buf[:int((B - A) / US * SR)]
    np.save(f"{SP}/0919_v{gi+1}_audio.npy", buf)
    fr = buf[:len(buf)//800*800].reshape(-1, 800); rms = np.sqrt(np.mean(fr**2, axis=1)); act = rms[rms > np.percentile(rms, 50)]
    lvl = 20*np.log10(np.mean(act)*g["vol"] + 1e-9)
    words = transcribe.transcribe(buf)
    for w in words: w["start_s"] += A / US; w["end_s"] += A / US
    out["videos"].append({"file": g["file"], "A": A, "B": B, "speech_dbfs": round(float(lvl), 1), "pieces": [(s["target_timerange"]["start"]/US, s["target_timerange"]["duration"]/US, s["source_timerange"]["start"]/US) for s in g["segs"]], "words": words})
    print(f"video {gi+1}: {A/US:.2f}→{B/US:.2f} {len(words)} words speech {lvl:.1f} dBFS", flush=True)
    print(" ".join(w["text"] for w in words), flush=True)
    json.dump(out, open(f"{SP}/0919_words.json", "w"), ensure_ascii=False, indent=0)
    json.dump(out, open(os.path.expanduser("~/Desktop/0919 דף תודה — תמלול.json"), "w"), ensure_ascii=False, indent=0)
print("DONE")
