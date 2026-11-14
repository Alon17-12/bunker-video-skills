#!/usr/bin/env python3
"""Every reel cut of a session: prep_words → each work/edl_rN.sh (tighten_edl) → build_cut on silence → post_cut.

    python3 build_cuts.py <session>
"""
import os, subprocess, sys
from pathlib import Path
from rpaths import session_paths

S, RM, PUB, WORK = session_paths(sys.argv)
T = Path.home() / ".claude/skills/bunker-editing/vendor/teaser"
HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(HERE / "prep_words.py"), str(S)], check=True)
cuts = []
for edl in sorted(WORK.glob("edl_r*.sh"), key=lambda p: int(p.stem.split("_r")[1])):
    n = edl.stem.split("_r")[1]
    subprocess.run(["zsh", str(edl)], check=True, cwd=RM, env=dict(os.environ, T=str(T)))
    subprocess.run([sys.executable, str(T / "build_cut.py"), str(WORK / f"edl_r{n}.json"), str(WORK / "words.json"),
                    str(WORK / "speakers.json"), str(PUB / f"r{n}.json"), "--audio", str(WORK / "dialogue16k.wav")], check=True)
    cuts.append(str(PUB / f"r{n}.json"))
subprocess.run([sys.executable, str(HERE / "post_cut.py"), str(S), *cuts], check=True)
