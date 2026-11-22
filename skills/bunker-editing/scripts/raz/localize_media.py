"""Put a «רז» draft's camera files INSIDE the draft folder so the project opens working — no Import / Relink by hand.
  localize_media.py <draft name> <cam1> <cam2> [--work <dir on the SSD>] [--mode auto|copy|h264]

Why (22.11.2026, מנחה R2): CapCut for Mac is sandboxed. A path written into the draft by a script that points at
an external SSD opens as «File not accessible» / «Unsupported Media» — only files Alon picked in CapCut's own dialog
are readable. Alon will not do the Import step («תצור פרויקט עם הקבצים הנכונים»), so the media goes into
<draft>/ccstudio-media/ and the materials point there.

  copy  — the original files (full quality). Needs (cam1 + cam2) × 1.15 free on the internal disk.
  h264  — full-length copies, same frames and clock: h264_videotoolbox 6 Mbps (SSIM 0.964 vs the 45 Mbps camera
          file; ~2.7 GB per camera-hour). Encoded on the SSD (--work), then copied in.
          (avconvert PresetHEVC1920x1080 is better — SSIM 0.977 — but 8.8 Mbps; ffmpeg hevc_videotoolbox fails here.)
  auto  — copy when it fits, otherwise h264 when it fits, otherwise stop and say how much space is missing.
Also cleans the media panel (draft_meta_info.json) to the files the timeline uses — a draft cloned from a template
otherwise lists the template's media («Media lost», other clients' SRTs, compound clips).
CapCut must be closed. Backs up draft_info.json / draft_meta_info.json as *.pre-localmedia.json.
"""
import argparse, copy, json, os, platform, shutil, subprocess, sys, time, uuid
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
import capcut

FF = os.path.expanduser('~/ffmpeg-bin/ffmpeg'); FP = os.path.expanduser('~/ffmpeg-bin/ffprobe')
GB = 1024 ** 3


def probe(p, what):
    return subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', what, '-of', 'csv=p=0', str(p)],
                          capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('draft'); ap.add_argument('cam1'); ap.add_argument('cam2')
    ap.add_argument('--work'); ap.add_argument('--mode', default='auto', choices=['auto', 'copy', 'h264'])
    a = ap.parse_args()
    if capcut._capcut_pid() is not None:
        sys.exit('⛔ CapCut פתוח — לסגור לגמרי ולהריץ שוב')
    D = capcut.DRAFTS_DIR / a.draft
    cams = {1: Path(a.cam1), 2: Path(a.cam2)}
    free = shutil.disk_usage(D).free
    orig = sum(p.stat().st_size for p in cams.values())
    dur = float(probe(cams[1], 'format=duration') or 0) or float(subprocess.run(
        [FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(cams[1])], capture_output=True, text=True).stdout)
    h264_size = 2 * dur * 6.2e6 / 8
    mode = a.mode
    if mode == 'auto':
        mode = 'copy' if orig * 1.15 < free else 'h264' if h264_size * 1.3 < free else None
    if mode is None:
        sys.exit(f'⛔ אין מקום בדיסק הפנימי: פנוי {free/GB:.1f}GB, צריך {h264_size*1.3/GB:.1f}GB לעותקים (או {orig*1.15/GB:.1f}GB למקור). '
                 f'לפנות מקום (מטמון כרום/ספוטיפיי, לרוקן פח — באישור אלון) ולהריץ שוב.')
    media = D / 'ccstudio-media'; media.mkdir(exist_ok=True)
    stem = a.draft.replace(' - רז', '')
    newp = {}
    for c, src in cams.items():
        dst = media / f'{stem} - מצלמה {c}.mp4'
        if mode == 'copy':
            if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                shutil.copyfile(src, dst)
        else:
            work = Path(a.work or src.parent); tmp = work / dst.name
            if not tmp.exists():
                enc = ['-c:v', 'h264_videotoolbox', '-profile:v', 'high', '-b:v', '6M', '-maxrate', '9M'] if platform.system() == 'Darwin' \
                    else ['-c:v', 'libx264', '-preset', 'fast', '-crf', '20']
                subprocess.run([FF, '-v', 'error', '-y', '-i', str(src), '-an', *enc, '-g', '30', '-colorspace', 'bt709',
                                '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-movflags', '+faststart', str(tmp)], check=True)
            if probe(tmp, 'stream=nb_frames') != probe(src, 'stream=nb_frames'):
                sys.exit(f'⛔ מספר הפריימים בעותק שונה מהמקור: {tmp}')
            shutil.copyfile(tmp, dst)
        newp[str(src)] = str(dst)
    shutil.copy2(D / 'draft_info.json', D / 'draft_info.pre-localmedia.json')
    d = json.loads((D / 'draft_info.json').read_text())
    n = 0
    for m in d['materials'].get('videos', []):
        if m.get('path') in newp:
            m['path'] = newp[m['path']]; m['material_name'] = Path(m['path']).name; n += 1
    capcut._atomic_write(D, d)
    # media panel = only the two cameras
    mp = D / 'draft_meta_info.json'
    meta = json.loads(mp.read_text()); shutil.copy2(mp, D / 'draft_meta_info.pre-localmedia.json')
    donor = next((x for g in meta.get('draft_materials', []) if g.get('type') == 0 for x in g.get('value', []) if x.get('metetype') == 'video'), None)
    vals, now = [], int(time.time())
    for p in newp.values():
        e = copy.deepcopy(donor) if donor else {'metetype': 'video', 'type': 0, 'width': 1920, 'height': 1080, 'item_source': 1, 'md5': ''}
        us = int(round(float(probe(p, 'format=duration') or dur) * 1e6))
        e.update({'id': str(uuid.uuid4()), 'file_Path': p, 'extra_info': Path(p).name, 'duration': us,
                  'roughcut_time_range': {'duration': us, 'start': 0}, 'sub_time_range': {'duration': -1, 'start': -1},
                  'create_time': now, 'import_time': now, 'import_time_ms': now * 1_000_000})
        vals.append(e)
    for g in meta.get('draft_materials', []):
        g['value'] = vals if g.get('type') == 0 else []
    mp.write_text(json.dumps(meta, ensure_ascii=False))
    print(f'✅ {mode}: {n} חומרים הופנו לתוך הטיוטה · פנוי עכשיו {shutil.disk_usage(D).free/GB:.1f}GB')


if __name__ == '__main__':
    main()
