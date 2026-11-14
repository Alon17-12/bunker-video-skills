"""`$PY -m bsession <command>` — the deterministic steps the bunker-session skill calls."""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from . import session as S, spec as SP, ingest as I, transcript as T, picks as P, reel_plan as R
from . import reel_qa as Q, episode as E, notes as N, deliver as D, express as X, corrections as C

REPO = Path(__file__).resolve().parent.parent
CAPTAIN = Path.home() / "bunker-video-engine/app"
SKILLS = Path.home() / ".claude/skills"
FFMPEG = str(Path.home() / "ffmpeg-bin" / "ffmpeg")
COMMANDS = ("init", "spec", "check-spec", "ingest", "transcribe", "check-picks", "plans",
            "qa-reel", "qa-episode", "notes", "corrections", "deliver", "status", "mark")


def _decode(path: Path, t0: float | None = None, dur: float | None = None, sr: int = 16000) -> np.ndarray:
    cmd = [FFMPEG, "-v", "error"]
    if t0 is not None:
        cmd += ["-ss", f"{max(t0, 0)}"]
    if dur is not None:
        cmd += ["-t", f"{dur}"]
    cmd += ["-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def load_window(paths: list[Path], t0: float, t1: float) -> np.ndarray:
    """Mono 16 kHz float32 of the mic mix (never Live-Mix) for [t0, t1)."""
    chans = [_decode(p, t0, t1 - t0) for p in paths]
    n = min(c.size for c in chans)
    return np.mean([c[:n] for c in chans], axis=0).astype(np.float32)


def _rms50(path: Path) -> np.ndarray:
    x = _decode(path, sr=800)
    n = x.size // 16
    return np.sqrt((x[: n * 16].reshape(n, 16) ** 2).mean(axis=1))


def known_fonts() -> set[str]:
    txt = (REPO / "skill/references/fonts.txt").read_text(encoding="utf-8")
    line = next((l for l in txt.splitlines() if l.startswith("FONTS:")), "FONTS:")
    return {f.strip() for f in line[6:].split(",") if f.strip()}


def _session(p: str) -> Path:
    s = Path(p)
    if not (s / "יומן.md").exists():
        sys.exit(f"לא תיקיית סשן: {s}")
    return s


# ---------- commands ----------

def cmd_init(a):
    s = S.create_session(Path(a.root), a.client, a.date)
    spec = s / "אפיון.json"
    if not spec.exists():
        shutil.copy(REPO / "skill/references/spec-template.json", spec)
    S.Journal(s).log("init", f"נפתח סשן {s.name}")
    print(s)


def cmd_spec(a):
    s = _session(a.session)
    x = X.read_express_html(Path(a.html).read_text(encoding="utf-8"))
    spec, kept = X.to_session_spec(x), []
    prev = s / "אפיון.json"
    if prev.exists():                                        # a re-submitted form: keep who-is-who and the site brand
        spec, kept = X.carry_over(spec, json.loads(prev.read_text(encoding="utf-8")))
    (s / "אפיון.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy2(a.html, s / "אפיון.html")
    url = (x.get("look") or {}).get("logo_url")
    if url:                                                  # last, and never fatal: the spec is already written
        if not str(url).startswith(("https://", "http://")):
            print(f"⚠ קישור הלוגו לא תקין ({url}) — לבקש את הלוגו מהלקוח")
        else:
            try:
                import urllib.request
                urllib.request.urlretrieve(url, s / "לוגו.png")
            except Exception as e:
                print(f"⚠ הלוגו לא ירד ({e}) — לבקש את הלוגו מהלקוח")
    S.Journal(s).log("spec", f"אפיון בונקר אקספרס נקלט: {spec['show']} · {len(spec['speakers'])} דוברים"
                     + (f" · נשמר מהקודם: {', '.join(kept)}" if kept else ""))
    print(json.dumps(spec, ensure_ascii=False, indent=1))


def cmd_check_spec(a):
    s = _session(a.session)
    errs = SP.validate_spec(SP.load_spec(s), known_fonts())
    for e in errs:
        print(e)
    sys.exit(1 if errs else 0)


def _offset_3win(ref: Path, other: Path, dur: float, win: float = 60.0) -> list[float]:
    """Offset (other_t = ref_t + off) measured in three windows spread over the recording."""
    if dur < 3 * win:
        starts = [0.0]
    else:
        gap = min(1200.0, (dur - win) / 2)
        mid = (dur - win) / 2
        starts = [max(mid - gap, 0), mid, min(mid + gap, dur - win)]
    return [I.measure_offset(_decode(ref, t, win), _decode(other, t, win), 16000) for t in starts]


def cmd_ingest(a):
    s = _session(a.session)
    j, st = S.Journal(s), S.State(s)
    card = [p for p in Path(a.card).rglob("*") if p.is_file()]
    c = I.classify(card)
    durs = {k: I.probe_duration(c[k]) for k in ("source", "cam1", "cam2")}
    probs = [f"יש יותר מהקלטה אחת בכרטיס ({', '.join(c['duplicates'])}) — תן את תיקיית ההקלטה עצמה"
             for _ in c["duplicates"][:1]]
    probs += I.probe_problems(c, durs) or I.completeness(durs)
    if probs:
        for p in probs:
            print(p)
        st.set("ingest", "failed"); sys.exit(1)
    st.set("ingest", "running")
    c = I.copy_card(c, s, j, in_place=a.in_place)
    c["mics"], silent = I.drop_silent(c["mics"], {m.name: I.mean_volume(m) for m in c["mics"]})
    for m in silent:
        j.log("ingest", f"מיקרופון שקט, לא בשימוש: {m.name}")
    offsets = {}
    for k in ("cam1", "cam2"):
        if c[k] is None:
            offsets[k] = None
            continue
        vals = _offset_3win(c["source"], c[k], durs["source"])
        if not I.offsets_agree(vals):
            print(f"הסנכרון של {I.LABEL[k]} לא עקבי: {vals}")
            st.set("ingest", "failed"); sys.exit(1)
        offsets[k] = float(np.median(vals))
    if (p := I.cam_sync_problem(offsets)):
        print(p); st.set("ingest", "failed"); sys.exit(1)
    mic_src = 0.0
    if c["mics"]:
        vals = _offset_3win(c["source"], c["mics"][0], durs["source"])
        if not I.offsets_agree(vals):
            print(f"הסנכרון של המיקרופונים לא עקבי: {vals}")
            st.set("ingest", "failed"); sys.exit(1)
        mic_src = float(np.median(vals))
    offsets["mic_src"] = mic_src                      # mic_t = source_t + mic_src
    offsets["mic"] = mic_src - offsets["cam1"]        # mic_t = cam_t + mic
    out = {"source": str(c["source"]), "cam1": str(c["cam1"]),
           "cam2": str(c["cam2"]) if c["cam2"] else None,
           "mics": [str(m) for m in c["mics"]], "durations": durs, "offsets": offsets}
    (s / "ingest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    j.log("ingest", f"offsets {offsets}")
    st.set("ingest", "done")
    print(json.dumps(offsets))


def cmd_transcribe(a):
    s = _session(a.session)
    final = s / "תמלול/transcript.json"
    if final.exists() and json.loads(final.read_text()).get("clock") == "source":
        print("התמלול כבר הושלם"); S.State(s).set("transcript", "done"); return
    sys.path.insert(0, str(CAPTAIN))
    import transcribe as stt                           # the captain's faster-whisper model
    ing = json.loads((s / "ingest.json").read_text())
    mics = [Path(m) for m in ing["mics"]] or [Path(ing["source"])]
    shift = ing["offsets"].get("mic_src", 0.0) if ing["mics"] else 0.0
    dur = I.probe_duration(mics[0])
    j, st = S.Journal(s), S.State(s)
    st.set("transcript", "running")
    words = T.run(mics, s / "תמלול", stt.transcribe, load_window, dur)
    words = T.tag_speakers(words, {i + 1: _rms50(m) for i, m in enumerate(mics)})
    words = [dict(w, start_s=w["start_s"] - shift, end_s=w["end_s"] - shift) for w in words]  # → source clock
    (s / "תמלול/transcript.json").write_text(
        json.dumps({"done_until": dur, "clock": "source", "words": words}, ensure_ascii=False))
    (s / "תמלול/episode.srt").write_text(T.to_srt(words), encoding="utf-8")
    st.set("transcript", "done"); j.log("transcript", f"{len(words)} מילים")


def _words(s: Path) -> list[dict]:
    return json.loads((s / "תמלול/transcript.json").read_text())["words"]


def cmd_check_picks(a):
    s = _session(a.session)
    f = s / "רילס/רילס.json"
    words = _words(s)
    picks = [P.snap(p, words) for p in json.loads(f.read_text())]
    f.write_text(json.dumps(picks, ensure_ascii=False, indent=1))
    count = SP.load_spec(s).get("reels", {}).get("count", 10)   # 10 by default; a short episode sets fewer
    errs = P.validate_picks(picks, words, count=count)
    for e in errs:
        print(e)
    S.State(s).set("picks", "failed" if errs else "done")
    sys.exit(1 if errs else 0)


def cmd_plans(a):
    s = _session(a.session)
    spec, ing = SP.load_spec(s), json.loads((s / "ingest.json").read_text())
    for p in json.loads((s / "רילס/רילס.json").read_text()):
        d = s / "רילס" / R.reel_dir_name(p)
        d.mkdir(exist_ok=True)
        target = f"{spec['client']} · ריל {p['n']:02d}"
        (d / "plan.json").write_text(json.dumps(R.build_plan(p, spec, ing, target, a.donor),
                                                ensure_ascii=False, indent=1))
        print(d)


def cmd_qa_reel(a):
    d = Path(a.reel_dir)
    lv = D.latest_version(d)
    if not lv:
        sys.exit(f"אין רינדור ב-{d}")
    ver, video = lv
    cuts = json.loads((d / "cuts.json").read_text()) if (d / "cuts.json").exists() else []
    lines = [f"# בדיקה — v{ver}", ""]
    if cuts:
        sheet = Q.contact_sheet(video, cuts, d / f"qa-v{ver}.jpg")
        lines.append(f"- פריימים סביב {len(cuts)} קאטים: {sheet.name}")
    words = json.loads((d / f"heard-v{ver}.json").read_text()) if (d / f"heard-v{ver}.json").exists() else None
    if words is not None:
        lines += [f"- {e}" for e in Q.boundary_report(words, I.probe_duration(video))]
    (d / f"qa-v{ver}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def cmd_qa_episode(a):
    s = _session(a.session)
    video = Path(a.video) if a.video else s / "פרק/פרק.mp4"
    rep = E.qa_report(video)
    (s / "פרק/בקרת-איכות.md").write_text(rep, encoding="utf-8")
    print(rep)


def cmd_notes(a):
    s = _session(a.session)
    print(json.dumps(N.parse_notes((s / f"תיקונים/{a.who}.md").read_text(encoding="utf-8")),
                     ensure_ascii=False, indent=1))


def cmd_corrections(a):
    s = _session(a.session)
    parsed = C.parse_prompt(Path(a.prompt).read_text(encoding="utf-8"))
    rows = C.locate(s, parsed)
    (s / "תיקונים" / f"{parsed['round']}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    S.Journal(s).log("corrections", f"{parsed['round']}: {len(rows)} הערות")
    for r in rows:
        when = "כללי" if r["t"] is None else f"{int(r['t'] // 60)}:{r['t'] % 60:04.1f}"
        print(f"[{r['dir']}] {when} — {r['text']}" + (f"   ‹{r['said']}›" if r["said"] else ""))


def cmd_deliver(a):
    s = _session(a.session)
    out = D.stage_express(s)
    S.State(s).set("deliver", "done"); S.Journal(s).log("deliver", f"{len(out)} קבצים במסירה (חומרי גלם · הפרק השלם · רילס)")
    for p in out:
        print(p.name)


def cmd_status(a):
    s = _session(a.session)
    st = S.State(s)
    for stage in S.STAGES:
        print(f"{stage:12} {st.get(stage)}")
    print(f"next: {st.next_pending(S.STAGES)}")


def cmd_mark(a):
    s = _session(a.session)
    S.State(s).set(a.stage, a.status)
    S.Journal(s).log(a.stage, a.status)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bsession")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("root"); p.add_argument("client"); p.add_argument("date")
    p = sub.add_parser("spec"); p.add_argument("session"); p.add_argument("html")
    for name in ("check-spec", "transcribe", "check-picks", "deliver", "status"):
        sub.add_parser(name).add_argument("session")
    p = sub.add_parser("ingest"); p.add_argument("card"); p.add_argument("session")
    p.add_argument("--in-place", action="store_true", help="work off the SSD folder, copy nothing")
    p = sub.add_parser("plans"); p.add_argument("session"); p.add_argument("--donor", required=True)
    sub.add_parser("qa-reel").add_argument("reel_dir")
    p = sub.add_parser("qa-episode"); p.add_argument("session"); p.add_argument("--video")
    p = sub.add_parser("corrections"); p.add_argument("session"); p.add_argument("prompt")
    p = sub.add_parser("notes"); p.add_argument("session"); p.add_argument("who", choices=["צוות", "לקוח"])
    p = sub.add_parser("mark"); p.add_argument("session"); p.add_argument("stage", choices=S.STAGES)
    p.add_argument("status", choices=["pending", "running", "done", "failed"])
    a = ap.parse_args(argv)
    globals()["cmd_" + a.cmd.replace("-", "_")](a)
