#!/bin/bash
# Download one reference video + metadata (+ platform captions on YouTube).
# usage: fetch.sh <url> <outdir>
#
# Instagram: public reels download logged-out (verified on a 53 s reel,
# 23.09.26). A cookies file is optional but recommended — it switches yt-dlp to
# the proper API path (duration and metadata come through; the embed fallback
# leaves duration empty). Drop one at ~/.config/video-breakdown/instagram-cookies.txt
# or set BREAKDOWN_COOKIES_FILE / BREAKDOWN_COOKIES_BROWSER.
set -euo pipefail

URL="${1:?usage: fetch.sh <url> <outdir>}"
OUT="${2:?usage: fetch.sh <url> <outdir>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The bundled macOS binary ships its own Python, so it can track yt-dlp's
# releases. The pip build is pinned to 2025.10 by the system Python 3.9 and its
# Instagram extractor is already stale — keep it only as a fallback.
YTDLP="$HERE/../bin/yt-dlp"
[ -x "$YTDLP" ] || YTDLP="$HOME/Library/Python/3.9/bin/yt-dlp"
FFPROBE="$HOME/ffmpeg-bin/ffprobe"
[ -x "$FFPROBE" ] || FFPROBE="$(command -v ffprobe)"
# ffmpeg is not on PATH on this Mac. Without it yt-dlp leaves DASH video and
# audio as two files and never produces source.mp4 (Instagram, and any YouTube
# format above the pre-muxed 360p).
FFDIR="$(dirname "$FFPROBE")"

# Reading Chrome's cookies directly needs the "Chrome Safe Storage" key from the
# Keychain, which a non-interactive shell is denied (0 of 3909 decrypted — seen
# 23.09.26). A cookies.txt exported from the browser sidesteps the Keychain.
DEFAULT_COOKIES="$HOME/.config/video-breakdown/instagram-cookies.txt"
COOKIES=()
if [ -n "${BREAKDOWN_COOKIES_BROWSER:-}" ]; then
  COOKIES=(--cookies-from-browser "$BREAKDOWN_COOKIES_BROWSER")
elif [ -n "${BREAKDOWN_COOKIES_FILE:-}" ]; then
  COOKIES=(--cookies "$BREAKDOWN_COOKIES_FILE")
elif [ -f "$DEFAULT_COOKIES" ]; then
  COOKIES=(--cookies "$DEFAULT_COOKIES")
fi

# YouTube forces SABR streaming on the default web client, which fails with
# "The page needs to be reloaded". android/ios/tv_embedded still serve plain
# HTTPS formats. Verified 23.09.26.
EXTRA=()
PLATFORM=other
case "$URL" in
  *youtube.com*|*youtu.be*) PLATFORM=youtube; EXTRA=(--extractor-args 'youtube:player_client=android,ios,tv_embedded') ;;
  *instagram.com*)          PLATFORM=instagram ;;
esac

mkdir -p "$OUT"

if [ -f "$OUT/source.mp4" ]; then
  echo "source.mp4 already present — skipping download"
else
  "$YTDLP" --ffmpeg-location "$FFDIR" ${EXTRA[@]+"${EXTRA[@]}"} ${COOKIES[@]+"${COOKIES[@]}"} \
    --no-progress --no-warnings \
    -f 'bv*+ba/b' -S 'res:1080,ext:mp4:m4a' \
    --merge-output-format mp4 \
    --write-info-json --no-playlist --restrict-filenames \
    -o "$OUT/source.%(ext)s" \
    "$URL" || true
  # yt-dlp's own ERROR line is the diagnosis; everything after this needs the file.
  if [ ! -f "$OUT/source.mp4" ]; then
    echo "!! download produced no source.mp4 — see the ERROR line above (rate limit, login, or a stale extractor: try bin/yt-dlp -U)" >&2
    exit 1
  fi
fi

# Captions are a bonus, never a blocker. A rate-limited subtitle track once
# aborted the whole fetch under `set -e`, so this runs separately and may fail.
if [ "$PLATFORM" = youtube ] && ! ls "$OUT"/source.*.vtt >/dev/null 2>&1; then
  "$YTDLP" --ffmpeg-location "$FFDIR" ${EXTRA[@]+"${EXTRA[@]}"} ${COOKIES[@]+"${COOKIES[@]}"} \
    --no-progress --no-warnings --skip-download \
    --write-auto-subs --write-subs --sub-langs 'he,en' --sub-format vtt \
    --no-playlist -o "$OUT/source.%(ext)s" \
    "$URL" || echo "note: no captions retrieved — transcript.py will report none"
fi

# The compact facts comparison.md needs, pulled out of the 20 KB info.json.
python3 - "$OUT" "$URL" "$PLATFORM" <<'PY'
import json, sys
from pathlib import Path
out, url, platform = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
info = json.loads((out / "source.info.json").read_text(encoding="utf-8"))
meta = {
    "url": url, "platform": platform,
    "title": info.get("title"), "creator": info.get("uploader") or info.get("channel"),
    "upload_date": info.get("upload_date"), "duration_s": info.get("duration"),
    "views": info.get("view_count"), "likes": info.get("like_count"),
    "comments": info.get("comment_count"),
    "resolution": f"{info.get('width')}x{info.get('height')}" if info.get("width") else None,
    "description": (info.get("description") or "")[:500] or None,
}
(out / "evidence").mkdir(exist_ok=True)
(out / "evidence" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: meta[k] for k in ("platform", "creator", "duration_s", "views", "likes")}, ensure_ascii=False))
PY

# The old "5 s + no audio = logged-out preview" guard was a false positive:
# two July-2026 Hormozi reels are genuinely 5 s and silent (identical formats
# logged-in and out; the API says duration 5.0). A silent clip is content, but
# the style book must know there is nothing to hear — record it in meta.json.
HAS_AUDIO=$("$FFPROBE" -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$OUT/source.mp4" | head -1)
DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$OUT/source.mp4")
python3 - "$OUT" "$DUR" "$HAS_AUDIO" <<'PY'
import json, sys
from pathlib import Path
out, dur, has_audio = Path(sys.argv[1]), float(sys.argv[2]), bool(sys.argv[3])
meta_path = out / "evidence" / "meta.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
meta["file_duration_s"] = round(dur, 2)
meta["audio_present"] = has_audio
if not has_audio:
    meta["note"] = "no audio stream — a silent clip; MUSIC/SFX/SPEECH are '—' by fact, not omission"
    print("note: no audio stream in source.mp4 — silent clip", file=sys.stderr)
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
PY

echo "--- files:"
ls -1 "$OUT"
