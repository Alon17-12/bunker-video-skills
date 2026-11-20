#!/usr/bin/env python3
"""v11 = Alon's v10 (20.11, 01:00) with every «למחיקה» block he left on the track CUT (= approved), the 25 s gap he opened in
senior closed, captions corrected word by word across every join, the LUT / routing / plates rippled with it. Red markers ONLY
where I want his eye (Alon 20.11: «איפה שאתה רוצה עוד מבט שלי… שים לי מרקר אדום»): a join with speech at the cut instant, or a
caption I could not correct with certainty.
Each cut edge snaps to the quietest 10 ms within ±60 ms first (a cut between words, not inside one).
Then v10 → Trash: one client E project remains.        build_v11.py [--write]"""
import difflib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app')); sys.path.insert(0, str(Path(__file__).parent))
import capcut, reels
import edit_engine as E

HERE = Path(__file__).parent; D = capcut.DRAFTS_DIR; US = 1_000_000
CUR = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v10'; OUT = 'לקוח E · VSL + ג׳וניור + מיד + סיניור · 18.11.26 v11'
WRITE = '--write' in sys.argv
FF = os.path.expanduser('~/ffmpeg-bin/ffmpeg')
WORDS = Path('/private/tmp/claude-501/-Users-alongabaymain/1a66187f-134c-45dd-b0bc-c927f4702122/scratchpad/words_src.json')
LOUD = -38.0                         # dB in the 10 ms at the join: above this there is speech at the cut instant → his eye
ts, te = E.ts, E.te
hms = lambda us: f"{int(us / US // 60)}:{us / US % 60:05.2f}"

d = json.loads(re.sub(r'##_draftpath_placeholder_[0-9A-F-]+_##', str(D / CUR), (D / CUR / 'draft_info.json').read_text()))
idx = E.mats_index(d)
tx = {x['id']: x for x in d['materials']['texts']}
DIA = next(t for t in d['tracks'] if t['type'] == 'audio' and t.get('name', '') == '')
CAP = next(t for t in d['tracks'] if t.get('name') == 'כתוביות')
BLK = next(t for t in d['tracks'] if t.get('name') == 'למחיקה')
text_of = lambda s: json.loads(tx[s['material_id']]['content'])['text']


def dia():
    return [(ts(s), te(s), idx[s['material_id']][1]['path'], s['source_timerange']['start']) for s in sorted(DIA['segments'], key=ts)]


A = dia()
def src_at(t, side):                 # side 'L' = the sound just before t, 'R' = just after
    for a, b, f, s in A:
        if (a < t <= b) if side == 'L' else (a <= t < b):
            return f, s + t - a
    return None, None


def tl_of(f, src):
    for a, b, ff, s in A:
        if os.path.basename(ff) == os.path.basename(f) and s <= src < s + (b - a):
            return a + src - s


_pcm = {}
def pcm(p):
    if p not in _pcm:
        raw = subprocess.run([FF, '-v', 'quiet', '-i', p, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
        _pcm[p] = np.frombuffer(raw, dtype=np.float32)
    return _pcm[p]


def db(p, src_us, w_ms=10):
    x = pcm(p); i = int(src_us / US * 16000); h = int(w_ms * 8)
    seg = x[max(0, i - h):i + h]
    return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)) if len(seg) else -99.0


def snap(t, side):
    """move a cut edge to the quietest 10 ms within ±60 ms (on its own side's sound)"""
    f, s = src_at(t, side)
    if f is None:
        return t
    best = min(range(-60_000, 60_001, 5_000), key=lambda k: db(f, s + k))
    return t + best if db(f, s + best) < db(f, s) - 6 else t


# ---- the cuts -------------------------------------------------------------------------------------------------------------
cuts = []
for s in sorted(BLK['segments'], key=ts):
    head, *rest = text_of(s).split('\n')
    p = head.split(' · ')
    cuts.append({'a': ts(s), 'b': te(s), 'id': p[1], 'kind': p[2], 'said': rest[0] if rest else ''})
main = sorted(d['tracks'][0]['segments'], key=ts)
for x, y in zip(main, main[1:]):
    if ts(y) - te(x) > 1_000_000:
        cuts.append({'a': te(x), 'b': ts(y), 'id': 'פער', 'kind': 'הפער שהשארת', 'said': ''})
cuts.sort(key=lambda c: c['a'])
for c in cuts:
    if c['id'] != 'פער':
        c['a'], c['b'] = snap(c['a'], 'L'), snap(c['b'], 'R')
    fa, sa = src_at(c['a'], 'L'); fb, sb = src_at(c['b'], 'R')
    c['ea'] = db(fa, sa - 5_000) if fa else -99.0           # the last 10 ms kept before the join
    c['eb'] = db(fb, sb + 5_000) if fb else -99.0           # the first 10 ms kept after it
    c['why'] = []
    if max(c['ea'], c['eb']) > LOUD:
        c['why'].append('דיבור בנקודת החיבור')


_model = None
def hear_after_cut(S, Ee, pad=150_000):
    """the card window [S, Ee) as it will sound after the cuts → Whisper words"""
    global _model
    import transcribe as T
    pieces, t = [], S - pad
    for c in sorted(cuts, key=lambda c: c['a']):
        if c['b'] <= t or c['a'] >= Ee + pad:
            continue
        if c['a'] > t:
            pieces.append((t, c['a']))
        t = max(t, c['b'])
    if t < Ee + pad:
        pieces.append((t, Ee + pad))
    audio = []
    for a, b in pieces:
        for x0, x1, f, s0 in A:
            lo, hi = max(a, x0), min(b, x1)
            if hi > lo:
                x = pcm(f); i, j = int((s0 + lo - x0) / US * 16000), int((s0 + hi - x0) / US * 16000)
                audio.append(x[i:j])
    if not audio:
        return []
    return T.transcribe(np.concatenate(audio).astype(np.float32))

# ---- captions: which words go -----------------------------------------------------------------------------------------------
W = json.loads(WORDS.read_text())
for w in W:
    w['t'] = tl_of(w['file'], w['src']) if 'src' in w else None
gone = lambda t: t is not None and any(c['a'] <= t < c['b'] for c in cuts)
norm = lambda x: re.sub(r'[^\w\-]', '', x.replace('״', '').replace('׳', "'")).lower()

caption_edits, removed_cards, emptied = {}, set(), set()
for s in CAP['segments']:
    S, Ee = ts(s), te(s)
    hit = [c for c in cuts if c['a'] < Ee and c['b'] > S]
    if not hit:
        continue
    if all(c['a'] <= S and Ee <= c['b'] for c in hit) or any(c['a'] <= S and Ee <= c['b'] for c in hit):
        removed_cards.add(s['id']); continue                 # wholly inside a cut: the ripple removes it
    old = text_of(s); toks = old.split()
    # the truth = what the joined sound says now: transcribe the card's window AFTER the cut (Whisper word times run early,
    # so timing alone hands a repeated word to the wrong side: «לא לקבל» → «לא מישהו», «זה לא אומר» lost)
    heard = [norm(w['text']) for w in hear_after_cut(S, Ee)]
    said = [norm(x) for c in hit for x in re.sub(r'\[[^\]]*:|[«»…()\[\]]', ' ', c['said']).split()]
    sm = difflib.SequenceMatcher(None, [norm(t) for t in toks], heard, autojunk=False)
    matched = set()
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
            matched.update(range(i1, i2))
    keep = [True] * len(toks); unsure = False; dropped = 0
    for i, t in enumerate(toks):
        if i in matched:
            continue
        if norm(t) in said:
            keep[i] = False; dropped += 1                    # not heard any more AND part of what the block said: gone
        else:
            unsure = True                                    # not heard, not in the block: Whisper missed it? keep + flag
    new = [t for t, k in zip(toks, keep) if k]
    unsure = unsure and dropped > 0                          # an unheard word on a card I did not change = Whisper/QA spelling, not my cut
    # every card word heard after the cut stays; nothing dropped is fine (the cut was between cards' words)
    for c in hit:
        c.setdefault('caps', []).append((old.replace('\n', ' '), ' '.join(new)))
        if unsure:
            c['why'].append('כתובית לבדיקה')
    if not new:
        removed_cards.add(s['id']); emptied.add(s['id']); continue
    if len(new) > 8:
        h = (len(new) + 1) // 2; new_text = ' '.join(new[:h]) + '\n' + ' '.join(new[h:])
    else:
        new_text = ' '.join(new)
    new_text = re.sub(r'^[,،]\s*', '', new_text)
    caption_edits[s['material_id']] = new_text

# ---- report -------------------------------------------------------------------------------------------------------------------
total = sum(c['b'] - c['a'] for c in cuts)
red = [c for c in cuts if c['why']]
print(f"cuts {len(cuts)} · {total / US:.1f} s · red {len(red)} · captions edited {len(caption_edits)} · cards removed {len(removed_cards)}")
for c in cuts:
    print(f"{hms(c['a'])} {(c['b'] - c['a']) / US:5.2f} {c['id']:8} {c['kind']:12} {c['ea']:6.1f} {c['eb']:6.1f} {'🔴 ' + ' + '.join(dict.fromkeys(c['why'])) if c['why'] else ''}  {c['said'][:60]}")
    for o, n in c.get('caps', []):
        print('      ', o[:70], '\n    → ', n[:70])
if not WRITE:
    sys.exit()

# ---- apply --------------------------------------------------------------------------------------------------------------------
if capcut._capcut_pid() is not None:
    sys.exit('⛔ CapCut פתוח')
for c in sorted(cuts, key=lambda c: -c['a']):                 # last first: earlier times stay valid
    E.ripple_cut(d, c['a'], c['b'])
for c in cuts:                                                # where each join lands now
    c['j'] = c['a'] - sum(x['b'] - x['a'] for x in cuts if x['a'] < c['a'])
for mid, new_text in caption_edits.items():
    m = tx[mid]
    for f in ('content', 'base_content'):
        if m.get(f):
            p = json.loads(m[f]); p['text'] = new_text
            if p.get('styles'):
                st = p['styles'][0]; st['range'] = [0, len(new_text)]; p['styles'] = [st]
            m[f] = json.dumps(p, ensure_ascii=False)
CAP['segments'] = [s for s in CAP['segments'] if s['id'] not in emptied]   # a card whose every word was cut
left = [s for s in BLK['segments']]
if left:
    print('⚠️ blocks left on «למחיקה»:', [hms(ts(s)) for s in left])
else:
    d['tracks'].remove(BLK)
nz = E.zoom_jumps(d, [c['j'] for c in cuts])
ns = E.fix_short_shots(d)
E.add_markers(d, [{'t': c['j'], 'color': '#ff375f',
                   'title': f"בדוק חיתוך · {c['id']} · {' + '.join(dict.fromkeys(c['why']))}"} for c in red])
print('zoom', nz, 'short shots', ns)

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
meta.update({'draft_id': capcut._new_id(), 'draft_name': dst.name, 'draft_fold_path': str(dst), 'tm_draft_create': now,
             'tm_draft_modified': now, 'tm_duration': d['duration']})
mp.write_text(json.dumps(meta, ensure_ascii=False))
reels._registry_add(dst, meta['draft_id'], d['duration'], CUR)
(HERE / 'v11_cuts.json').write_text(json.dumps([{k: v for k, v in c.items()} for c in cuts], ensure_ascii=False, indent=1, default=str))
reg = D / 'root_meta_info.json'; shutil.copy2(reg, str(reg) + '.before-v10-trash')
r = json.loads(reg.read_text()); r['all_draft_store'] = [x for x in r['all_draft_store'] if os.path.basename(x.get('draft_fold_path', '')) != CUR]
tmp = str(reg) + '.tmp'; Path(tmp).write_text(json.dumps(r, ensure_ascii=False)); os.replace(tmp, reg)
shutil.move(str(D / CUR), os.path.expanduser('~/.Trash/' + CUR + ' ' + time.strftime('%H%M%S')))
print('✅', dst.name, '· duration', hms(d['duration']))
