#!/usr/bin/env python3
"""פרויקט הפרק המלא ב-CapCut, משוכפל מפרק קודם שאלון כבר אישר (15.10.2026, אורח T אורח N מתוך אורח J).

המבנה של אלון (״פתיחה — טיזר 16:9 · פרק — קובץ רז מהתיקייה · סיום · פופאפ הרשמה כל 10 דקות עם הלוגואים למעלה״) כבר
קיים בפרויקט «אורח U אורח J צומת 20 פרק». כאן לא בונים אותו מחדש: מעתיקים את התיקייה, מחליפים את שלושת הקבצים
(טיזר, רז, אורך), ופורסים מחדש את מה שתלוי באורך — הסגירה, הבאנרים והלוגואים.

    PY=~/bunker-video-engine/.venv/bin/python
    $PY build_episode_from_template.py --teaser ".../טיזר 16x9.mp4" --episode ".../… רז.mp4" --name "אורח T אורח N צומת 20 פרק" \
        [--end-music <teaser>/public/music.wav --hit 128.5 --bar 1.4033 --ph 0.705] [--dry-run]

--end-music (Alon, 15.10.2026: "לשלב בסיום מוזיקה עדינה — מהסוף של המוזיקה של הטריילר" → "מושלם"): the end of the
teaser's own track, from a bar line ~18 s before its last drum hit; the hit lands on the closing card, the ring-out
plays over it. Under the last words it is a soft bed (2× lowpass 1.4 kHz, ×0.08 ≈ 11 dB under the ×2.24 dialogue), in
the last 2.2 s before the hit it opens to the full track (×0.42), and fades out over the last 0.8 s of the project.
Baked to "<episode folder>/<…> - מוזיקת סיום.wav" and added as its own audio track (volume 1.0).

שומרים: CapCut סגור לגמרי (רישום פרויקט כותב ל-root_meta_info.json). התבנית נקראת בלבד.
"""
import argparse, copy, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut, reels

US = 1_000_000
TEMPLATE = 'אורח U אורח J צומת 20 פרק'
BANNER_FIRST = 7_650_000      # באורח J: 7.65 שנ' אחרי תחילת הפרק
BANNER_EVERY = 600_000_000    # כל 10 דקות


def probe_dur_us(path):
    ff = next(c for c in (os.path.expanduser('~/ffmpeg-bin/ffprobe'), '/opt/homebrew/bin/ffprobe') if os.path.exists(c))
    r = subprocess.run([ff, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return int(round(float(r.stdout.strip()) * US))


def mat_index(d):
    return {m['id']: m for lst in d['materials'].values() if isinstance(lst, list) for m in lst if isinstance(m, dict) and m.get('id')}


def build(d, teaser, t_us, episode, e_us):
    idx = mat_index(d)
    path = lambda s: str(idx.get(s['material_id'], {}).get('path', ''))
    spine = d['tracks'][0]
    segs = sorted(spine['segments'], key=lambda s: s['target_timerange']['start'])
    s_t = next(s for s in segs if 'טיזר' in path(s))
    s_e = next(s for s in segs if 'רז' in path(s))
    s_c = next(s for s in segs if path(s).endswith('.png'))
    for s, p, dur in ((s_t, teaser, t_us), (s_e, episode, e_us)):
        m = idx[s['material_id']]
        m['path'] = str(p); m['material_name'] = os.path.basename(str(p)); m['duration'] = dur
        s['source_timerange'] = {'start': 0, 'duration': dur}
    s_t['target_timerange'] = {'start': 0, 'duration': t_us}
    s_e['target_timerange'] = {'start': t_us, 'duration': e_us}
    ep_end = t_us + e_us
    c_us = s_c['target_timerange']['duration']
    s_c['target_timerange'] = {'start': ep_end, 'duration': c_us}
    total = ep_end + c_us

    out = {'banners': [], 'logos': 0}
    for t in d['tracks'][1:]:
        if t['type'] != 'video' or not t['segments']:
            continue
        p0 = path(t['segments'][0])
        if 'באנר' in p0:                      # the subscribe pop-up: re-laid every 10 min from the new episode start
            proto = sorted(t['segments'], key=lambda s: s['target_timerange']['start'])[0]
            bans, at = [], t_us + BANNER_FIRST
            while at + proto['target_timerange']['duration'] <= ep_end:
                b = copy.deepcopy(proto); b['id'] = capcut._new_id()
                b['target_timerange'] = {'start': at, 'duration': proto['target_timerange']['duration']}
                bans.append(b); out['banners'].append(round(at / US, 2)); at += BANNER_EVERY
            t['segments'] = bans
        elif p0.endswith('.png'):             # the logos at the top: the whole episode
            for s in t['segments']:
                s['target_timerange'] = {'start': t_us, 'duration': e_us}
                s['source_timerange'] = {'start': 0, 'duration': e_us}
            out['logos'] += 1
    d['duration'] = total
    return total, out


def bake_end_music(music, hit, bar, ph, length_us, hit_at_us, out):
    """the last ~18 s of the teaser track, so its final hit lands at hit_at_us (relative to the clip start) — see --end-music"""
    ff = next(c for c in (os.path.expanduser('~/ffmpeg-bin/ffmpeg'), '/opt/homebrew/bin/ffmpeg') if os.path.exists(c))
    x = ph + math.floor((hit - 18 - ph) / bar) * bar          # a bar line ~18 s before the hit
    th, L = hit - x, length_us / US
    lp = f"0.08*min(t/3\\,1)*(1-min(max((t-({th}-2.2))/2.2\\,0)\\,1))"
    fu = f"0.42*min(max((t-({th}-2.2))/2.2\\,0)\\,1)*(1-min(max((t-({L}-0.8))/0.8\\,0)\\,1))"
    fc = f"[0]asplit[a][b];[a]lowpass=f=1400,lowpass=f=1400,volume='{lp}':eval=frame[lp];[b]volume='{fu}':eval=frame[fu];[lp][fu]amix=inputs=2:normalize=0"
    subprocess.run([ff, '-v', 'error', '-y', '-ss', f'{x:.4f}', '-t', f'{L:.4f}', '-i', str(music), '-filter_complex', fc,
                    '-ar', '48000', '-c:a', 'pcm_s24le', str(out)], check=True)
    return int(round(th * US))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--teaser', required=True); ap.add_argument('--episode', required=True)
    ap.add_argument('--name', required=True); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--end-music'); ap.add_argument('--hit', type=float); ap.add_argument('--bar', type=float); ap.add_argument('--ph', type=float, default=0.0)
    a = ap.parse_args()
    for p in (a.teaser, a.episode):
        if not Path(p).exists():
            sys.exit(f'⛔ חסר: {p}')
    t_us, e_us = probe_dur_us(a.teaser), probe_dur_us(a.episode)
    tpl = capcut.load_draft(TEMPLATE)
    if a.dry_run:
        total, out = build(copy.deepcopy(tpl), a.teaser, t_us, a.episode, e_us)
        print(f'[dry-run] טיזר {t_us/US:.2f}s · פרק {e_us/US/60:.1f} דק׳ · סה"כ {total/US/60:.1f} דק׳ · באנרים {out["banners"]} · לוגואים {out["logos"]}')
        return
    if capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח — סגור אותו לגמרי ותריץ שוב.')
    new_name = reels._unique_name(a.name)
    dst = capcut.DRAFTS_DIR / new_name
    reels._copy_draft_folder(capcut.DRAFTS_DIR / TEMPLATE, dst)
    try:
        d = json.loads((dst / 'draft_info.json').read_text())
        total, out = build(d, a.teaser, t_us, a.episode, e_us)
        tmp = dst / 'draft_info.tmp'
        tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':'))); json.loads(tmp.read_text()); tmp.replace(dst / 'draft_info.json')
        meta_id = capcut._new_id(); mp = dst / 'draft_meta_info.json'
        if mp.exists():
            meta = json.loads(mp.read_text()); now = int(time.time() * US)
            meta.update({'draft_id': meta_id, 'draft_name': new_name, 'draft_fold_path': str(dst), 'tm_draft_create': now, 'tm_draft_modified': now, 'tm_duration': total})
            mp.write_text(json.dumps(meta, ensure_ascii=False))
        reels._registry_add(dst, meta_id, total, TEMPLATE)
    except Exception:
        shutil.rmtree(dst, ignore_errors=True)
        raise
    if a.end_music:
        close_at = t_us + e_us
        th_us = int(round((a.hit - (a.ph + math.floor((a.hit - 18 - a.ph) / a.bar) * a.bar)) * US))
        out = Path(a.episode).parent / (Path(a.episode).stem.split(' רז')[0].split('  ')[-1].strip() + ' - מוזיקת סיום.wav')
        bake_end_music(a.end_music, a.hit, a.bar, a.ph, total - (close_at - th_us), th_us, out)
        capcut.add_audio(new_name, str(out), 'מוזיקת סיום', at_us=close_at - th_us, duration_us=total - (close_at - th_us), volume=1.0, kind='music')
        print(f'   מוזיקת סיום: {out.name} מ-{(close_at - th_us)/US:.2f}s, המכה על מסך הסגירה ({close_at/US:.2f}s)')
    print(f'✅ «{new_name}» · טיזר {t_us/US:.2f}s · פרק {e_us/US/60:.1f} דק׳ · סה"כ {total/US/60:.1f} דק׳')
    print(f'   באנרים ({len(out["banners"])}): {out["banners"]} · לוגואים: {out["logos"]}')


if __name__ == '__main__':
    main()
