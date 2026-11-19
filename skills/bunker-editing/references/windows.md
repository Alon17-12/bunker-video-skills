# Running these skills on Windows

The skills and the engine were built on a Mac (CapCut 7.8 for desktop). `install.ps1` sets up Windows so that
almost every command in the skills runs unchanged. This page lists what differs. Read it before the first job
on a Windows machine, and again whenever something works on the Mac but not here.

## Run the readiness check first

```bash
~/bunker-video-engine/.venv/bin/python ~/bunker-video-engine/doctor.py
```

Every ✗ has to be fixed before you write to a CapCut project. A ⚠ about `Timelines/` means you test on a
throwaway project first (see "CapCut version" below).

## What the installer did so the Mac commands keep working

Claude Code on Windows runs shell commands in **Git Bash**, so `~` is `%USERPROFILE%` and `/` paths work.

| Mac command in the skills | Why it also works on Windows |
|---|---|
| `~/bunker-video-engine/.venv/bin/python` | `.venv\bin` is a junction to `.venv\Scripts` |
| `~/ffmpeg-bin/ffmpeg`, `~/ffmpeg-bin/ffprobe` | `~\ffmpeg-bin` is a junction to the engine's `bin` (`ffmpeg.exe`); Windows adds `.exe` itself |
| fonts under `~/Library/Containers/com.lemon.lvoverseas/Data/Library/Fonts/` | the installer creates that folder and puts the house fonts there (Heebo, Assistant, Fredoka). Bamberger is a paid font and isn't included |
| `capcut.DRAFTS_DIR` | `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`. If CapCut saves somewhere else, set `BUNKER_CAPCUT_DRAFTS` |
| Hebrew project and file names | `PYTHONUTF8=1` is set for the user. Without it Python reads the JSON files in cp1255 and breaks the Hebrew |

## Rules that differ

1. **Quit CapCut completely before every write**, not just back to the home screen. Windows has no `lsof`,
   so the engine can't tell which project is open. While `CapCut.exe` is running, it treats every project
   as locked and refuses to write.
2. **Drives:** the RØDECaster SSD gets a drive letter, not `/Volumes/<name>`. In Git Bash that's `/d/…`,
   `/e/…`. Wherever a skill says `/Volumes/*`, search every drive letter
   (`ls /?/*/RODECASTER_Video 2>/dev/null`). The same goes for `/Volumes` paths stored inside old projects.
3. **Encoders:** `h264_videotoolbox` and `hevc_videotoolbox` only exist on Mac. The scripts already choose
   `libx264` (and ProRes 4444 for alpha cut-outs) on their own. If you see a command in the docs with
   `videotoolbox`, use `-c:v libx264 -preset fast`, or `h264_nvenc` on an NVIDIA card.
4. **Things that don't exist on Windows:** Finder and `osascript` (to open a folder, use
   `explorer.exe "<path>"`), `open -a`, MapKit, `afplay`. Deleting goes to the Recycle Bin, not the Trash.
5. **Disks:** wherever the docs mention "the internal APFS disk", read "the internal NTFS disk" (`C:`).
   The rule stays the same: build and mux on the internal disk, then copy to the external drive and
   check md5. Hard links (`os.link`) only work within a single volume.
6. **Paths in reports to the user:** give a Windows path (`C:\Users\…`) so they can paste it into
   Explorer.
7. **Effects from CapCut's cache:** a few scripts point at an effect file in the Mac cache
   (`Cache/effect/<id>/…`). On Windows that path doesn't exist. CapCut usually re-downloads the effect by
   its id when the project opens. If an effect is missing, add it once by hand in CapCut, and from then
   on take it from that project (a donor).

## CapCut version (the main risk)

The engine writes the project JSON directly. That works as long as CapCut saves projects as **plain
JSON** (`draft_info.json` or `draft_content.json` that starts with `{`).

- **Encrypted project** (binary file): the engine can't work with it. Stop and report it. This is known
  from the Chinese version (JianYing 6+), not from the international CapCut.
- **`Timelines/` folder inside the project** (CapCut 8.7+ on Windows, 9.x on Mac): CapCut may read the
  timeline from `Timelines/<id>/draft_info.json` or `template-2.tmp`, and a write to the root file gets
  ignored. Before the first real job:
  1. Duplicate a project.
  2. Write one caption to it with the engine.
  3. Open it in CapCut.
  4. Check that the caption is there.

  If it isn't, report it to Alon. Don't keep going.
- **A project the engine built from scratch** that won't open ("corrupted" / "unusual path"): start from
  a donor project created by Dolev's own CapCut (empty or a template), not one copied from the Mac.

**Projects from the Mac:** a CapCut project folder copied from Alon's Mac holds absolute `/Users/...` and
`/Volumes/...` paths. It opens on Windows with the media marked missing. Relink in CapCut, or use the
skills' `reel_repoint_materials.py`.
