#!/usr/bin/env python3
"""v10 = Alon's latest (v9) with every mid/senior marker re-anchored from its ORIGIN: markers.json / edit_proposals_senior.json
hold each marker's time on the v3 clock → dialogue-file source time → where that source moment plays now. (20.11: the v7
markers were already ~15.7 s late, so remapping from v7 carried the error; anchor to the origin, never to an earlier version.)
Then v9 goes to the Trash so one client E project remains.   fix_markers_v10.py [--write]"""
import json, os, re, shutil, sys, time
from pathlib import Path
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app')); sys.path.insert(0, str(Path(__file__).parent))
import capcut, reels
import edit_engine as E
HERE = Path(__file__).parent; D = capcut.DRAFTS_DIR; US = 1_000_000
CUR = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v9'; OUT = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v10'
EP3 = {'מיד': 1501.383, 'סיניור': 2535.75}
d = json.loads(re.sub(r'##_draftpath_placeholder_[0-9A-F-]+_##', str(D / CUR), (D / CUR / 'draft_info.json').read_text()))
idx = E.mats_index(d)
aud = sorted(next(t for t in d['tracks'] if t['type'] == 'audio' and t.get('name', '') == '')['segments'], key=E.ts)
files = []
for s in aud:
    f = idx[s['material_id']][1]['path']
    if f not in files: files.append(f)
ep_file = dict(zip(['VSL', "ג'וניור", 'מיד', 'סיניור'], files))
def to_tl(t3):
    ep = 'סיניור' if t3 >= EP3['סיניור'] else 'מיד'
    src = int(round((t3 - EP3[ep]) * US))
    for s in aud:
        if idx[s['material_id']][1]['path'] != ep_file[ep]: continue
        a = s['source_timerange']['start']
        if a <= src < a + s['source_timerange']['duration']: return E.ts(s) + src - a
    return None
MJ = json.loads((HERE / 'markers.json').read_text())
moved = []
for m in d['time_marks']['mark_items']:
    o = next((x for x in MJ if x['title'][:30] == m['title'][:30]), None)
    if not o or o['t3'] < EP3['מיד']: continue
    new = to_tl(o['t3'])
    if new is None:
        m['title'] = m['title'][:46] + ' (הקטע נמחק)'; continue
    moved.append((round(m['time_range']['start'] / US, 2), round(new / US, 2))); m['time_range']['start'] = int(new)
print('moved', len(moved), moved[:3])
if '--write' not in sys.argv: sys.exit()
if capcut._capcut_pid() is not None: sys.exit('⛔ CapCut פתוח')
dst = D / reels._unique_name(OUT)
def cp(x, y, *k, **kw):
    if os.path.getsize(x) > 50_000_000: os.link(x, y); return y
    return shutil.copy2(x, y)
shutil.copytree(D / CUR, dst, copy_function=cp, ignore=lambda dd, n: [x for x in n if x.startswith('draft_info.ccstudio-backup') or x.endswith(('.tmp', '.bak'))])
d = json.loads(json.dumps(d, ensure_ascii=False).replace(str(D / CUR) + '/', str(dst) + '/'))
for f in (dst / 'subdraft').glob('*/draft_content.json'):
    f.write_text(f.read_text().replace(str(D / CUR) + '/', str(dst) + '/'))
capcut._atomic_write(dst, d)
mp = dst / 'draft_meta_info.json'; meta = json.loads(mp.read_text()); now = int(time.time() * US)
meta.update({'draft_id': capcut._new_id(), 'draft_name': dst.name, 'draft_fold_path': str(dst), 'tm_draft_create': now, 'tm_draft_modified': now, 'tm_duration': d['duration']})
mp.write_text(json.dumps(meta, ensure_ascii=False))
reels._registry_add(dst, meta['draft_id'], d['duration'], CUR)
# one client E project: v9 → Trash, out of the registry
reg = D / 'root_meta_info.json'; shutil.copy2(reg, str(reg) + '.before-v9-trash')
r = json.loads(reg.read_text()); r['all_draft_store'] = [x for x in r['all_draft_store'] if os.path.basename(x.get('draft_fold_path', '')) != CUR]
tmp = str(reg) + '.tmp'; Path(tmp).write_text(json.dumps(r, ensure_ascii=False)); os.replace(tmp, reg)
shutil.move(str(D / CUR), os.path.expanduser('~/.Trash/' + CUR + ' ' + time.strftime('%H%M%S')))
print('✅', dst.name, '· left:', sorted(n for n in os.listdir(D) if '18.11.26' in n))
