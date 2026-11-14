"""One pick → one reels_build.py plan (camera clock) + the spec bits the reel editor needs."""
import re
from .spec import speakers, graphics_on, logo_for


def reel_dir_name(pick: dict) -> str:
    title = re.sub(r"\s+", " ", re.sub(r"[/:\\]", " ", pick["title"])).strip()
    return f"{pick['n']:02d} - {title}"


def build_plan(pick: dict, spec: dict, ingest: dict, target_draft: str, donor_draft: str) -> dict:
    off = ingest["offsets"]["cam1"]
    mics = ingest["mics"] + [None, None]
    return {
        "target": target_draft,
        "donor": donor_draft,
        "shoots": {"s": {"cam1": ingest["cam1"], "cam2": ingest.get("cam2"),
                         "mic1": mics[0], "mic2": mics[1], "mic_offset": ingest["offsets"]["mic"]}},
        "reels": [{"n": pick["n"], "title": pick["title"], "shoot": "s",
                   "start": pick["start"] + off, "end": pick["end"] + off, "music": None}],
        "base_cam": 1,                      # reels_build: int(base_cam), 1|2
        "prefix": f"r{pick['n']:02d}",
        "bunker": {"font": spec["reels"]["font"],
                   "speaker_colors": {s["mic"]: s["color"] for s in speakers(spec)},
                   "graphics": graphics_on(spec),
                   "logo": logo_for(spec, "reels"),
                   "terms": list(spec.get("terms", [])),
                   "hook": ({"start": h["start"] + off, "end": h["end"] + off}
                            if (h := pick.get("hook")) else None),
                   "music": spec.get("reels", {}).get("music"),
                   "brand": (spec.get("landing_page") or {}).get("brand") if graphics_on(spec) else None},
    }
