#!/usr/bin/env python3
"""What a CapCut project shows at timeline t — every video layer bottom→top (cameras with their scale/position, splits,
transparent .mov overlays incl. HEVC-with-alpha, cut-outs), captions drawn as boxes with their text. A check, not a render:
keyframes are evaluated at their first value, the grade is not applied.

    draft_frame.py "<project>" out.jpg t1,t2,… [--scale 0.4] [--no-text]   (--no-text: pictures only, e.g. for draft_cover.jpg)
"""
import json, re, subprocess, sys, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path.home() / "bunker-video-engine/app"))
import capcut  # noqa: E402

FF = str(Path.home() / "ffmpeg-bin/ffmpeg"); US = 1_000_000
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def grab(path, t, alpha):
    hevc = alpha and path.endswith(".mov") and b"hevc" in subprocess.run([FF[:-len("ffmpeg")] + "ffprobe", "-v", "error", "-select_streams", "v:0",
                                                                          "-show_entries", "stream=codec_name", "-of", "csv=p=0", path], capture_output=True).stdout
    args = [FF, "-v", "error"] + (["-c:v", "hevc"] if hevc else []) + ["-ss", f"{max(0, t):.3f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]
    raw = subprocess.run(args, capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGBA") if raw else None


def main():
    proj, out, ts = sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")]
    sc = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 0.4
    P = capcut.DRAFTS_DIR / proj
    d = json.loads((P / "draft_info.json").read_text())
    W, H = d["canvas_config"]["width"], d["canvas_config"]["height"]
    mats = {m["id"]: m for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
    tiles = []
    for t in ts:
        T = int(t * US)
        can = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for tr in d["tracks"]:
            if tr["type"] != "video":
                continue
            for s in tr["segments"]:
                a = s["target_timerange"]["start"]
                if not (a <= T < a + s["target_timerange"]["duration"]) or s["clip"]["alpha"] < 0.5:
                    continue
                m = mats[s["material_id"]]
                path = re.sub(r"##_draftpath_placeholder_[0-9A-F-]+_##", str(P), m.get("path", ""))
                if m.get("type") == "photo":
                    im = Image.open(path).convert("RGBA") if Path(path).exists() else None
                else:
                    im = grab(path, (s["source_timerange"]["start"] + T - a) / US, True)
                if im is None:
                    continue
                k = s["clip"]["scale"]["x"]; tx, ty = s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
                fit = min(W / im.width, H / im.height) * k
                im = im.resize((max(1, int(im.width * fit)), max(1, int(im.height * fit))))
                cx, cy = W / 2 + tx * W / 2, H / 2 - ty * H / 2
                can.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)) if True else (0, 0))
        dr = ImageDraw.Draw(can)
        for tr in d["tracks"]:
            if tr["type"] != "text" or "--no-text" in sys.argv:
                continue
            for s in tr["segments"]:
                a = s["target_timerange"]["start"]
                if a <= T < a + s["target_timerange"]["duration"] and s["clip"].get("alpha", 1) > 0.5:
                    txt = json.loads(mats[s["material_id"]]["content"])["text"]
                    y = H / 2 - s["clip"]["transform"]["y"] * H / 2
                    f = ImageFont.truetype(FONT, int(H * (0.035 if W > H else 0.03)))
                    dr.text((W / 2, y), txt[::-1] if re.search("[א-ת]", txt) else txt, font=f, anchor="mm", fill="white", stroke_width=4, stroke_fill="black")
        if "--no-text" not in sys.argv:
            dr.text((20, 20), f"{t:.2f}", font=ImageFont.truetype(FONT, 50), fill="yellow")
        tiles.append(can.convert("RGB").resize((int(W * sc), int(H * sc))))
    G = Image.new("RGB", (sum(x.width for x in tiles), tiles[0].height))
    x = 0
    for im in tiles:
        G.paste(im, (x, 0)); x += im.width
    G.save(out); print(out)


if __name__ == "__main__":
    main()
