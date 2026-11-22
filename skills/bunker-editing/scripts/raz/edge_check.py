"""Edge intrusion + head stability for listener candidates.
  edge_check.py <plan.json> <cam1> <cam2>
For each candidate: max change of the outer 12 % strips (a hand / head of the other speaker entering) relative to the
window's first frame, and overall motion. Adds 'edge' to each candidate and rewrites the plan.
"""
import json, os, subprocess, sys
import numpy as np
FF = os.path.expanduser('~/ffmpeg-bin/ffmpeg')
plan_p, cam1, cam2 = sys.argv[1:4]
P = json.load(open(plan_p))


def frames(cam, t0, dur):
    raw = subprocess.run([FF, '-v', 'error', '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', cam, '-vf',
                          'fps=10,scale=160:90,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.float32)


for sl in P['plan']:
    cam = cam1 if sl['listener'] == 1 else cam2
    for c in sl['cands']:
        f = frames(cam, c['cam_t'] - 0.3, c['t_out'] - c['t_in'] + 0.6)
        ref = np.median(f, axis=0)
        l = np.abs(f[:, :, :19] - ref[:, :19]).mean(axis=(1, 2)).max()
        r = np.abs(f[:, :, -19:] - ref[:, -19:]).mean(axis=(1, 2)).max()
        c['edge'] = round(float(max(l, r)), 2)
json.dump(P, open(plan_p, 'w'), ensure_ascii=False, indent=1)
for i, sl in enumerate(P['plan']):
    print(i, sl['listener'], [(round(c['t_in'], 1), c['motion'], c['edge']) for c in sl['cands']])
