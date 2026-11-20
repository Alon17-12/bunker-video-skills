#!/usr/bin/env python3
"""Pre-handoff gate for a long-form CapCut draft (course / interview / VSL). Read-only: never writes the draft.
Every check here is a failure Alon once caught by hand (לקוח E v2–v11, הסימולטור r1–r9, 11.2026).

  python longform_gate.py "<draft name>" [--ref "<previous version draft name>"] [--sep 5.0] [--allow-drive /Volumes/X]
  --allow-drive: only when the Mac has no room for the media (course footage) AND CapCut already opened a project from
  that drive. Media there passes with a WARN: the project must never be opened without the drive connected.

FAIL (exit 1):
  media      every video/audio file exists AND sits inside the draft folder (CapCut's sandbox can't read the SSD:
             «File not accessible»; opened without access it also zeroes clip source starts)
  ids        no material id / segment id used twice (merged episodes from one template → «Unsupported Media»)
  sync       each camera file has ONE offset against the dialogue file under it (± 1 frame); with --ref, the same offset
             as the previous version
  gaps       main video track has no hole > 1 frame, except separators ≥ --sep seconds (between episodes)
  lut        every second of camera picture is under an adjust (LUT) layer
  captions   no two cards of one text track overlap; no card < 0.25 s; no empty card («למחיקה» / «לוודא» tracks excluded)
  slivers    no routing/main segment shorter than 2 frames
  markers    every marker inside the timeline
WARN: «למחיקה» / «לוודא» track still present (switch off before export); clips with speed ≠ 1 (sync check skips them)."""
import json, os, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut

US, FR = 1_000_000, 1_000_000 // 30
D = capcut.DRAFTS_DIR
ts = lambda s: s['target_timerange']['start']
te = lambda s: s['target_timerange']['start'] + s['target_timerange']['duration']
hms = lambda us: f"{int(us // US // 3600)}:{int(us / US % 3600 // 60):02d}:{us / US % 60:05.2f}"


def load(name):
    raw = (D / name / 'draft_info.json').read_text()
    return json.loads(re.sub(r'##_draftpath_placeholder_[0-9A-F-]+_##', str(D / name), raw))


def index(d):
    out = {}
    for k, v in d['materials'].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and 'id' in m:
                    out[m['id']] = (k, m)
    return out


def tracks(d, typ, name=None):
    return [t for t in d['tracks'] if t['type'] == typ and (name is None or t.get('name', '') == name)]


def media_path(idx, s):
    m = idx.get(s.get('material_id'), (None, {}))[1]
    p = m.get('path') or ''
    return p if p and m.get('type') in ('video', 'photo', 'extract_music', 'music', 'sound', None) or (p and os.path.splitext(p)[1]) else ''


def offsets(d):
    """{(camera file, dialogue file): set of offsets µs} — camera src − dialogue src at the same timeline instant."""
    idx = index(d)
    dia = sorted((s for t in tracks(d, 'audio', '')[:1] for s in t['segments']), key=ts)
    out, skipped = defaultdict(set), 0
    vids = [s for t in tracks(d, 'video') if t.get('name', '') in ('', 'ניתוב') for s in t['segments']]
    starts = defaultdict(set)                             # a graphic reused from the same source point (subscribe
    for v in vids:                                        # banner every 10 min) is an overlay, not a camera
        starts[v['material_id']].add(v['source_timerange']['start'])
    reused = {mid for mid, st in starts.items() if len(st) == 1 and sum(v['material_id'] == mid for v in vids) > 1}
    for v in vids:
        if v['material_id'] in reused:
            continue
        p = media_path(idx, v)
        if not p or idx[v['material_id']][1].get('type') == 'photo':
            continue
        if abs(v.get('speed', 1.0) - 1.0) > 1e-6:
            skipped += 1; continue
        for a in dia:                                     # every dialogue piece this shot overlaps
            x, y = max(ts(v), ts(a)), min(te(v), te(a))
            if y - x < FR or abs(a.get('speed', 1.0) - 1.0) > 1e-6:
                continue
            off = (v['source_timerange']['start'] - ts(v)) - (a['source_timerange']['start'] - ts(a))
            out[(Path(p).name, Path(idx[a['material_id']][1]['path']).name)].add(off)
    return out, skipped


def spread(vals):
    """cluster offsets 1 frame apart → list of clusters (a cut edit keeps one cluster per pair)"""
    cl = []
    for v in sorted(vals):
        if cl and v - cl[-1][-1] <= FR:
            cl[-1].append(v)
        else:
            cl.append([v])
    return cl


def main():
    name = sys.argv[1]
    ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else None
    sep = float(sys.argv[sys.argv.index('--sep') + 1]) * US if '--sep' in sys.argv else 5.0 * US
    d = load(name); idx = index(d); folder = str(D / name)
    fails, warns = defaultdict(list), []
    drive = sys.argv[sys.argv.index('--allow-drive') + 1].rstrip('/') + '/' if '--allow-drive' in sys.argv else None
    on_drive = 0

    # media
    for k in ('videos', 'audios'):
        for m in d['materials'].get(k, []):
            p = m.get('path') or ''
            if not p or m.get('type') == 'text':
                continue
            if not os.path.exists(p):
                fails['media'].append(f'missing: {p}')
            elif '/CapCut/User Data/Cache/' in p:
                continue                                  # CapCut's own downloaded stickers/effects: always readable
            elif drive and p.startswith(drive):
                on_drive += 1
            elif not os.path.realpath(p).startswith(os.path.realpath(folder)):
                fails['media'].append(f'outside the draft folder: {p}')
    if on_drive:
        warns.append(f'{on_drive} media files on {drive} — open the project ONLY with that drive connected '
                     '(opened without it, CapCut zeroes clip source starts)')
    # ids — one id must mean one file (merged episodes from one template once shared ids → «Unsupported Media»)
    paths = defaultdict(set)
    for k in ('videos', 'audios'):
        for m in d['materials'].get(k, []):
            paths[m['id']].add(m.get('path') or '')
    fails['ids'] += [f'material {i} → {len(v)} files' for i, v in paths.items() if len(v) > 1][:10]
    segs = defaultdict(int)
    for t in d['tracks']:
        for s in t['segments']:
            segs[s['id']] += 1
    fails['ids'] += [f'segment {i} ×{n}' for i, n in segs.items() if n > 1][:10]
    # sync
    offs, skipped = offsets(d)
    for pair, vals in sorted(offs.items()):
        cl = spread(vals)
        if len(cl) > 1:
            fails['sync'].append(f'{pair[0]} vs {pair[1]}: {len(cl)} different offsets ' +
                                 ', '.join(f'{c[0] / US:+.3f}s' for c in cl[:4]))
    if skipped:
        warns.append(f'{skipped} clips with speed ≠ 1 not sync-checked')
    if ref:
        roffs, _ = offsets(load(ref))
        for pair, vals in offs.items():
            if pair in roffs:
                a, b = spread(vals)[0][0], spread(roffs[pair])[0][0]
                if abs(a - b) > FR:
                    fails['sync'].append(f'{pair[0]} vs {pair[1]}: {b / US:+.3f}s in ref → {a / US:+.3f}s now')
    # gaps + slivers on main / routing
    main = sorted(tracks(d, 'video', '')[0]['segments'], key=ts) if tracks(d, 'video', '') else []
    for a, b in zip(main, main[1:]):
        g = ts(b) - te(a)
        if FR < g < sep:
            fails['gaps'].append(f'{hms(te(a))} hole {g / US:.2f}s')
    if main and ts(main[0]) > FR:
        fails['gaps'].append(f'timeline starts with {ts(main[0]) / US:.2f}s of nothing')
    for t in tracks(d, 'video'):
        if t.get('name', '') in ('', 'ניתוב'):
            for s in t['segments']:
                if s['target_timerange']['duration'] < 2 * FR:
                    fails['slivers'].append(f"{t.get('name') or 'main'} {hms(ts(s))} {s['target_timerange']['duration'] / US:.3f}s")
    # lut coverage of camera picture
    adj = sorted((ts(s), te(s)) for t in tracks(d, 'adjust') for s in t['segments'])
    if not adj:
        warns.append('no adjust (LUT) layer — colour must then be per clip; check it in stills')
    for s in (main if adj else []):
        if not media_path(idx, s) or idx[s['material_id']][1].get('type') == 'photo':
            continue
        cur, bare = ts(s), 0
        for a, b in adj:
            if b <= cur or a >= te(s):
                continue
            bare += max(0, a - cur); cur = max(cur, b)
        bare += max(0, te(s) - cur)
        if bare > FR:
            fails['lut'].append(f'{hms(ts(s))} {bare / US:.2f}s of picture without LUT')
    # captions
    texts = {m['id']: m for m in d['materials'].get('texts', [])}
    for t in tracks(d, 'text'):
        if t.get('name') in ('למחיקה', 'לוודא'):
            warns.append(f"«{t.get('name')}» track still has {len(t['segments'])} blocks — delete it before export")
            continue
        segs = sorted(t['segments'], key=ts)
        for a, b in zip(segs, segs[1:]):
            if te(a) - ts(b) > 1000:
                fails['captions'].append(f"{t.get('name')} overlap at {hms(ts(b))}")
        for s in segs:
            if s['target_timerange']['duration'] < 250_000:
                fails['captions'].append(f"{t.get('name')} {hms(ts(s))} card {s['target_timerange']['duration'] / US:.2f}s")
            m = texts.get(s['material_id'])
            if m:
                try:
                    txt = json.loads(m['content']).get('text', '')
                except Exception:
                    txt = m.get('content', '')
                if not txt.strip():
                    fails['captions'].append(f"{t.get('name')} {hms(ts(s))} empty card")
    # markers
    for mk in (d.get('time_marks') or {}).get('mark_items', []):
        if mk['time_range']['start'] > d['duration']:
            fails['markers'].append(f"«{mk.get('title', '')[:40]}» after the end")
    # report
    if subprocess.run(['pgrep', '-x', 'CapCut'], capture_output=True).returncode == 0:
        warns.append('CapCut is open — fine for this read-only check, but do not write the draft now')
    nmk = len((d.get('time_marks') or {}).get('mark_items', []))
    print(f'{name}\n  length {hms(d["duration"])} · {len(main)} main shots · {nmk} markers · {len(offs)} camera↔dialogue pairs')
    for k in ('media', 'ids', 'sync', 'gaps', 'lut', 'captions', 'slivers', 'markers'):
        v = fails.get(k, [])
        print(f"  {'FAIL' if v else 'ok  '} {k}" + (f' ({len(v)})' if v else ''))
        for line in v[:8]:
            print('       ', line)
    for w in warns:
        print('  WARN', w)
    sys.exit(1 if any(fails.values()) else 0)


if __name__ == '__main__':
    main()
