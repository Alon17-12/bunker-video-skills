#!/usr/bin/env python3
"""CapCut markers do not move when Alon ripple-deletes earlier on the timeline (19.11.2026, v8: one 6.1 s cut left every later
marker 6.1 s late). Re-anchor them by CONTENT: a marker sat at a moment of a recording in the reference version (where the
markers were right); find where that moment of that recording plays now. If the moment was deleted, the marker goes to the
cut and its title says so.
    remap_markers.py "<reference project>" "<edited project>" "<new project name>" [--write]
The edited project itself is never written: the result is a copy under the new name."""
import json, os, re, shutil, sys, time
from pathlib import Path
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
sys.path.insert(0, str(Path(__file__).parent))
import capcut, reels
import edit_engine as E

US = 1_000_000
D = capcut.DRAFTS_DIR
ts, te = E.ts, E.te


def load(name):
    return json.loads(re.sub(r'##_draftpath_placeholder_[0-9A-F-]+_##', str(D / name), (D / name / 'draft_info.json').read_text()))


def dialogue(d):
    idx = E.mats_index(d)
    t = next(x for x in d['tracks'] if x['type'] == 'audio' and x.get('name', '') == '')
    return [(ts(s), te(s), Path(idx[s['material_id']][1]['path']).name, s['source_timerange']['start']) for s in sorted(t['segments'], key=ts)]


def main():
    ref, cur, out = sys.argv[1:4]
    a, b = load(ref), load(cur)
    A, B = dialogue(a), dialogue(b)
    # a file copied into another draft folder keeps its name: match by file name + source time
    marks = (b.get('time_marks') or {}).get('mark_items', [])
    ref_marks = {m['id']: m for m in (a.get('time_marks') or {}).get('mark_items', [])}
    moved, cut_hit, kept = 0, 0, 0
    for m in marks:
        r = ref_marks.get(m['id'])
        t = (r or m)['time_range']['start']
        seg = next((x for x in A if x[0] <= t < x[1]), None)
        if seg is None:
            kept += 1; continue                                # outside any dialogue (a separator): leave it
        f, src = seg[2], seg[3] + (t - seg[0])
        hit = next((x for x in B if x[2] == f and x[3] <= src < x[3] + (x[1] - x[0])), None)
        if hit:
            new = hit[0] + (src - hit[3])
        else:                                                  # that moment was deleted: the cut that removed it
            after = [x for x in B if x[2] == f and x[3] > src]
            new = min(after, key=lambda x: x[3])[0] if after else m['time_range']['start']
            if '(הקטע נמחק)' not in m['title']:
                m['title'] = (m['title'][:46] + ' (הקטע נמחק)'); cut_hit += 1
        if abs(new - m['time_range']['start']) > 1000:
            moved += 1
        m['time_range']['start'] = int(new)
    print(json.dumps({'markers': len(marks), 'moved': moved, 'on_deleted_content': cut_hit, 'outside_dialogue': kept}, ensure_ascii=False))
    if '--write' not in sys.argv:
        return
    if capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח')
    dst = D / reels._unique_name(out)
    def cp(x, y, *k, **kw):
        if os.path.getsize(x) > 50_000_000:
            os.link(x, y); return y
        return shutil.copy2(x, y)
    shutil.copytree(D / cur, dst, copy_function=cp, ignore=lambda dd, n: [x for x in n if x.startswith('draft_info.ccstudio-backup') or x.endswith(('.tmp', '.bak'))])
    b = json.loads(json.dumps(b, ensure_ascii=False).replace(str(D / cur) + '/', str(dst) + '/'))
    for f in (dst / 'subdraft').glob('*/draft_content.json'):
        f.write_text(f.read_text().replace(str(D / cur) + '/', str(dst) + '/'))
    capcut._atomic_write(dst, b)
    mp = dst / 'draft_meta_info.json'; meta = json.loads(mp.read_text()); now = int(time.time() * US)
    meta.update({'draft_id': capcut._new_id(), 'draft_name': dst.name, 'draft_fold_path': str(dst), 'tm_draft_create': now,
                 'tm_draft_modified': now, 'tm_duration': b['duration']})
    mp.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta['draft_id'], b['duration'], cur)
    print('✅', dst.name)


if __name__ == '__main__':
    main()
