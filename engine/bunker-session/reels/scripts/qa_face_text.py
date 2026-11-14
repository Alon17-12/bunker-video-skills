"""Every caption against the faces under it, on the draft itself (PROJ env)."""
import json, os, sys, importlib.util
import numpy as np, cv2
from PIL import ImageFont
spec = importlib.util.spec_from_file_location("pv", os.path.expanduser("~/bunker-video-engine/bunker-session/reels/scripts/capcut_preview.py"))
pv = importlib.util.module_from_spec(spec); spec.loader.exec_module(pv)
d, M, st, en = pv.d, pv.M, pv.st, pv.en
F = ImageFont.truetype(os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/opensanshebrew-bold-webfont.ttf"), 72)
FR = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PR = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
caps = sorted([s for t in d["tracks"] if t.get("name") == "כתוביות" for s in t["segments"]], key=st)
PITCH = 100   # px per row at 1920 (Open Sans ~72 px + line spacing 0.06), conservative
hits = []
for i, c in enumerate(caps):
    m = json.loads(M[c["material_id"]][1]["content"]); rows = m["text"].split("\n")
    cy = 960 - c["clip"]["transform"]["y"] * 960
    h = len(rows) * PITCH; w = max(F.getlength(r) for r in rows) + 30
    box = (540 - w / 2, cy - h / 2, 540 + w / 2, cy + h / 2)
    worst = 0
    for t in (st(c) / 1e6 + 0.08, (st(c) + en(c)) / 2e6, en(c) / 1e6 - 0.08):
        im, lab = pv.frame(t)
        g = cv2.cvtColor(np.array(im.convert("RGB").resize((540, 960))), cv2.COLOR_RGB2GRAY)
        fs = list(FR.detectMultiScale(g, 1.1, 5, minSize=(40, 40))) + list(PR.detectMultiScale(g, 1.1, 5, minSize=(40, 40)))
        for (x, y, fw, fh) in fs:
            x, y, fw, fh = x * 2, y * 2, fw * 2, fh * 2
            fb = (x, y - 0.25 * fh, x + fw, y + 1.25 * fh)          # hair to chin
            ov = max(0, min(box[2], fb[2]) - max(box[0], fb[0])) * max(0, min(box[3], fb[3]) - max(box[1], fb[1]))
            worst = max(worst, ov / (fw * fh * 1.5))
            if ov: lastlab = (round(t, 2), lab, [int(v) for v in fb])
    if worst > 0:
        hits.append((round(worst, 2), round(st(c) / 1e6, 2), m["text"].replace("\n", " / "), round(cy), lastlab))
    if i % 50 == 0: print(i, len(hits), flush=True)
hits.sort(reverse=True)
json.dump(hits, open(sys.argv[1], "w"), ensure_ascii=False, indent=0)
print("captions", len(caps), "touching a face", len(hits))
for h in hits[:40]: print(h)
