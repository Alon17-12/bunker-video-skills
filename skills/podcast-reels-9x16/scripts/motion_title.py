# -*- coding: utf-8 -*-
"""Render a motion-graphics chapter title as a ProRes 4444 .mov with alpha (CapCut Mac reads it as a
transparent overlay) — the «מושקע» title Alon asked for on 0923 r8 after the PNG badges («ילדותי») and the
plain text supers («לא טובות»). Design, measured on the canvas:

    kicker   "01"  — Assistant-Regular, tracked, 70 % white, above the rule
    rule     3 px accent line (#d01020) that wipes out from the centre
    keyword  «עוגנים» — Heebo-ExtraBold, white, revealed by a soft wipe + 14 px rise, drop shadow
    in 0.55 s (ease-out) · hold · out 0.35 s (fade + 10 px rise). Nothing else — one device.

    python motion_title.py --out ccstudio-title-01.mov --kicker 01 --keyword עוגנים --dur 2.6 [--y 230] [--kw-size 104] [--accent d01020] [--fps 30]
    python motion_title.py --out ccstudio-counter-3.mov --kicker 3 --keyword טיפים --big-kicker --dur 2.3

Hebrew is drawn without raqm: a keyword is a single RTL run, so it is drawn reversed (text[::-1]); the
kicker is digits (LTR). `--big-kicker` puts the digit at keyword size in the accent colour (the «3» icon).
Requires ffmpeg with prores_ks (bin/ffmpeg has it). Frames are piped as RGBA PNG.
"""
import argparse, math, os, subprocess, sys
sys.path.insert(0, os.path.expanduser("~/bunker-video-engine/app")); import paths
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/")
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--kicker", default=""); ap.add_argument("--keyword", required=True); ap.add_argument("--dur", type=float, default=2.6)
ap.add_argument("--y", type=int, default=230, help="centre of the block in canvas px from the top"); ap.add_argument("--kw-size", type=int, default=104); ap.add_argument("--accent", default="d01020"); ap.add_argument("--fps", type=int, default=30); ap.add_argument("--big-kicker", action="store_true")
A = ap.parse_args(); W, H = 1080, 1920; ACC = tuple(int(A.accent[i:i + 2], 16) for i in (0, 2, 4))
kw_font = ImageFont.truetype(FONTS + "Heebo-ExtraBold.ttf", A.kw_size); kk_font = ImageFont.truetype(FONTS + ("Heebo-ExtraBold.ttf" if A.big_kicker else "Assistant-Regular.ttf"), A.kw_size if A.big_kicker else int(A.kw_size * 0.42))
kw = A.keyword[::-1]; kk = A.kicker
kw_w = kw_font.getlength(kw); kk_w = kk_font.getlength(kk) + (len(kk) - 1) * (0 if A.big_kicker else 6)
ease = lambda t: 1 - (1 - max(0.0, min(1.0, t))) ** 3
IN, OUT, RULE = 0.55, 0.35, 0.40; n = int(round(A.dur * A.fps)); cmd = [str(paths.FFMPEG), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(A.fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", A.out]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for f in range(n):
    t = f / A.fps; tin = ease(t / IN); tout = ease((t - (A.dur - OUT)) / OUT) if t > A.dur - OUT else 0.0
    alpha = (1 - tout); rise = 14 * (1 - tin) - 10 * tout
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(layer)
    if A.big_kicker:
        # «3 טיפים»: accent digit + white word on one baseline, digit on the right (RTL reading: digit first)
        gap = 22; total = kw_w + gap + kk_w; x0 = (W - total) / 2; y = A.y - A.kw_size * 0.55 + rise
        # keyword on the left of the digit visually (Hebrew reads right→left: «3» then «טיפים»)
        dr.text((x0, y), kw, font=kw_font, fill=(255, 255, 255, int(255 * alpha * tin)))
        dr.text((x0 + kw_w + gap, y), kk, font=kk_font, fill=ACC + (int(255 * alpha * ease(t / (IN * 0.7))),))
        # reveal mask: soft wipe right→left over the whole group
        mask = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mask); edge = x0 + total - tin * (total + 120); md.rectangle([edge, 0, W, H], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(28)); layer.putalpha(Image.fromarray(__import__("numpy").minimum(__import__("numpy").array(layer.split()[3]), __import__("numpy").array(mask))))
    else:
        rule_len = 220 * ease(t / RULE) * (1 - tout * 0.0); yr = A.y + rise
        # kicker (tracked digits) above the rule
        kx = (W - kk_w) / 2; ky = yr - int(A.kw_size * 0.42) - 26
        for ch in kk:
            dr.text((kx, ky), ch, font=kk_font, fill=(255, 255, 255, int(255 * 0.72 * alpha * ease(t / (IN * 0.6))))); kx += kk_font.getlength(ch) + 6
        if rule_len > 0: dr.rectangle([W / 2 - rule_len / 2, yr - 1.5, W / 2 + rule_len / 2, yr + 1.5], fill=ACC + (int(255 * alpha),))
        # keyword below the rule, soft wipe right→left + rise
        kwy = yr + 18 + rise * 0.6; kwx = (W - kw_w) / 2
        klayer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); kd = ImageDraw.Draw(klayer); kd.text((kwx, kwy), kw, font=kw_font, fill=(255, 255, 255, int(255 * alpha)))
        mask = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mask); edge = kwx + kw_w - ease((t - 0.12) / IN) * (kw_w + 140); md.rectangle([edge, 0, W, H], fill=255); mask = mask.filter(ImageFilter.GaussianBlur(24))
        import numpy as np
        klayer.putalpha(Image.fromarray(np.minimum(np.array(klayer.split()[3]), np.array(mask)))); layer = Image.alpha_composite(layer, klayer)
    # a soft dark scrim behind the block (creator grammar: text sits on a scrim, never raw over a bright plate — r8: «02» vanished over stage spotlights), then a drop shadow
    bbox = layer.getbbox()
    if bbox:
        sc = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sc); x0, y0, x1, y1 = bbox
        sd.rounded_rectangle([x0 - 90, y0 - 60, x1 + 90, y1 + 60], radius=80, fill=(0, 0, 0, int(115 * alpha * min(1.0, ease(t / 0.35)))))
        im = Image.alpha_composite(im, sc.filter(ImageFilter.GaussianBlur(55)))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.paste((0, 0, 0, int(150 * alpha)), (0, 0, W, H), layer.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(10))
    im = Image.alpha_composite(im, sh.transform(sh.size, Image.AFFINE, (1, 0, -3, 0, 1, -5))); im = Image.alpha_composite(im, layer)
    im.save(proc.stdin, format="PNG")
proc.stdin.close(); proc.wait(); print(f"{A.out}: {n} frames @ {A.fps} fps, {A.dur}s, prores 4444 alpha, rc {proc.returncode}")
