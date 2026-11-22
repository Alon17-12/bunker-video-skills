"""A Bunker «רז» as an editable CapCut project: cam 1 = spine, cam 2 on the «ניתוב» track wherever its mic leads,
dialogue from the mics, the Bunker LUT (adjust layer cloned from «14.08.26 - לקוח V 1 - רז»), 0.5 s fades.
Reuses bunker-editing/scripts/build_session_episode.py (template «יונתן אורח W צומת 20 פרק», no logo / names).

  build_raz_project.py <route.json> <cam1> <cam2> <dialogue.wav (Live-Mix clock)> <in_live> <out_live> <name>
CapCut must be closed.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/bunker-video-engine/app'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))      # bunker-editing/scripts
import capcut, reels
import build_session_episode as bse

US = 1_000_000
FF = os.path.expanduser('~/ffmpeg-bin/ffmpeg'); FP = os.path.expanduser('~/ffmpeg-bin/ffprobe')

route, cam1, cam2, dia, t_in, t_out, name = sys.argv[1:8]
r = json.load(open(route))
lag = sum(x[0] for x in r['clocks']['cam1']) / len(r['clocks']['cam1'])          # cam_t = live_t + lag
cin = round((float(t_in) + lag) * 30) / 30; cout = round((float(t_out) + lag) * 30) / 30
tin, tout = int(round(cin * US)), int(round(cout * US))
e_dur = (tout - tin) / US
src_dur = int(round(float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', cam1],
                                        capture_output=True, text=True).stdout) * US))
patches = []
for c, a, b in r['shots']:
    if c != 2: continue
    a, b = max(a, cin), min(b, cout)
    if b - a >= 0.5: patches.append([2, round(a * 30) / 30, round(b * 30) / 30])

if capcut._capcut_pid() is not None:
    sys.exit('⛔ CapCut פתוח')
work = Path(route).parent
dia_local = work / f'{name} - דיאלוג.m4a'        # AAC: the draft copy lives on the (nearly full) internal disk
subprocess.run([FF, '-v', 'error', '-y', '-ss', f'{cin - lag:.6f}', '-t', f'{e_dur:.6f}', '-i', dia,
                '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', str(dia_local)], check=True)

color = capcut.extract_color(bse.COLOR_FROM)
new_name = reels._unique_name(name)
dst = capcut.DRAFTS_DIR / new_name
reels._copy_draft_folder(capcut.DRAFTS_DIR / bse.TEMPLATE, dst)
try:
    d = json.loads((dst / 'draft_info.json').read_text())
    e_us, _ = bse.build(d, Path(cam1), src_dur, tin, tout, False)
    capcut._atomic_write(dst, d)
    meta_id = capcut._new_id(); mp = dst / 'draft_meta_info.json'
    if mp.exists():
        meta = json.loads(mp.read_text()); now = int(time.time() * US)
        meta.update({'draft_id': meta_id, 'draft_name': new_name, 'draft_fold_path': str(dst),
                     'tm_draft_create': now, 'tm_draft_modified': now, 'tm_duration': e_us})
        mp.write_text(json.dumps(meta, ensure_ascii=False))
    reels._registry_add(dst, meta_id, e_us, bse.TEMPLATE)
    capcut.add_audio(new_name, str(dia_local), 'דיאלוג', at_us=0, duration_us=e_us, volume=1.0, kind='sfx')
    n_patch = bse.add_routing_patches(new_name, patches, tin, {1: cam1, 2: cam2})
    n_edges = bse.single_layer_fades(new_name)
    capcut.apply_color(new_name, color)
    capcut.apply_fades(new_name, bse.FADE_US // 1000)
    bse.grade_footage_only(new_name)
except Exception:
    shutil.rmtree(dst, ignore_errors=True)
    raise
out = {'draft': new_name, 'duration_s': round(e_us / US, 2), 'cam_in': cin, 'cam_out': cout, 'cam_lag': round(lag, 4),
       'routing_patches': n_patch, 'single_layer_fade_edges': n_edges}
(work / 'פרויקט.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
print('✅', json.dumps(out, ensure_ascii=False))
