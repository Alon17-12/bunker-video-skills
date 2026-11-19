#!/bin/zsh
# כלי העריכה של הבונקר — התקנה חד-פעמית (אפשר להריץ שוב בבטחה)
# מתקין: הסקילים ל-Claude Code, מנוע העריכה (~/bunker-video-engine), ffmpeg, מודל תמלול עברית, מודל זיהוי פנים, Remotion.
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$HOME/bunker-video-engine"
SKILLS="$HOME/.claude/skills"
FORCE=0; [[ "$1" == "--force" ]] && FORCE=1

[[ "$(uname -s)" == "Darwin" ]] || { echo "✗ זה המתקין למק. ב-Windows: powershell -ExecutionPolicy Bypass -File .\\install.ps1"; exit 1; }
[[ "$(uname -m)" == "arm64" ]] || echo "⚠ המחשב לא Apple Silicon — ffmpeg שיורד כאן הוא arm64; התקינו ffmpeg בעצמכם."

echo "▶ 1/7 סקילים → $SKILLS"
mkdir -p "$SKILLS"
for d in "$REPO"/skills/*/; do
  n=$(basename "$d")
  if [[ -e "$SKILLS/$n" && $FORCE -eq 0 ]]; then
    echo "  • $n כבר קיים — מדלג (להחלפה: ./install.sh --force; הישן נשמר כגיבוי)"; continue
  fi
  [[ -e "$SKILLS/$n" ]] && mv "$SKILLS/$n" "$SKILLS/$n.backup-$(date +%Y%m%d-%H%M%S)"
  cp -R "$d" "$SKILLS/$n"; echo "  ✓ $n"
done

echo "▶ 2/7 מנוע העריכה → $ENGINE"
mkdir -p "$ENGINE/bin" "$ENGINE/models"
rsync -a "$REPO/engine/app/" "$ENGINE/app/"
rsync -a --exclude node_modules "$REPO/engine/bunker-session/" "$ENGINE/bunker-session/"
cp "$REPO/engine/doctor.py" "$ENGINE/doctor.py"
ln -sfn "$SKILLS/bunker-editing" "$ENGINE/bunker-session/skill"
[[ -f "$ENGINE/config.json" ]] || echo '{"styles": [], "color_presets": [], "show_presets": []}' > "$ENGINE/config.json"

echo "▶ 3/7 Python 3.12 + ספריות (uv)"
if ! command -v uv >/dev/null && [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
[[ -d "$ENGINE/.venv" ]] || uv venv --python 3.12 "$ENGINE/.venv"
uv pip install --python "$ENGINE/.venv/bin/python" -r "$REPO/requirements.txt"
uv tool install yt-dlp >/dev/null 2>&1 || true   # לסקיל ניתוח הסרטונים

echo "▶ 4/7 ffmpeg + ffprobe"
for t in ffmpeg ffprobe; do
  if [[ ! -x "$ENGINE/bin/$t" ]]; then
    curl -LsS -o "/tmp/$t.zip" "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/$t.zip"
    unzip -o "/tmp/$t.zip" -d "$ENGINE/bin" >/dev/null && rm "/tmp/$t.zip" && chmod +x "$ENGINE/bin/$t"
  fi
done
# הסקריפטים מחפשים את ffmpeg ב-~/ffmpeg-bin
[[ -e "$HOME/ffmpeg-bin" ]] || ln -s "$ENGINE/bin" "$HOME/ffmpeg-bin"

echo "▶ 5/7 מודל תמלול עברית (ivrit.ai, ‎~1.6GB, פעם אחת)"
if [[ ! -f "$ENGINE/models/ivrit-whisper-large-v3-turbo-ct2/model.bin" ]]; then
  "$ENGINE/.venv/bin/python" -c "
from huggingface_hub import snapshot_download
snapshot_download('ivrit-ai/whisper-large-v3-turbo-ct2', local_dir='$ENGINE/models/ivrit-whisper-large-v3-turbo-ct2')"
fi

echo "▶ 6/7 מודל זיהוי פנים (YuNet)"
[[ -f "$ENGINE/models/face_detection_yunet_2023mar.onnx" ]] || curl -LsS -o "$ENGINE/models/face_detection_yunet_2023mar.onnx" \
  "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

echo "▶ 7/7 Remotion (לרילס עם גרפיקה)"
if command -v npm >/dev/null; then
  (cd "$ENGINE/bunker-session/reels" && npm install --silent)
else
  echo "  ⚠ אין Node.js — מדלג. להתקנה: https://nodejs.org ואז להריץ שוב."
fi

mkdir -p "$HOME/VideoAssets/music" "$HOME/VideoAssets/סאונד/SFX"
echo; echo "▶ בדיקת מוכנות"
"$ENGINE/.venv/bin/python" "$ENGINE/doctor.py" || true
echo
echo "✓ מוכן. פותחים שיחה חדשה ב-Claude Code ומבקשים, למשל: «תערוך רילס מהפרק בפרויקט X ב-CapCut»."
