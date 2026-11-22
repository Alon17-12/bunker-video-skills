"""Pick one clean candidate per slot and write the listener cutaways into the LIVE draft.
  listener_apply.py <plan.json> [--write]
Without --write: prints the picks, the longest single-camera run after them, and writes picks.json.
cam 2 listener → new segment on «ניתוב» over the cam-1 spine. cam 1 listener → the «ניתוב» segment is split and the
cam-1 spine shows through the gap. Source = timeline + the spine offset at that point (same camera clock).
"""
import copy, json, os, sys
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut

US = 1_000_000
EDGE = {1: 1.3, 2: 1.5}
plan_p = sys.argv[1]; write = '--write' in sys.argv
P = json.load(open(plan_p)); name = P['draft']
d = capcut.load_draft(name)
spine = d['tracks'][0]['segments']
rt = next(t for t in d['tracks'] if t.get('name') == 'ניתוב')
idx = {m['id']: m for l in d['materials'].values() if isinstance(l, list) for m in l if isinstance(m, dict) and m.get('id')}
fr = lambda t: int(round(t * 30)) * US // 30            # timeline seconds on the 30 fps grid → µs (CapCut floors)


def spine_off(t):
    for s in spine:
        a = s['target_timerange']['start']; b = a + s['target_timerange']['duration']
        if a <= fr(t) < b and idx[s['material_id']].get('path'):
            return s['source_timerange']['start'] - a
    return None


picks = []
for sl in P['plan']:
    ok = [c for c in sl['cands'] if c.get('edge', 99) < EDGE[sl['listener']] and c['motion'] < 1.0]
    ok.sort(key=lambda c: c['motion'] + c['dist'] * 0.06)
    for c in ok:
        if all(abs(c['t_in'] - p['t_in']) > 15 for p in picks) and spine_off(c['t_in']) is not None and spine_off(c['t_in']) == spine_off(c['t_out'] - 0.04):
            picks.append({'listener': sl['listener'], 't_in': c['t_in'], 't_out': c['t_out'], 'goal': sl['goal']}); break
    else:
        print('⚠ no clean pick for slot at', sl['goal'], 'listener', sl['listener'])
for x in filter(None, os.environ.get('EXTRA', '').split(',')):
    l, a, b = x.split(':'); picks.append({'listener': int(l), 't_in': float(a), 't_out': float(b), 'goal': None})
picks.sort(key=lambda p: p['t_in'])

# screen map after the picks (0.1 s), longest run of one camera
T = d['duration'] / US
def cam_at(t):
    for p in picks:
        if p['t_in'] <= t < p['t_out']:
            return p['listener']
    for s in rt['segments']:
        a = s['target_timerange']['start'] / US
        if a <= t < a + s['target_timerange']['duration'] / US:
            return 2
    return 1
runs = []
t = 2.5
while t < T:
    c = cam_at(t)
    if runs and runs[-1][0] == c: runs[-1][2] = t + 0.1
    else: runs.append([c, t, t + 0.1])
    t += 0.1
longest = sorted(runs, key=lambda r: r[1] - r[2])[:5]
print(len(picks), 'cutaways; longest runs now:', [(r[0], round(r[1], 1), round(r[2] - r[1], 1)) for r in longest])
json.dump(picks, open(os.path.join(os.path.dirname(plan_p), 'picks.json'), 'w'), indent=1)
if not write:
    sys.exit()

assert capcut._capcut_pid() is None, 'CapCut open'
D = capcut.DRAFTS_DIR / name
capcut._backup(D)
d = capcut.load_draft(name)                                 # re-read right before writing
rt = next(t for t in d['tracks'] if t.get('name') == 'ניתוב')
mats = d['materials']
donor = rt['segments'][0]
cam2_mat = donor['material_id']


def clone_seg(src):
    s = copy.deepcopy(src); s['id'] = capcut._new_id(); refs = []
    for r in src.get('extra_material_refs', []):
        lst = next((k for k, v in mats.items() if isinstance(v, list) and any(isinstance(x, dict) and x.get('id') == r for x in v)), None)
        if not lst or lst in ('audio_fades', 'transitions'):
            continue
        e = copy.deepcopy(next(x for x in mats[lst] if x.get('id') == r)); e['id'] = capcut._new_id()
        mats[lst].append(e); refs.append(e['id'])
    s['extra_material_refs'] = refs; s['common_keyframes'] = []
    return s


segs = rt['segments']
for p in picks:
    a, b = fr(p['t_in']), fr(p['t_out'])
    if p['listener'] == 2:
        s = clone_seg(donor); s['material_id'] = cam2_mat
        s['target_timerange'] = {'start': a, 'duration': b - a}
        s['source_timerange'] = {'start': a + spine_off(p['t_in']), 'duration': b - a}
        assert not any(x['target_timerange']['start'] < b and a < x['target_timerange']['start'] + x['target_timerange']['duration'] for x in segs)
        segs.append(s)
    else:
        host = next(x for x in segs if x['target_timerange']['start'] < a and b < x['target_timerange']['start'] + x['target_timerange']['duration'])
        h0 = host['target_timerange']['start']; h1 = h0 + host['target_timerange']['duration']; s0 = host['source_timerange']['start']
        tail = clone_seg(host)
        host['target_timerange']['duration'] = a - h0; host['source_timerange']['duration'] = a - h0
        tail['target_timerange'] = {'start': b, 'duration': h1 - b}
        tail['source_timerange'] = {'start': s0 + (b - h0), 'duration': h1 - b}
        segs.append(tail)
segs.sort(key=lambda x: x['target_timerange']['start'])
# sync check: every «ניתוב» segment keeps source − target equal to the spine offset at its start
for x in segs:
    off = spine_off(x['target_timerange']['start'] / US)
    assert off is None or abs(x['source_timerange']['start'] - x['target_timerange']['start'] - off) <= 2, x['target_timerange']
capcut._atomic_write(D, d)
print('✅ written', len(picks), 'cutaways; «ניתוב» segments:', len(segs))
