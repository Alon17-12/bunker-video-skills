# Bunker video tools - one-time install for Windows (safe to run again).
# Run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1          (add -Force to replace installed skills)
# Installs: the Claude Code skills, the editing engine (~\bunker-video-engine), ffmpeg, the Hebrew
# transcription model, the face model, Remotion, the house fonts, and the shims that let the Mac
# commands in the skills (~/bunker-video-engine/.venv/bin/python, ~/ffmpeg-bin/ffmpeg) run unchanged.
param([switch]$Force)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is 10x slower with the progress bar
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Repo   = $PSScriptRoot
$Home_  = $env:USERPROFILE
$Engine = Join-Path $Home_ "bunker-video-engine"
$Skills = Join-Path $Home_ ".claude\skills"
$Py     = Join-Path $Engine ".venv\Scripts\python.exe"

function Step($t) { Write-Host "`n> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "  OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "  !!  $t" -ForegroundColor Yellow }
function Junction($link, $target) {
    if (Test-Path $link) {
        $item = Get-Item $link -Force
        if ($item.LinkType -eq "Junction" -or $item.LinkType -eq "SymbolicLink") { return }
        Warn "$link exists and is not a link - leaving it"; return
    }
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
}

if ($env:OS -ne "Windows_NT") { throw "This installer is for Windows. On a Mac run ./install.sh" }
if (-not [Environment]::Is64BitOperatingSystem) { throw "64-bit Windows is required." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Warn "Git for Windows is missing (Claude Code needs it for Git Bash): https://git-scm.com/download/win"
}

Step "1/9 Skills -> $Skills"
New-Item -ItemType Directory -Force -Path $Skills | Out-Null
foreach ($d in Get-ChildItem (Join-Path $Repo "skills") -Directory) {
    $dst = Join-Path $Skills $d.Name
    if ((Test-Path $dst) -and -not $Force) { Ok "$($d.Name) already installed - skipped (use -Force to replace; the old copy is kept as a backup)"; continue }
    if (Test-Path $dst) { Rename-Item $dst ("$($d.Name).backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
    Copy-Item $d.FullName $dst -Recurse
    Ok $d.Name
}

Step "2/9 Engine -> $Engine"
New-Item -ItemType Directory -Force -Path (Join-Path $Engine "bin"), (Join-Path $Engine "models") | Out-Null
robocopy (Join-Path $Repo "engine\app") (Join-Path $Engine "app") /E /NFL /NDL /NJH /NJS /NP | Out-Null
robocopy (Join-Path $Repo "engine\bunker-session") (Join-Path $Engine "bunker-session") /E /XD node_modules /NFL /NDL /NJH /NJS /NP | Out-Null
Copy-Item (Join-Path $Repo "engine\doctor.py") $Engine -Force
Junction (Join-Path $Engine "bunker-session\skill") (Join-Path $Skills "bunker-editing")
$cfg = Join-Path $Engine "config.json"
if (-not (Test-Path $cfg)) { [IO.File]::WriteAllText($cfg, '{"styles": [], "color_presets": [], "show_presets": []}') }
Ok "engine copied"

Step "3/9 Python 3.12 + libraries (uv)"
$env:Path = "$Home_\.local\bin;$env:Path"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$Home_\.local\bin;$env:Path"
}
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Engine ".venv") }
uv pip install --python $Py -r (Join-Path $Repo "requirements.txt")
try { uv tool install yt-dlp 2>$null | Out-Null } catch { }
# the skills call ~/bunker-video-engine/.venv/bin/python (Mac layout) -> point bin at Scripts
Junction (Join-Path $Engine ".venv\bin") (Join-Path $Engine ".venv\Scripts")
Ok "python ready"

Step "4/9 ffmpeg + ffprobe"
$ff = Join-Path $Engine "bin\ffmpeg.exe"
if (-not (Test-Path $ff)) {
    $zip = Join-Path $env:TEMP "ffmpeg-win64.zip"; $tmp = Join-Path $env:TEMP "ffmpeg-win64"
    Invoke-WebRequest "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile $zip
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive $zip $tmp
    Get-ChildItem $tmp -Recurse -Include ffmpeg.exe, ffprobe.exe | Copy-Item -Destination (Join-Path $Engine "bin")
    Remove-Item $zip, $tmp -Recurse -Force
}
# the scripts look for ffmpeg in ~/ffmpeg-bin
Junction (Join-Path $Home_ "ffmpeg-bin") (Join-Path $Engine "bin")
Ok "ffmpeg ready"

Step "5/9 Hebrew transcription model (ivrit.ai, ~1.6GB, once)"
$model = Join-Path $Engine "models\ivrit-whisper-large-v3-turbo-ct2"
if (-not (Test-Path (Join-Path $model "model.bin"))) {
    & $Py -c "from huggingface_hub import snapshot_download; snapshot_download('ivrit-ai/whisper-large-v3-turbo-ct2', local_dir=r'$model')"
}
Ok "model ready"

Step "6/9 Face detection model (YuNet)"
$yunet = Join-Path $Engine "models\face_detection_yunet_2023mar.onnx"
if (-not (Test-Path $yunet)) {
    Invoke-WebRequest "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile $yunet
}
Ok "face model ready"

Step "7/9 Remotion (reels with graphics)"
if (-not (Get-Command npm -ErrorAction SilentlyContinue) -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    winget install --id OpenJS.NodeJS.LTS -e --silent --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Push-Location (Join-Path $Engine "bunker-session\reels"); npm install --silent; Pop-Location
    Ok "remotion ready"
} else { Warn "No Node.js - skipped. Install https://nodejs.org and run this again." }

Step "8/9 House fonts (Heebo, Assistant, Fredoka)"
# scripts load fonts from the Mac CapCut font folder path -> create the same path under the user folder
$fontDir = Join-Path $Home_ "Library\Containers\com.lemon.lvoverseas\Data\Library\Fonts"
New-Item -ItemType Directory -Force -Path $fontDir | Out-Null
$userFonts = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
New-Item -ItemType Directory -Force -Path $userFonts | Out-Null
$reg = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
if (-not (Test-Path $reg)) { New-Item $reg -Force | Out-Null }
foreach ($f in Get-ChildItem (Join-Path $Repo "fonts") -Filter *.ttf) {
    Copy-Item $f.FullName $fontDir -Force
    $dst = Join-Path $userFonts $f.Name
    if (-not (Test-Path $dst)) { Copy-Item $f.FullName $dst }
    New-ItemProperty -Path $reg -Name "$($f.BaseName) (TrueType)" -Value $dst -PropertyType String -Force | Out-Null
}
Ok "fonts installed for this user (restart CapCut to see them)"

Step "9/9 Settings"
# Hebrew file and project names: make Python read/write UTF-8 everywhere (default on Windows is cp1255)
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User"); $env:PYTHONUTF8 = "1"
New-Item -ItemType Directory -Force -Path (Join-Path $Home_ "VideoAssets\music"), (Join-Path $Home_ "VideoAssets\סאונד\SFX") | Out-Null
Ok "PYTHONUTF8=1, ~\VideoAssets"

Write-Host "`n> Readiness check" -ForegroundColor Cyan
& $Py (Join-Path $Engine "doctor.py")

Write-Host "`nDone. Open a NEW Claude Code session (new terminal) and ask, for example:" -ForegroundColor Green
Write-Host "  'Read windows.md and run doctor.py', then 'תערוך את הסשן של X'"
