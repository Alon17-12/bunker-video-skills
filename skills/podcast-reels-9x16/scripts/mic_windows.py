# -*- coding: utf-8 -*-
"""Read the two ISO mics against a finished reels draft and print everything the
editing rules depend on, each line tagged with whether the edit already honours
it. Read-only.

    .venv/bin/python mic_windows.py "<project>" --audio "<episode>/… - אודיו" \
        [--report host,crosstalk,silence,shots]

`--audio` is the folder holding the per-mic wavs; mic n is matched by an "n" in
the filename, and mic n belongs to camera n.

Why the ratio and not the level: mic bleed puts one man at 5-15% of his own
level on the other's mic, so "both mics are loud" is almost always one person
talking. What separates them is the RATIO — one mic owning the sound by a factor
of several, versus neither owning it.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app"))
import capcut  # noqa: E402

FFMPEG = os.path.expanduser("~/ffmpeg-bin/ffmpeg")
FPS = 100                 # envelope resolution, Hz
OWNS = 1.5                # mic n is louder by this much -> speaker n
AMBIG = (0.40, 2.50)      # neither mic owns the sound
MIN_HOST = 0.40           # shortest interjection worth cutting to
MIN_CROSS = 0.25
MIN_SIL = 0.70


def envelope(path, start, dur):
    raw = subprocess.run(
        [FFMPEG, "-v", "error", "-ss", f"{max(start,0):.3f}", "-t", f"{dur:.3f}",
         "-i", path, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
        capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    h = 8000 // FPS
    k = max(len(x) // h, 1)
    e = np.sqrt((x[:k * h].reshape(k, h) ** 2).mean(1)) if k else np.zeros(1)
    return np.convolve(e, np.ones(9) / 9, mode="same")


def mic_paths(folder):
    out = {}
    for f in sorted(os.listdir(folder)):
        # "._name.wav" is an AppleDouble stub of a few KB that sorts first and
        # decodes to zero samples — pick it up and every envelope comes back empty
        if f.startswith("._") or not f.lower().endswith(".wav") or "mix" in f.lower():
            continue
        m = re.search(r"(\d)", os.path.splitext(f)[0].split("אודיו")[-1] or f)
        if m:
            out.setdefault(int(m.group(1)), os.path.join(folder, f))
    if set(out) != {1, 2}:
        raise SystemExit(f"expected two numbered mic wavs, found {sorted(out)}")
    return out


def runs(mask, fps=FPS, floor=0.0):
    """[(start_s, end_s)] of contiguous True at least `floor` seconds long"""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if (j - i) / fps >= floor:
                out.append((i / fps, j / fps))
            i = j
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--audio", required=True, help="folder with the per-mic wavs")
    ap.add_argument("--offsets", help="JSON {work_copy_name: absolute_start_seconds}; "
                                      "omit when the draft plays the raw angles")
    ap.add_argument("--report", default="host,crosstalk,silence,shots")
    args = ap.parse_args()
    want = set(args.report.split(","))
    mics = mic_paths(args.audio)
    offsets = json.load(open(args.offsets)) if args.offsets else {}

    d = capcut.load_draft(args.project)
    vm = {m["id"]: m for m in d["materials"]["videos"]}
    bots = sorted(d["tracks"][0]["segments"], key=lambda s: s["target_timerange"]["start"])
    top = sorted(d["tracks"][1]["segments"], key=lambda s: s["target_timerange"]["start"])
    vis = [(s["target_timerange"]["start"] / 1e6,
            (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6)
           for s in top if s["clip"].get("alpha", 1.0) > 0.5]

    def cam1_on(t):
        return any(a <= t < b for a, b in vis)

    host, cross, sil = [], [], []
    for s in bots:
        mat = vm[s["material_id"]]
        name = mat.get("material_name") or os.path.basename(mat.get("path", ""))
        if mat.get("path", "").endswith(".image") or name.lower().endswith(".png"):
            continue
        t0 = s["target_timerange"]["start"] / 1e6
        dur = s["target_timerange"]["duration"] / 1e6
        # a work copy's frame 0 is not the recording's second 0
        base = offsets.get(name, 0.0) + s["source_timerange"]["start"] / 1e6
        m1, m2 = envelope(mics[1], base, dur), envelope(mics[2], base, dur)
        n = min(len(m1), len(m2))
        m1, m2 = m1[:n], m2[:n]
        tot = m1 + m2
        speech = tot > np.percentile(tot, 90) * 0.10
        r = m1 / np.maximum(m2, 1e-9)
        host += [(t0 + a, t0 + b) for a, b in runs(speech & (r > OWNS), floor=MIN_HOST)]
        loud = tot > np.percentile(tot, 90) * 0.20
        cross += [(t0 + a, t0 + b)
                  for a, b in runs(loud & (r > AMBIG[0]) & (r < AMBIG[1]), floor=MIN_CROSS)]
        sil += [(t0 + a, t0 + b) for a, b in runs(~speech, floor=MIN_SIL)]

    if "host" in want:
        print(f"\nמיקרופון 1 נושא את הקול — {len(host)} קטעים "
              f"(מצלמה 1 על המסך ב-{sum(1 for a, b in host if cam1_on((a+b)/2))}):")
        for a, b in host:
            print(f"   {a:7.2f}..{b:7.2f} ({b-a:4.2f}s)  "
                  f"{'✓ מצלמה 1' if cam1_on((a+b)/2) else '✗ מצלמה 2 על המסך'}")
    if "crosstalk" in want:
        print(f"\nאף מיקרופון לא בעלים של הקול — {len(cross)} קטעים:")
        for a, b in cross:
            print(f"   {a:7.2f}..{b:7.2f} ({b-a:4.2f}s)")
        if cross and max(b - a for a, b in cross) < 1.5:
            print("   (כולם קצרים מכדי להחזיק מסך מפוצל — פצל על חילופי דיבור במקום)")
    if "silence" in want:
        print(f"\nשקט של {MIN_SIL}ש' ומעלה — {len(sil)} קטעים:")
        for a, b in sil:
            print(f"   {a:7.2f}..{b:7.2f} ({b-a:4.2f}s)")
    if "shots" in want:
        shots, p = [], None
        for s in bots:
            a = s["target_timerange"]["start"] / 1e6
            b = a + s["target_timerange"]["duration"] / 1e6
            inner = sorted(v for v in vis if a <= v[0] < b)
            p = a
            for x, y in inner:
                if x > p:
                    shots.append(("מצלמה 2", p, x))
                shots.append(("מצלמה 1", x, y))
                p = max(p, y)
            if p < b:
                shots.append(("מצלמה 2", p, b))
        print(f"\nשוטים — {len(shots)}, הארוך {max(y-x for _,x,y in shots):.2f}s, "
              f"הקצר {min(y-x for _,x,y in shots):.2f}s")
        for who, x, y in shots:
            if y - x < 1.0 or y - x > 9.0:
                print(f"   {x:7.2f}..{y:7.2f} ({y-x:5.2f}s) {who}  "
                      f"{'רסיס' if y-x < 1.0 else 'החזקה ארוכה'}")


if __name__ == "__main__":
    main()
