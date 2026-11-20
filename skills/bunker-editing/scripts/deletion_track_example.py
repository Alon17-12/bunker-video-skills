#!/usr/bin/env python3
"""v8 = Alon's current v7 + the proposed deletions shown as a text track «למחיקה» instead of range markers (Alon 19.11: «אני לא
מצליח להבין מהמרקרים… תחליף בשיטה של סימון srt לטווח המחיקה המומלץ, מנקודת ההתחלה לנקודת הסיום»).
Each block starts and ends exactly on the span to delete — found from the CONTENT (the span's sound on its source clock), not
from old times, so his own edits since v7 are respected (a span he already removed is skipped, a shortened one is clipped).
On screen: a red bar at the top while the span plays: «למחיקה · ID · kind» / what is said in it. The 46 range markers go.
Turn the track off (eye icon) or delete it before export.   build_v8.py [--write]"""
import copy, json, os, re, shutil, sys, time
from pathlib import Path
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
sys.path.insert(0, str(Path(__file__).parent))
import capcut, reels
import edit_engine as E

US = 1_000_000
HERE = Path(__file__).parent; D = capcut.DRAFTS_DIR
V7 = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v7'
V8 = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v8'
WRITE = '--write' in sys.argv
FONT = '~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/Rubik-Bold.ttf'
EP3 = {'מיד': 1501.383, 'סיניור': 2535.75}
K = {'silence': 'שקט', 'retake': 'טייק חוזר', 'false_start': 'פתיחה שגויה', 'direction': 'מחוץ לאוויר', 'stutter': 'גמגום', 'filler': 'אה/אממ'}
ts, te = E.ts, E.te


def fr(x):
    return int(round(x * 30)) * US // 30


def style():
    cfg = json.loads((Path.home() / 'bunker-video-engine/config.json').read_text())
    st = copy.deepcopy(next(x for x in cfg['styles'] if x['id'] == '5d70ccc7')['style'])            # white text on a box
    m = st['material_template']
    m.update({'font_path': FONT, 'font_name': 'Rubik', 'font_title': 'Rubik Bold', 'font_id': '', 'font_resource_id': '', 'fonts': [],
              'background_color': '#D0102E', 'background_alpha': 0.92, 'line_max_width': 0.9, 'alignment': 1, 'font_size': 6.0})
    for f in ('content', 'base_content'):
        if m.get(f):
            p = json.loads(m[f])
            for s in p.get('styles', []):
                s['font'] = {'path': FONT, 'id': ''}; s['size'] = 6.0
                s['fill'] = {'content': {'solid': {'color': [1, 1, 1]}, 'render_type': 'solid'}}
            m[f] = json.dumps(p, ensure_ascii=False)
    st['segment_template']['clip'] = {'scale': {'x': 1.0, 'y': 1.0}, 'rotation': 0.0, 'transform': {'x': 0.0, 'y': 0.84},
                                      'flip': {'vertical': False, 'horizontal': False}, 'alpha': 1.0}
    return st


def main():
    if WRITE and capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח — סגור אותו לגמרי (Cmd+Q) ותריץ שוב.')
    txt = (D / V7 / 'draft_info.json').read_text()
    d = json.loads(re.sub(r'##_draftpath_placeholder_[0-9A-F-]+_##', str(D / V7), txt))
    idx = E.mats_index(d)
    aud = sorted(next(t for t in d['tracks'] if t['type'] == 'audio' and t.get('name', '') == '')['segments'], key=ts)
    files = []
    for s in aud:
        f = idx[s['material_id']][1]['path']
        if f not in files:
            files.append(f)
    ep_file = dict(zip(['VSL', "ג'וניור", 'מיד', 'סיניור'], files))
    rs = json.loads((HERE / 'v7_restored.json').read_text())
    edits = {c['id']: c for c in json.loads((HERE / 'edits.json').read_text())['cuts']}
    blocks, gone = [], []
    for r in rs:
        c = edits[r['id']]; ep = r['ep']
        cs, ce = fr(c['start_s']) - fr(EP3[ep]), fr(c['end_s']) - fr(EP3[ep])            # the span on the dialogue file's clock
        hit = []
        for s in aud:
            if idx[s['material_id']][1]['path'] != ep_file[ep]:
                continue
            a, b = s['source_timerange']['start'], s['source_timerange']['start'] + s['source_timerange']['duration']
            x, y = max(a, cs), min(b, ce)
            if y - x > 100_000:
                hit.append((ts(s) + x - a, ts(s) + y - a))
        if not hit:
            gone.append(r['id']); continue
        t0, t1 = min(h[0] for h in hit), max(h[1] for h in hit)
        what = K.get(r['kind'], r['kind'])
        said = '' if r['kind'] == 'silence' else (c.get('text') or '').split('|')[0].strip()
        line1 = f"למחיקה · {r['id']} · {what} · {(t1 - t0) / US:.1f} שנ׳"
        text = line1 + (f"\n«{said[:70]}»" if said else '')
        blocks.append({'text': text, 'start_us': t0, 'duration_us': t1 - t0, 'words': None})
    # the range markers of these spans go; the other markers stay
    ids = {i for r in rs for i in r['id'].split('+')} | {r['id'] for r in rs}
    tm = d.get('time_marks') or {'mark_items': []}
    before = len(tm['mark_items'])
    tm['mark_items'] = [m for m in tm['mark_items'] if not (m['time_range'].get('duration', 0) > 0 and m['title'].split(' · ')[0] in ids)]
    print(json.dumps({'blocks': len(blocks), 'already_removed_by_alon': gone, 'markers': f"{before} → {len(tm['mark_items'])}",
                      'first': [(round(b['start_us'] / US, 2), round(b['duration_us'] / US, 2), b['text'].split(chr(10))[0]) for b in blocks[:3]]}, ensure_ascii=False))
    if not WRITE:
        return
    dst = D / reels._unique_name(V8)
    def cp(a, b, *x, **k):
        if os.path.getsize(a) > 50_000_000:
            os.link(a, b); return b
        return shutil.copy2(a, b)
    shutil.copytree(D / V7, dst, copy_function=cp, ignore=lambda dd, n: [x for x in n if x.startswith('draft_info.ccstudio-backup') or x.endswith(('.tmp', '.bak'))])
    d = json.loads(json.dumps(d, ensure_ascii=False).replace(str(D / V7) + '/', str(dst) + '/'))
    for f in (dst / 'subdraft').glob('*/draft_content.json'):
        f.write_text(f.read_text().replace(str(D / V7) + '/', str(dst) + '/'))
    capcut._atomic_write(dst, d)
    mp = dst / 'draft_meta_info.json'; meta = json.loads(mp.read_text()); now = int(time.time() * US)
    meta.update({'draft_id': capcut._new_id(), 'draft_name': dst.name, 'draft_fold_path': str(dst), 'tm_draft_create': now,
                 'tm_draft_modified': now, 'tm_duration': d['duration']})
    mp.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta['draft_id'], d['duration'], V7)
    capcut.inject_captions(dst.name, blocks, style(), replace_existing=False)
    d2 = capcut.load_draft(dst.name)
    d2['tracks'][-1]['name'] = 'למחיקה'
    capcut._atomic_write(dst, d2)
    # the SRT, same spans
    def st(us):
        ms = int(round(us / 1000)); h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    L = []
    for i, b in enumerate(blocks, 1):
        L += [str(i), f"{st(b['start_us'])} --> {st(b['start_us'] + b['duration_us'])}", b['text'], '']
    (HERE / 'קטעים למחיקה - מיד וסיניור (v8).srt').write_text('\n'.join(L), encoding='utf-8-sig')
    print('✅', dst.name)


if __name__ == '__main__':
    main()
