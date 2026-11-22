"""Plan listener cutaways in a «רז» draft so no camera holds > MAX s.
  listener_plan.py <draft name> <route.json> <cam1 file> <cam2 file> <out plan.json>
Reads the LIVE draft (timeline clock): spine track 0 (cam1 + Alon's compound), «ניתוב» track (cam2).
For every run of one camera longer than MAX, places k cutaways of the other camera, evenly spaced, each snapped to a
speaker pause (cut in and out at pauses of the speaking mic), the listener's mic silent throughout, and the listener's
camera calm (low frame difference). Writes candidates (with alternatives) for the visual check.
"""
import json, math, subprocess, sys, os
import numpy as np
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut

MAX, TARGET = 60.0, 48.0
DUR_MIN, DUR_MAX = 2.2, 4.5
US = 1e6
FF = os.path.expanduser('~/ffmpeg-bin/ffmpeg')

name, route, cam1, cam2, out = sys.argv[1:6]
d = capcut.load_draft(name)
r = json.load(open(route))
e = {1: np.array(r['env']['e1']), 2: np.array(r['env']['e2'])}
m2c = r['mic_to_cam']                                   # cam_t = mic_t + m2c

idx = {m['id']: m for l in d['materials'].values() if isinstance(l, list) for m in l if isinstance(m, dict) and m.get('id')}
spine = d['tracks'][0]['segments']; rout = next(t for t in d['tracks'] if t.get('name') == 'ניתוב')['segments']
T = d['duration'] / US


def seg_map(t):
    """timeline t -> (cam on screen, cam-clock time) ; None inside a compound"""
    for s in rout:
        a = s['target_timerange']['start'] / US; b = a + s['target_timerange']['duration'] / US
        if a <= t < b:
            return 2, t - a + s['source_timerange']['start'] / US
    for s in spine:
        a = s['target_timerange']['start'] / US; b = a + s['target_timerange']['duration'] / US
        if a <= t < b:
            if not idx[s['material_id']].get('path'):
                return None
            return 1, t - a + s['source_timerange']['start'] / US
    return None


def lvl(mic, cam_t):
    i = int(round((cam_t - m2c) * 10))
    return e[mic][max(0, min(i, len(e[mic]) - 1))]


# runs of the camera on screen, on the timeline (0.1 s grid)
grid = np.arange(0, T, 0.1)
cams = [seg_map(t) for t in grid]
runs = []
for t, c in zip(grid, cams):
    k = c[0] if c else 0
    if runs and runs[-1][0] == k:
        runs[-1][2] = t + 0.1
    else:
        runs.append([k, t, t + 0.1])
long_runs = [x for x in runs if x[0] and x[2] - x[1] > MAX]
print('runs > 60 s:', [(x[0], round(x[1], 1), round(x[2] - x[1], 1)) for x in long_runs])


def motion(cam_file, cam_t0, dur):
    """mean abs frame difference of the listener camera in the window (small, gray, 5 fps)"""
    raw = subprocess.run([FF, '-v', 'error', '-ss', f'{cam_t0:.3f}', '-t', f'{dur:.3f}', '-i', cam_file,
                          '-vf', 'fps=5,scale=96:54,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 54, 96).astype(np.float32)
    return float(np.abs(np.diff(f, axis=0)).mean()) if len(f) > 1 else 99.0


def pauses(spk, t0, t1):
    """pause midpoints (timeline) of the speaking mic: >= 0.25 s below its speech level"""
    out, cur = [], None
    for t in np.arange(t0, t1, 0.1):
        c = seg_map(t)
        if not c: continue
        quiet = lvl(spk, c[1]) < -46 and lvl(1 if spk == 2 else 2, c[1]) < -46
        if quiet:
            cur = cur or [t, t]; cur[1] = t + 0.1
        elif cur:
            if cur[1] - cur[0] >= 0.2: out.append(cur)
            cur = None
    return out


plan = []
for k, a, b in long_runs:
    listener = 2 if k == 1 else 1
    L = b - a
    n = max(1, math.ceil(L / TARGET) - 1)
    ps = pauses(k, a + 3, b - 3)
    for j in range(1, n + 1):
        goal = a + L * j / (n + 1)
        cands = []
        for p in ps:
            t_in = round(((p[0] + p[1]) / 2) * 30) / 30
            if abs(t_in - goal) > float(os.environ.get("TOL", 15)): continue
            # out at a later pause DUR_MIN..DUR_MAX after
            outs = [q for q in ps if DUR_MIN <= (q[0] + q[1]) / 2 - t_in <= DUR_MAX]
            for q in outs:
                t_out = round(((q[0] + q[1]) / 2) * 30) / 30
                c0 = seg_map(t_in); c1 = seg_map(t_out - 0.05)
                if not c0 or not c1 or c0[0] != k or c1[0] != k: continue
                # the listener must stay silent
                lis = max(lvl(listener, c0[1] + x) - max(lvl(k, c0[1] + x), -50) for x in np.arange(0, t_out - t_in, 0.1))
                if lis > -8: continue
                cands.append({'t_in': t_in, 't_out': t_out, 'cam_t': round(c0[1], 3), 'dist': abs(t_in - goal), 'lis': round(float(lis), 1)})
        cands.sort(key=lambda x: x['dist'])
        best = []
        for c in cands[:int(os.environ.get("NC", 10))]:
            c['motion'] = round(motion(cam1 if listener == 1 else cam2, c['cam_t'], c['t_out'] - c['t_in']), 2)
            best.append(c)
        best.sort(key=lambda x: x['motion'] + x['dist'] * 0.08)
        plan.append({'run': [k, round(a, 2), round(b, 2)], 'listener': listener, 'goal': round(goal, 2), 'cands': best[:int(os.environ.get("KEEP", 4))]})
        print(f'run cam{k} {a:7.1f}-{b:7.1f}  goal {goal:7.1f}  ->', [(c["t_in"], round(c["t_out"] - c["t_in"], 2), c["motion"]) for c in best[:3]], flush=True)
json.dump({'draft': name, 'runs': long_runs, 'plan': plan}, open(out, 'w'), ensure_ascii=False, indent=1)
