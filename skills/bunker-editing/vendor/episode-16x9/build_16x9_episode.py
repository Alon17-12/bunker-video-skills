#!/usr/bin/env python3
"""9:16 טיזר → טיוטת פרק 16:9 מלאה (פתיח · פרק · מסך סגירה · באנר).

הפרויקט האנכי הוא מקור האמת. כאן לא עורכים אותו מחדש — מעתיקים את החיתוכים
כמו שהם, זורקים את המסגור האנכי, ומתאימים את הכתוביות לשני מספרים שנמדדו על
«אורח S צומת 20 פרק».
"""
import argparse, copy, json, os, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut, reels

US = 1_000_000
DONOR = 'אורח S צומת 20 פרק'          # ממנו נשאלים חומרי השלד והבאנר
ASSETS = Path(os.path.expanduser('~/Desktop/צומת 20/02 - חומרי גלם לעריכה'))
OPENER = ASSETS / 'קליפ פתיחה/פתיח צומת 20 (מאסטר 4K).mp4'
CLOSER = ASSETS / 'מסך סגירה/מסך סגירה - צומת 20 (1080p).png'
BANNER = ASSETS / 'באנרים/באנר יוטיוב - הירשמו (HEVC שקוף ל-CapCut).mov'

# --- המספרים. כולם נמדדו, אף אחד לא נבחר -----------------------------------
W, H, FPS = 1920, 1080, 60.0
OPENER_US   = 44_000_000        # הפתיח רץ *מתחת* לטיזר; הזנב הוא אנימציית הלוגו
OPENER_VOL  = 0.10000000149011612
CLOSER_US   = 3_283_333
CLOSER_SCALE = 1.05
BANNER_US   = 5_000_000
BANNER_FIRST = 7_620_000        # אחרי תחילת הפרק
BANNER_EVERY = 600_000_000      # כל 10 דקות
CAP_SIZE_9x16, CAP_SIZE_16x9 = 20.0, 10.2
CAP_Y_16x9 = -0.7450
TITLE_US = 25_000_000           # טקסט ארוך מזה הוא כותרת, לא כתובית

def is_camera(mat):
    """האם הסגמנט הוא צילום המצלמה — ורק עליו חל המסגור האנכי.

    ⚠️ הכלל הזה נלמד בדם: איפוס גורף של scale/transform על *כל* רצועת וידאו
    פוצץ שני לוגואים מ-0.411 ו-0.259 בפינה לפריים מלא במרכז. המסגור האנכי
    קיים אך ורק כדי לדחוס חומר *לרוחב* לתוך קנבס אנכי — אז מאפסים רק חומר
    שהמקור שלו רחב יותר מגובהו. PNG של לוגו, מדבקה או Compound אנכי — לא.
    """
    w, h = mat.get('width') or 0, mat.get('height') or 0
    return bool(mat.get('path')) and w > h


def is_portrait_compound(mat):
    """Compound אנכי הוא אלמנט 9:16 בלבד — בפרויקט הרוחבי של אורח S אין כאלה.
    בקנבס 1920x1080 הוא היה נראה כרצועה צרה באמצע."""
    return not mat.get('path') and (mat.get('height') or 0) > (mat.get('width') or 0)


def _ffprobe():
    # ⚠️ ה-ffprobe לא יושב ליד ה-ffmpeg של הקפטן — שם יש רק ffmpeg
    for c in (os.path.expanduser('~/ffmpeg-bin/ffprobe'),
              str(capcut.paths.FFMPEG).replace('ffmpeg', 'ffprobe'),
              '/opt/homebrew/bin/ffprobe', '/usr/local/bin/ffprobe'):
        if os.path.exists(c):
            return c
    sys.exit('⛔ ffprobe לא נמצא')


def probe_dur_us(path):
    r = subprocess.run([_ffprobe(), '-v', 'error', '-show_entries',
                        'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True)
    return int(round(float(r.stdout.strip()) * US))


def mat_index(draft):
    out = {}
    for lst, items in draft.get('materials', {}).items():
        if isinstance(items, list):
            for m in items:
                if isinstance(m, dict) and m.get('id'):
                    out[m['id']] = (lst, m)
    return out


def clone(donor_draft, donor_idx, seg, dst, path=None, dur_us=None):
    """מעתיק סגמנט מהתורם + כל החומרים שהוא מצביע עליהם, עם מזהים חדשים."""
    seg = copy.deepcopy(seg)
    remap = {}
    for mid in [seg['material_id']] + list(seg.get('extra_material_refs') or []):
        lst, m = donor_idx.get(mid, (None, None))
        if m is None:
            continue
        c = copy.deepcopy(m); c['id'] = capcut._new_id()
        if mid == seg['material_id'] and path is not None:
            c['path'] = str(path)
            c['material_name'] = os.path.basename(path)
            if dur_us is not None:
                c['duration'] = dur_us
        dst.setdefault('materials', {}).setdefault(lst, []).append(c)
        remap[mid] = c['id']
    seg['id'] = capcut._new_id()
    seg['material_id'] = remap.get(seg['material_id'], seg['material_id'])
    seg['extra_material_refs'] = [remap.get(r, r) for r in (seg.get('extra_material_refs') or [])]
    return seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--episode', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--teaser-end', type=float, default=None)
    a = ap.parse_args()

    if capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח. רישום פרויקט חדש כותב ל-root_meta_info.json '
                 'ש-CapCut מחזיק. תסגור אותו לגמרי ותריץ שוב.')
    for p in (OPENER, CLOSER, BANNER, Path(a.episode)):
        if not p.exists():
            sys.exit(f'⛔ חסר: {p}')

    src = capcut.load_draft(a.source)          # ⚠️ הטיוטה החיה, לא גיבוי
    donor = capcut.load_draft(DONOR)
    didx = mat_index(donor)
    sidx = mat_index(src)

    # --- איפה נגמר הטיזר: סוף הרצף הראשון ברצועת הווידאו התחתונה -----------
    main_tr = next(t for t in src['tracks'] if t['type'] == 'video' and t['segments'])
    segs = sorted(main_tr['segments'], key=lambda s: s['target_timerange']['start'])
    end = segs[0]['target_timerange']['start'] + segs[0]['target_timerange']['duration']
    for s in segs[1:]:
        if s['target_timerange']['start'] - end > 5 * US:
            break
        end = s['target_timerange']['start'] + s['target_timerange']['duration']
    teaser_end = int(a.teaser_end * US) if a.teaser_end else end
    print(f'טיזר: 0 → {teaser_end/US:.2f}s')

    ep_us = probe_dur_us(a.episode)
    # הפרק מתחיל כשהטיזר נגמר *וגם* הפתיח נגמר — בפרויקט אורח S (טיזר ~42s)
    # שניהם 44; טיזר ארוך מ-44 (מונטאז' רגעי שיא) דוחה את הפרק לסופו.
    ep_start = max(OPENER_US, teaser_end)
    ep_end = ep_start + ep_us
    total = ep_end + CLOSER_US
    print(f'פרק: {ep_us/US:.2f}s → {ep_start/US:.2f} עד {ep_end/US:.2f} · סה"כ {total/US/60:.1f} דק׳')

    # --- תיקייה חדשה -------------------------------------------------------
    new_name = reels._unique_name(a.name)
    dst_dir = capcut.DRAFTS_DIR / new_name
    reels._copy_draft_folder(capcut.DRAFTS_DIR / a.source, dst_dir)
    try:
        d = json.loads((dst_dir / 'draft_info.json').read_text())
        d['canvas_config'] = {'ratio': 'original', 'width': W, 'height': H, 'background': None}
        d['fps'] = FPS
        d['duration'] = total
        didx_new = mat_index(d)

        kept, stats = [], {'video': 0, 'caption': 0, 'dropped': 0, 'kf': 0,
                       'overlay': 0, 'other': []}
        for t in d['tracks']:
            keep = [s for s in t['segments']
                    if s['target_timerange']['start'] < teaser_end - 1000]
            stats['dropped'] += len(t['segments']) - len(keep)
            if not keep:
                continue
            t = dict(t, segments=keep)

            if t['type'] == 'video':
                fresh = []
                for s in keep:
                    mat = (didx_new.get(s['material_id']) or (None, {}))[1] or {}
                    if is_portrait_compound(mat):
                        stats['other'].append(
                            f"«{mat.get('material_name')}» (אנכי) הושמט — אין לו מקבילה ב-16:9")
                        stats['dropped'] += 1
                        continue
                    fresh.append(s)
                    if not is_camera(mat):
                        stats['overlay'] += 1      # שומרים אותו בדיוק כפי שהוא
                        continue
                    c = s.setdefault('clip', {})
                    c['scale'] = {'x': 1.0, 'y': 1.0}
                    c['transform'] = {'x': 0.0, 'y': 0.0}
                    # כל קבוצת הקיפריימים היא תנועת המסגור (מיקום+סקייל+סיבוב
                    # יחד). להשאיר את הסיבוב לבד זה יתום שממשיך לאינטרפולציה.
                    stats['kf'] += len(s.get('common_keyframes') or [])
                    s['common_keyframes'] = []
                    stats['video'] += 1
                if not fresh:
                    continue
                t['segments'] = keep = fresh

            elif t['type'] == 'text':
                for s in keep:
                    lst, m = didx_new.get(s['material_id'], (None, None))
                    if m is None:
                        continue
                    if s['target_timerange']['duration'] > TITLE_US:
                        stats['other'].append('טקסט ארוך — לא הומר')
                        continue
                    k = CAP_SIZE_16x9 / CAP_SIZE_9x16
                    if m.get('font_size'):
                        m['font_size'] = round(m['font_size'] * k, 2)
                    for field in ('content', 'base_content'):
                        if not m.get(field):
                            continue
                        try:
                            p = json.loads(m[field])
                        except json.JSONDecodeError:
                            continue
                        for st in p.get('styles', []):
                            if st.get('size'):
                                st['size'] = round(st['size'] * k, 2)
                        m[field] = json.dumps(p, ensure_ascii=False)
                    s.setdefault('clip', {}).setdefault('transform', {})['y'] = CAP_Y_16x9
                    stats['caption'] += 1

            elif t['type'] == 'adjust':
                for s in keep:
                    s['target_timerange'] = {'start': 0, 'duration': ep_end}

            elif t['type'] == 'audio':
                # הפתיח חוזר כווידאו על השלד עם האודיו שלו — רצועת אודיו נפרדת
                # שלו הייתה מכפילה את המוזיקה
                if any('פתיח צומת 20' in str((didx_new.get(s['material_id'], (None, {}))[1] or {}).get('path', ''))
                       for s in keep):
                    stats['other'].append('רצועת אודיו של הפתיח הוסרה (חוזר כווידאו)')
                    continue
            kept.append(t)

        # --- שלד: פתיח · פרק · מסך סגירה --------------------------------
        dspine = sorted(donor['tracks'][0]['segments'], key=lambda s: s['target_timerange']['start'])
        d_open = dspine[0]
        d_ep = next(s for s in dspine[1:] if 'רז' in str(didx[s['material_id']][1].get('path', '')))
        d_close = next(s for s in dspine if str(didx[s['material_id']][1].get('path', '')).endswith('.png'))

        s_open = clone(donor, didx, d_open, d, OPENER, OPENER_US)
        s_open['source_timerange'] = {'start': 0, 'duration': OPENER_US}
        s_open['target_timerange'] = {'start': 0, 'duration': OPENER_US}
        s_open['volume'] = OPENER_VOL

        s_ep = clone(donor, didx, d_ep, d, a.episode, ep_us)
        s_ep['source_timerange'] = {'start': 0, 'duration': ep_us}
        s_ep['target_timerange'] = {'start': ep_start, 'duration': ep_us}
        s_ep['volume'] = 1.0

        s_close = clone(donor, didx, d_close, d, CLOSER, CLOSER_US)
        s_close['source_timerange'] = {'start': 0, 'duration': CLOSER_US}
        s_close['target_timerange'] = {'start': ep_end, 'duration': CLOSER_US}
        s_close.setdefault('clip', {})['scale'] = {'x': CLOSER_SCALE, 'y': CLOSER_SCALE}

        spine = {'attribute': 4, 'flag': 0, 'id': capcut._new_id(), 'is_default_name': True,
                 'name': '', 'segments': [s_open, s_ep, s_close], 'type': 'video'}

        # --- באנר ---------------------------------------------------------
        d_ban = sorted(next(t for t in donor['tracks']
                            if any('באנר' in str(didx[s['material_id']][1].get('path', ''))
                                   for s in t['segments']))['segments'],
                       key=lambda s: s['target_timerange']['start'])[0]
        bans, at = [], ep_start + BANNER_FIRST
        while at + BANNER_US <= ep_end:
            b = clone(donor, didx, d_ban, d, BANNER, None)
            b['source_timerange'] = {'start': 0, 'duration': BANNER_US}
            b['target_timerange'] = {'start': at, 'duration': BANNER_US}
            bans.append(b); at += BANNER_EVERY
        ban_tr = {'attribute': 0, 'flag': 2, 'id': capcut._new_id(), 'is_default_name': True,
                  'name': '', 'segments': bans, 'type': 'video'}

        d['tracks'] = [spine] + kept + [ban_tr]
        ri = 0
        for t in d['tracks']:
            for s in t['segments']:
                s['render_index'] = max(s.get('render_index', 0), ri)
            ri += 1

        tmp = dst_dir / 'draft_info.tmp'
        tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
        json.loads(tmp.read_text())
        tmp.replace(dst_dir / 'draft_info.json')

        meta_id = capcut._new_id()
        mp = dst_dir / 'draft_meta_info.json'
        if mp.exists():
            meta = json.loads(mp.read_text()); now = int(time.time() * US)
            meta.update({'draft_id': meta_id, 'draft_name': new_name,
                         'draft_fold_path': str(dst_dir), 'tm_draft_create': now,
                         'tm_draft_modified': now, 'tm_duration': total})
            mp.write_text(json.dumps(meta, ensure_ascii=False))
        reels._registry_add(dst_dir, meta_id, total, a.source)
    except Exception:
        shutil.rmtree(dst_dir, ignore_errors=True)
        raise

    print(f'✅ «{new_name}» · {W}x{H} @ {FPS:g} · {total/US/60:.1f} דק׳')
    print(f'   שוטי מצלמה שאופסו למרכז: {stats["video"]} · קיפריימים של מסגור שהוסרו: {stats["kf"]}')
    if stats['overlay']:
        print(f'   ⚠️  {stats["overlay"]} שכבות-על (לוגו/מדבקה) נשמרו במיקום ה-9:16 שלהן — '
              f'צריך למקם אותן מחדש ידנית. אין להן מקבילה מדודה ב-16:9.')
    print(f'   כתוביות שהומרו: {stats["caption"]} · סגמנטים שנשמטו (רילס): {stats["dropped"]}')
    print(f'   באנרים: {len(bans)} · ראשון {bans[0]["target_timerange"]["start"]/US:.2f}s')
    for o in dict.fromkeys(stats['other']):
        print(f'   ⚠️  {o}')


if __name__ == '__main__':
    main()
