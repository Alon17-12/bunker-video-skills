#!/usr/bin/env python3
"""Ripple edits on a CapCut draft dict (µs), every track at once, so picture, routing, sound, colour and plates stay in sync.
  ripple_cut(d, a, b)   — remove timeline [a, b): segments inside go, segments across it are trimmed or split (media pieces keep
                          their source clock: the second piece starts b−S later in its source), everything after moves left.
  Segments without a media source (adjust / solid / compound) that span the cut just get shorter.
  Audio fades: a split audio piece gets no fade at the cut (the cut is in silence) — the fade in stays on the first piece, the
  fade out on the second.
  zoom_jumps(d, cuts)   — a cut that keeps the same camera on screen is a jump cut: the shot after it punches in (×1.08) or back
                          out, alternating per camera run, so the jump reads as a deliberate re-frame.
  add_markers(d, items) — CapCut timeline markers [{t, title, color}] (Alon reviews / corrects at those spots)."""
import copy, json, os, sys
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut

ts = lambda s: s['target_timerange']['start']
te = lambda s: ts(s) + s['target_timerange']['duration']


def mats_index(d):
    return {m['id']: (k, m) for k, v in d['materials'].items() if isinstance(v, list) for m in v if isinstance(m, dict) and 'id' in m}


def is_media(d, s, idx):
    k, m = idx.get(s['material_id'], (None, {}))
    return bool(s.get('source_timerange')) and k in ('videos', 'audios') and bool(m.get('path')) and m.get('type') != 'photo'


def clone_seg(d, seg, idx):
    s = copy.deepcopy(seg); s['id'] = capcut._new_id(); refs = []
    for r in seg.get('extra_material_refs', []):
        if r not in idx:
            continue
        k, m = idx[r]
        e = copy.deepcopy(m); e['id'] = capcut._new_id(); d['materials'][k].append(e); refs.append(e['id']); idx[e['id']] = (k, e)
    s['extra_material_refs'] = refs
    return s


def _fade(d, seg, idx):
    for r in seg.get('extra_material_refs', []):
        if idx.get(r, (None,))[0] == 'audio_fades':
            return idx[r][1]
    return None


def ripple_cut(d, a, b):
    L = b - a; idx = mats_index(d)
    for t in d['tracks']:
        out = []
        for s in t['segments']:
            S, E = ts(s), te(s)
            if E <= a:
                out.append(s)
            elif S >= b:
                s['target_timerange']['start'] -= L; out.append(s)
            elif S >= a and E <= b:
                continue                                            # wholly inside the cut
            elif S < a and E > b:
                if not is_media(d, s, idx):
                    s['target_timerange']['duration'] -= L
                    if s.get('source_timerange') and s['source_timerange'].get('duration'):
                        s['source_timerange']['duration'] = max(1, s['source_timerange']['duration'] - L)
                    out.append(s); continue
                s2 = clone_seg(d, s, idx)
                s['target_timerange']['duration'] = a - S; s['source_timerange']['duration'] = a - S
                s2['target_timerange'] = {'start': a, 'duration': E - b}
                s2['source_timerange'] = {'start': s['source_timerange']['start'] + (b - S), 'duration': E - b}
                f1, f2 = _fade(d, s, idx), _fade(d, s2, idx)
                if f1 and f2:
                    f2['fade_in_duration'] = 15_000; f2['fade_out_duration'] = f1['fade_out_duration']; f1['fade_out_duration'] = 15_000   # no click at the join
                out += [s, s2]
            elif S < a < E <= b:
                f = _fade(d, s, idx)
                if f and E < b - 1000:
                    f['fade_out_duration'] = 15_000
                s['target_timerange']['duration'] = a - S
                if s.get('source_timerange'):
                    s['source_timerange']['duration'] = a - S
                f = _fade(d, s, idx)
                if f and is_media(d, s, idx) and E < b + 1:
                    pass
                out.append(s)
            else:                                                   # a <= S < b < E
                f = _fade(d, s, idx)
                if f and S > a + 1000:
                    f['fade_in_duration'] = 15_000
                c = b - S
                if s.get('source_timerange'):
                    s['source_timerange']['start'] += c; s['source_timerange']['duration'] -= c
                s['target_timerange'] = {'start': a, 'duration': E - b}
                out.append(s)
        t['segments'] = sorted(out, key=ts)
    d['duration'] -= L


def visible(d, t, idx):
    """the camera segment on screen at t: the routing track over the main track"""
    for name in ('ניתוב', None):
        tr = next((x for x in d['tracks'] if x.get('name') == name), None) if name else d['tracks'][0]
        for s in tr['segments']:
            if ts(s) <= t < te(s):
                k, m = idx.get(s['material_id'], (None, {}))
                if m.get('path') or 'Compound' in m.get('material_name', ''):
                    return s, m.get('material_name', '')
    return None, ''


def zoom_jumps(d, cut_points, scale=1.08):
    """cut_points: timeline µs where a cut joined two pieces (after all ripples)"""
    idx = mats_index(d); n = 0
    for p in sorted(cut_points):
        before, cb = visible(d, p - 20_000, idx)
        after, ca = visible(d, p + 20_000, idx)
        if not before or not after or cb != ca or before is after:
            continue
        # the next speaker's camera comes < 0.8 s after the cut: move that switch onto the cut (the cut hides under it)
        rt = next((x for x in d['tracks'] if x.get('name') == 'ניתוב'), None)
        if rt and after in rt['segments'] and te(after) - p < 800_000:
            nxt = next((x for x in rt['segments'] if abs(ts(x) - te(after)) < 1000), None)
            if nxt is not None and idx.get(nxt['material_id'], (None, {}))[1].get('material_name', '') != ca:
                g = te(after) - p
                nxt['target_timerange']['start'] -= g; nxt['target_timerange']['duration'] += g
                nxt['source_timerange']['start'] -= g; nxt['source_timerange']['duration'] += g
                rt['segments'].remove(after) if ts(after) >= p - 1000 else after['target_timerange'].update(duration=p - ts(after))
                n += 1
                continue
        if te(after) - p < 1_500_000:
            continue                                                # too short to punch in — leave the jump
        zb = (before.get('clip') or {}).get('scale', {}).get('x', 1.0)
        z = 1.0 if zb > 1.001 else scale
        clip = copy.deepcopy(after.get('clip') or {'rotation': 0.0, 'transform': {'x': 0.0, 'y': 0.0}, 'flip': {'vertical': False, 'horizontal': False}, 'alpha': 1.0})
        clip['scale'] = {'x': z, 'y': z}
        # punch in toward the face (upper part of the frame), not the centre
        clip['transform'] = {'x': (clip.get('transform') or {}).get('x', 0.0), 'y': -0.04 if z > 1.001 else 0.0}
        after['clip'] = clip; n += 1
    return n


def add_markers(d, items):
    tm = d.get('time_marks') or {'id': capcut._new_id(), 'mark_items': []}
    tm.setdefault('mark_items', [])
    for it in items:
        tm['mark_items'].append({'id': capcut._new_id(), 'time_range': {'start': int(it['t']), 'duration': int(it.get('dur', 0))},
                                 'color': it.get('color', '#00c1cd'), 'title': it['title'][:60]})
    tm['mark_items'].sort(key=lambda m: m['time_range']['start'])
    d['time_marks'] = tm
    return len(items)


def fix_short_shots(d, min_us=1_000_000):
    """a visible shot < 1 s left between cuts takes the camera (and framing) of the shot before it — no flash"""
    idx = mats_index(d); n = 0
    rt = next((x for x in d['tracks'] if x.get('name') == 'ניתוב'), None)
    layers = ([rt['segments']] if rt else []) + [d['tracks'][0]['segments']]
    def vis(t):
        for segs in layers:
            for s in segs:
                if ts(s) <= t < te(s):
                    return s
    edges = sorted({ts(s) for segs in layers for s in segs} | {te(s) for segs in layers for s in segs})
    runs = []
    for a, b in zip(edges, edges[1:]):
        s = vis((a + b) // 2)
        if s is None:
            continue
        nm = idx.get(s['material_id'], (None, {}))[1].get('material_name', '')
        if runs and runs[-1][2] == nm and runs[-1][1] == a:
            runs[-1][1] = b; runs[-1][3].append(s)
        else:
            runs.append([a, b, nm, [s]])
    for i in range(1, len(runs) - 1):
        a, b, nm, segs = runs[i]
        if b - a >= min_us or 'מצלמה' not in nm or 'מצלמה' not in runs[i - 1][2]:
            continue
        prev = runs[i - 1][3][-1]
        for s in segs:
            if s.get('source_timerange') and idx.get(prev['material_id'], (None, {}))[1].get('path'):
                s['material_id'] = prev['material_id']; s['clip'] = copy.deepcopy(prev.get('clip')); n += 1
        runs[i][2] = runs[i - 1][2]
    return n
