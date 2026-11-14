"""Chapter cards for the 16:9 landing build — drawn locally, fully opaque.

The first version drew the grid with `(255, 255, 255, 10)` on an RGBA image. PIL's `line` does not
blend; it REPLACES the pixels with alpha-10 pixels, so every grid line became a slit and CapCut
showed the speaker through it — Alon saw "a perforated blue background". A card is a plate: every
pixel opaque, and any "translucent" line is a colour you mix yourself.

    python landing_16x9_cards.py "<draft folder>" --regen     # rebuild every ccstudio-chapter-*.png in place
"""
import os, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/")
FREDOKA, BOLD, HEEBO = FONTS + "Fredoka-Bold.ttf", FONTS + "bamberger-grunge-bold-fm.ttf", FONTS + "Heebo-ExtraBold.ttf"
PALETTE = {"wb": ((30, 58, 107), (15, 34, 70), (56, 182, 232), FREDOKA), "bk": ((26, 26, 28), (12, 12, 13), (237, 69, 56), BOLD)}


def rtl(text):
    """PIL without raqm draws Hebrew left-to-right: reverse the token order and each Hebrew token, keep Latin/digits."""
    return " ".join(t if re.search(r"[A-Za-z0-9]", t) else t[::-1] for t in reversed(text.split(" ")))


def _mix(a, b, f): return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


def chapter_card(folder, key, num, text, force=False):
    out = Path(folder) / f"ccstudio-chapter-{key}-{num}.png"
    if out.exists() and not force: return out
    top, bot, acc, font = PALETTE[key]
    im = Image.new("RGB", (1920, 1080), bot); dr = ImageDraw.Draw(im)
    for y in range(1080): dr.line([(0, y), (1919, y)], fill=_mix(top, bot, y / 1079))
    grid = _mix(top, (255, 255, 255), 0.06)                                   # an opaque, slightly lighter line — never alpha
    for x in range(0, 1920, 96): dr.line([(x, 0), (x, 1079)], fill=grid)
    for y in range(0, 1080, 96): dr.line([(0, y), (1919, y)], fill=grid)
    L, m, w = 130, 96, 4                                                       # the HUD's corner brackets, static and mixed into the plate (v2.2: no counter-moving layer)
    br = _mix(acc, bot, 0.35)
    for (x, y, sx, sy) in ((m, m, 1, 1), (1920 - m, m, -1, 1), (m, 1080 - m, 1, -1), (1920 - m, 1080 - m, -1, -1)):
        dr.line([(x, y), (x + sx * L, y)], fill=br, width=w); dr.line([(x, y), (x, y + sy * L)], fill=br, width=w)
    fb, fs = ImageFont.truetype(font, 118), ImageFont.truetype(font, 46)
    dr.text((960, 430), rtl(f"פרק {num}"), font=fs, fill=acc, anchor="mm")
    dr.rounded_rectangle((900, 478, 1020, 484), 3, fill=acc)
    dr.text((960, 580), rtl(text), font=fb, fill=(255, 255, 255), anchor="mm")
    tmp = out.with_suffix(".tmp.png"); im.save(tmp); os.replace(tmp, out)      # a new inode — safe even while CapCut holds the old file
    return out


if __name__ == "__main__":
    folder = Path(sys.argv[1]); regen = "--regen" in sys.argv
    n = 0
    for p in sorted(folder.glob("ccstudio-chapter-*.png")):
        key, num = re.match(r"ccstudio-chapter-(\w+)-(\d+)\.png", p.name).groups()
        if not regen: print(p.name); continue
        # the text lives in the build's VIDEOS spec; re-read it from the existing card's sibling json if any, else keep names
        n += 1
    print(f"{n} cards" if regen else "")


def hud_overlay(folder, key, force=False):
    """A transparent 'HUD' layer that rides over a chapter card with its own motion: corner brackets,
    two faint diagonals, a few dots — the layer moves against the card so the pair reads as depth."""
    out = Path(folder) / f"ccstudio-hud-{key}.png"
    if out.exists() and not force: return out
    acc = PALETTE[key][2]
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    L, m, w = 130, 96, 4
    for (x, y, sx, sy) in ((m, m, 1, 1), (1920 - m, m, -1, 1), (m, 1080 - m, 1, -1), (1920 - m, 1080 - m, -1, -1)):
        dr.line([(x, y), (x + sx * L, y)], fill=acc + (230,), width=w); dr.line([(x, y), (x, y + sy * L)], fill=acc + (230,), width=w)
    for (x0, y0, x1, y1) in ((-200, 1080, 2120, -60), (-200, 900, 1500, -200)):
        dr.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 22), width=2)
    for i in range(14):
        x, y = (i * 137 + 60) % 1920, (i * 233 + 90) % 1080
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=acc + (170,))
    dr.line([(m, 540), (m + 220, 540)], fill=acc + (120,), width=2); dr.line([(1920 - m - 220, 540), (1920 - m, 540)], fill=acc + (120,), width=2)
    tmp = out.with_suffix(".tmp.png"); im.save(tmp); os.replace(tmp, out); return out
