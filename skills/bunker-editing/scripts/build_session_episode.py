#!/usr/bin/env python3
"""The full episode of a סשן בונקר as a CapCut project, cloned from an approved episode project.

The template («אורח U אורח J צומת 20 פרק») already carries the house episode structure. Here it is reduced to
what the session spec asks for:
  · spine      — «מקור» trimmed to [trim_in, trim_out], muted (its sound is the Live-Mix, never used)
  · dialogue   — <session>/פרק/דיאלוג.wav (mic_dialogue.py master, on the «מקור» clock), same trim, volume 1.0
  · grade      — the Bunker LUT, cloned from a 16:9 Bunker project (--color-from)
  · logo       — the Bunker logo track of the template, over the whole episode (only if episode.logo.on)
  · names      — one lower-third PNG per speaker at their first words (only if episode.names_on_screen)
  · fades      — 0.5 s video (alpha keyframes) and audio fade in/out
Removed: teaser, closing card, subscribe banners, the צומת 20 logo (none of them is in the spec).

    $PY build_session_episode.py <session> --trim-in 3.2 --trim-out 850.1 --first "אלון=12.4" --first "אורח R=31.0" [--dry-run]

CapCut must be fully closed (registering a project writes root_meta_info.json). The template is read only.
"""
import argparse, copy, json, os, shutil, sys, time
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut, reels

US = 1_000_000
TEMPLATE = 'אורח U אורח J צומת 20 פרק'
COLOR_FROM = '14.08.26 - אורח R ואורח T 1 - רז'
FADE_US = 500_000
LT_SECONDS = 5.0
LT_SCALE, LT_X, LT_Y = 0.40, 0.504, -0.583      # 760×190 PNG, bottom-right, clear of the faces
LOGO_X, LOGO_Y = 0.83, 0.80                      # Bunker logo (scale 0.127 ≈ 244×134 px): ~40 px from the top and right edges


def mat_index(d):
    return {m['id']: m for lst in d['materials'].values() if isinstance(lst, list) for m in lst if isinstance(m, dict) and m.get('id')}


def alpha_kf(dur_us, src_start_us=0):
    """Fade in/out on a segment. CapCut reads keyframe time_offset on the SOURCE clock (source_timerange.start + offset):
    on the trimmed «מקור» spine relative offsets landed before the segment and the picture never faded (Alon, 17.10.2026)."""
    kf = lambda t, v, curve='Line': {'id': capcut._new_id(), 'curveType': curve, 'time_offset': src_start_us + t,
                                     'left_control': {'x': 0.0, 'y': 0.0}, 'right_control': {'x': 0.0, 'y': 0.0},
                                     'values': [v], 'string_value': '', 'graphID': ''}
    return {'id': capcut._new_id(), 'material_id': '', 'property_type': 'KFTypeAlpha',
            'keyframe_list': [kf(0, 0.0), kf(FADE_US, 1.0, 'CurveInOut'), kf(dur_us - FADE_US, 1.0), kf(dur_us, 0.0, 'CurveInOut')]}


def build(d, source, src_dur_us, trim_in_us, trim_out_us, show_logo):
    idx = mat_index(d)
    path = lambda s: str(idx.get(s['material_id'], {}).get('path', ''))
    e_us = trim_out_us - trim_in_us
    spine = d['tracks'][0]
    s_e = next(s for s in spine['segments'] if 'רז' in path(s))
    m = idx[s_e['material_id']]
    m['path'] = str(source); m['material_name'] = source.name; m['duration'] = src_dur_us
    s_e['source_timerange'] = {'start': trim_in_us, 'duration': e_us}
    s_e['target_timerange'] = {'start': 0, 'duration': e_us}
    s_e['volume'] = 0.0                                   # «מקור» sound = Live-Mix: muted, the dialogue track plays
    s_e['common_keyframes'] = [k for k in s_e.get('common_keyframes', []) if k.get('property_type') != 'KFTypeAlpha'] + [alpha_kf(e_us, trim_in_us)]
    spine['segments'] = [s_e]
    kept = [spine]
    logos = 0
    for t in d['tracks'][1:]:
        if t['type'] != 'video' or not t['segments']:
            continue                                      # audio / text from the template never belong to this episode
        p0 = path(t['segments'][0])
        if show_logo and p0.endswith('.png') and ('בונקר' in p0 or 'BUNJER' in p0.upper() or 'BUNKER' in p0.upper()):
            s = t['segments'][0]; t['segments'] = [s]
            s['target_timerange'] = {'start': 0, 'duration': e_us}
            s['source_timerange'] = {'start': 0, 'duration': e_us}
            # Alon 17.10.2026: the logo sits in the top-right corner, high (Guest J had it under the צומת 20 logo, y 0.46)
            s['clip'] = dict(s.get('clip') or {}, transform={'x': LOGO_X, 'y': LOGO_Y})
            kept.append(t); logos += 1
    d['tracks'] = kept
    d['duration'] = e_us
    return e_us, logos


def add_lower_thirds(draft_name, items):
    """items: [(png_path, at_us)] — photo overlays on one new track, bottom-right."""
    draft_dir = capcut.DRAFTS_DIR / draft_name
    d = capcut.load_draft(draft_name)
    mat0, seg0, extras0 = reels._photo_donor()
    mats = d['materials']
    segs = []
    for png, at in items:
        dst = draft_dir / Path(png).name
        shutil.copy2(png, dst)                            # inside the draft folder: no CapCut sandbox relink
        mat = copy.deepcopy(mat0); mat['id'] = capcut._new_id(); mat['path'] = str(dst)
        mat['material_name'] = dst.name; mat['width'], mat['height'] = 760, 190
        mats.setdefault('videos', []).append(mat)
        seg = copy.deepcopy(seg0); seg['id'] = capcut._new_id(); seg['material_id'] = mat['id']
        refs = []
        for ex in extras0:
            e = copy.deepcopy(ex['material']); e['id'] = capcut._new_id()
            mats.setdefault(ex['list'], []).append(e); refs.append(e['id'])
        seg['extra_material_refs'] = refs
        dur = int(LT_SECONDS * US)
        seg['target_timerange'] = {'start': at, 'duration': dur}
        seg['source_timerange'] = {'start': 0, 'duration': dur}
        seg['clip'] = dict(seg.get('clip') or {}, scale={'x': LT_SCALE, 'y': LT_SCALE},
                           transform={'x': LT_X, 'y': LT_Y}, alpha=1.0, rotation=0.0)
        seg['common_keyframes'] = [alpha_kf(dur)]
        segs.append(seg)
    d['tracks'].append({'id': capcut._new_id(), 'type': 'video', 'attribute': 0, 'flag': 0, 'name': 'שמות', 'segments': segs})
    capcut._atomic_write(draft_dir, d)
    return len(segs)


def add_routing_patches(draft_name, patches, trim_in_us, cams):
    """patches: [(cam 1|2, src_from_s, src_to_s)] — the live switch had the listener on air while the other one talked
    (routing_audit.py). Each patch puts that camera over the spine for the run, on its own track right above the spine
    (cameras are on the «מקור» clock, offset 0 on the RØDECaster), muted; the grade above covers them like the spine."""
    draft_dir = capcut.DRAFTS_DIR / draft_name
    d = capcut.load_draft(draft_name)
    idx = mat_index(d)
    spine_seg = d['tracks'][0]['segments'][0]
    donor = idx[spine_seg['material_id']]
    mats, segs, by_cam = d['materials'], [], {}
    for cam, a, b in patches:
        if cam not in by_cam:
            m = copy.deepcopy(donor); m['id'] = capcut._new_id(); m['path'] = str(cams[cam]); m['material_name'] = Path(cams[cam]).name
            mats['videos'].append(m); by_cam[cam] = m['id']
        seg = copy.deepcopy(spine_seg); seg['id'] = capcut._new_id(); seg['material_id'] = by_cam[cam]
        seg['common_keyframes'] = []; seg['volume'] = 0.0
        refs = []                                          # speed / canvas / … : CapCut wants its own copy per segment
        for r in spine_seg.get('extra_material_refs', []):
            lst = next((k for k, v in mats.items() if isinstance(v, list) and any(isinstance(x, dict) and x.get('id') == r for x in v)), None)
            if not lst or lst in ('audio_fades', 'transitions'):
                continue
            e = copy.deepcopy(next(x for x in mats[lst] if x.get('id') == r)); e['id'] = capcut._new_id()
            mats[lst].append(e); refs.append(e['id'])
        seg['extra_material_refs'] = refs
        a_us, b_us = int(round(a * US)), int(round(b * US))
        seg['source_timerange'] = {'start': a_us, 'duration': b_us - a_us}
        seg['target_timerange'] = {'start': a_us - trim_in_us, 'duration': b_us - a_us}
        segs.append(seg)
    d['tracks'].insert(1, {'id': capcut._new_id(), 'type': 'video', 'attribute': 0, 'flag': 0, 'name': 'ניתוב', 'segments': segs})
    capcut._atomic_write(draft_dir, d)
    return len(segs)


def grade_footage_only(draft_name):
    """The Bunker grade belongs to the camera picture only: the adjust layer sits right above the spine (so the logo
    and the names above it stay in brand colours), and no graphic segment carries enable_lut."""
    draft_dir = capcut.DRAFTS_DIR / draft_name
    d = capcut.load_draft(draft_name)
    spine, rest = d['tracks'][0], d['tracks'][1:]
    footage = [t for t in rest if t.get('name') == 'ניתוב']           # routing patches are camera picture: graded too
    rest = [t for t in rest if t.get('name') != 'ניתוב']
    adjust = [t for t in rest if t['type'] == 'adjust']
    video = [t for t in rest if t['type'] == 'video']
    other = [t for t in rest if t['type'] not in ('adjust', 'video')]
    for t in video:
        for seg in t['segments']:
            seg['enable_lut'] = False
    d['tracks'] = [spine] + footage + adjust + video + other
    capcut._atomic_write(draft_dir, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('session'); ap.add_argument('--trim-in', type=float, required=True); ap.add_argument('--trim-out', type=float, required=True)
    ap.add_argument('--first', action='append', default=[], help='"<name>=<seconds on the «מקור» clock>"')
    ap.add_argument('--patches', help='routing patches json: [[cam, from_s, to_s], …] on the «מקור» clock')
    ap.add_argument('--name'); ap.add_argument('--color-from', default=COLOR_FROM); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    S = Path(a.session)
    spec = json.loads((S / 'אפיון.json').read_text(encoding='utf-8'))
    ing = json.loads((S / 'ingest.json').read_text())
    source, dialogue = Path(ing['source']), S / 'פרק' / 'דיאלוג.wav'
    for p in (source, dialogue):
        if not p.exists():
            sys.exit(f'⛔ חסר: {p}')
    src_dur = int(round(float(ing['durations']['source']) * US))
    # trims on the 30 fps grid: 11.55 s (frame 346.5) put every routing patch half a frame off «מקור» → 65 one-frame flashes (אורח C, 27.10.2026)
    a.trim_in, a.trim_out = round(a.trim_in * 30) / 30, round(a.trim_out * 30) / 30
    tin, tout = int(round(a.trim_in * US)), int(round(a.trim_out * US))
    ep = spec.get('episode', {})
    show_logo = bool(ep.get('logo', {}).get('on'))
    firsts = []
    if ep.get('names_on_screen'):
        for f in a.first:
            n, t = f.split('=')
            png = S / 'פרק' / 'גרפיקה' / f'שם - {n}.png'
            if not png.exists():
                sys.exit(f'⛔ חסרה גרפיקת שם: {png}')
            firsts.append((str(png), max(0, int(round(float(t) * US)) - tin)))
    name = a.name or f"{spec['client']} · פרק · {S.name.split(' · ')[-1]}"
    tpl = capcut.load_draft(TEMPLATE)
    if a.dry_run:
        e_us, logos = build(copy.deepcopy(tpl), source, src_dur, tin, tout, show_logo)
        print(f'[dry-run] «{name}» · {e_us/US/60:.2f} דק׳ · לוגו {logos} · שמות {[(Path(p).stem, round(t/US, 2)) for p, t in firsts]}')
        return
    if capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.')
    color = capcut.extract_color(a.color_from)
    new_name = reels._unique_name(name)
    dst = capcut.DRAFTS_DIR / new_name
    reels._copy_draft_folder(capcut.DRAFTS_DIR / TEMPLATE, dst)
    try:
        d = json.loads((dst / 'draft_info.json').read_text())
        e_us, logos = build(d, source, src_dur, tin, tout, show_logo)
        capcut._atomic_write(dst, d)
        meta_id = capcut._new_id(); mp = dst / 'draft_meta_info.json'
        if mp.exists():
            meta = json.loads(mp.read_text()); now = int(time.time() * US)
            meta.update({'draft_id': meta_id, 'draft_name': new_name, 'draft_fold_path': str(dst),
                         'tm_draft_create': now, 'tm_draft_modified': now, 'tm_duration': e_us})
            mp.write_text(json.dumps(meta, ensure_ascii=False))
        reels._registry_add(dst, meta_id, e_us, TEMPLATE)
        local_dialogue = S / '.tmp' / 'דיאלוג - פרק.wav'    # the same trim as the picture, so it sits at 0
        import subprocess
        subprocess.run([os.path.expanduser('~/ffmpeg-bin/ffmpeg'), '-v', 'error', '-y', '-ss', f'{a.trim_in:.6f}',
                        '-t', f'{(tout - tin) / US:.6f}', '-i', str(dialogue), '-c:a', 'pcm_s24le', str(local_dialogue)], check=True)
        capcut.add_audio(new_name, str(local_dialogue), 'דיאלוג', at_us=0, duration_us=e_us, volume=1.0, kind='sfx')
        n_patch = add_routing_patches(new_name, json.loads(Path(a.patches).read_text()), tin, {1: ing['cam1'], 2: ing['cam2']}) if a.patches else 0
        capcut.apply_color(new_name, color)
        n_lt = add_lower_thirds(new_name, firsts) if firsts else 0
        capcut.apply_fades(new_name, FADE_US // 1000)
        grade_footage_only(new_name)
    except Exception:
        shutil.rmtree(dst, ignore_errors=True)
        raise
    out = {'draft': new_name, 'duration_s': round(e_us / US, 2), 'trim_in': a.trim_in, 'trim_out': a.trim_out,
           'logo_tracks': logos, 'lower_thirds': n_lt, 'routing_patches': n_patch, 'color_from': a.color_from}
    (S / 'פרק' / 'פרויקט.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print('✅', json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
