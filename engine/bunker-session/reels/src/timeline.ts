// The reel's timeline, computed once from the cut json (build_cut.py) and the reel's plan.
// Routing follows tsomet-20 reels-capcut.md: the camera is ALWAYS the person speaking (per-word speaker from the two
// mics), a real reaction of the listener may cut in (chosen by eye from the reaction sheets), and exchanges/listening
// moments go to the split screen. A jump cut keeps the framing unless that framing has held ≥ 3 s (88 zoom-cuts in the
// Guest N reels read as aggressive — Alon 15.10.2026), and the motion comes from eased pushes on keywords instead.

export type Word = { text: string; at: number; end: number; who: "host" | "guest" | "guest2"; clip: number };   // guest2: a third voice on the cam-3 crop (face["3"]) — אורח C 11.11.2026
export type Clip = { at: number; end: number; src: number; cam: 1 | 2; who: string };
export type Cut = { duration: number; clips: Clip[]; words: Word[] };

export type Plan = {
  file: string; title: string;
  react?: Range[];                 // the listener's real reaction (other camera)
  hold?: [number, number, 1 | 2][];   // one camera on screen whoever speaks — the listener's reaction landing on his own word
                                      // (אורח K 28.10.2026: «כשאלון אומר וואו שיראו רק אותו, ואז קאט לטק טק טק»)
  react3?: Range[];                // a third person's reaction (cam3s.mp4 + face["3"] — 3 speakers on 2 cameras, אלון+אייל+דולב 21.10.2026)
  mix?: number[];                  // jump cuts (reel s) that dissolve instead of cutting, framing kept (round 10: «קאטים חדים ומוזרים»)
  zcut?: number[];                 // jump cuts (reel s) that change the framing even inside 3 s — a visible jump (Alon 21.10: «חיתוכים גסים מדיי»)
  split?: Range[];                 // both faces, guest on top
  duo?: [number | string, number | string, 1 | 2 | 3, 1 | 2 | 3, number?][];   // 5th: shift (s) of the top crop's footage — a listener // split of any two crops [from, to, top, bottom] — the two
                                   // listeners reacting together, or the speaker with the one he talks about (1 = cam1 crop, 3 = face["3"])
  glass?: { items: { at: string; amount: string; label: string }[]; hide: string; recall: string; shatter: string };
  logo?: string;                   // this reel's logo file instead of the session's (e.g. without WhiteBoard)
  broll?: { from: number; to: number; img: string; zoom?: number }[];   // stills over the picture (reel seconds)
  flash?: number[];                // white flash transitions (reel seconds)
  split3?: Range[];                // both faces, the third person on top (3 speakers / 2 cameras: the guest's listening face was
                                   // not worth showing — אלון+אייל+דולב 26.10.2026: «רק זויות רלוונטיות של עניין»)
  push?: string[];                 // keyword (word text, n-th occurrence via "text#n") → an eased push that lands on it
  hot?: string[];                  // caption words in the accent colour ("text" or "text#n")
  pills?: { word: string; n: number; hold?: number }[]; // brand keyword pill: the n spoken words from `word` (the caption skips them)
  counter?: { word: string; to: number; suffix?: string; label?: string; hold?: number; skip?: string[] };
  fix?: Record<string, string>;     // caption text fixes, keyed "text" or "text#n" (positional — never a global replace)
  drop?: string[];                  // caption words not shown ("text#n") — e.g. a stutter left in for the picture
  breaks?: string[];                // caption words that always start a new card — no merge pulls a word across them
                                    // (round 6: «פודקאסט, אז / זהו שלא.» → «זה לצלם פודקאסט,» / «אז זהו שלא.»)
  solo?: [string, string?];         // caption words one per card, each on its own word's time — from the first anchor to the second
                                    // (or the end) (תוכן הבונקר 4.11.26 round 5: «שיראו מילה מילה את מה שדולב אומר, בדיוק על הזמן»)
  cards?: number[];                 // hand-made caption cards: word counts in order (empty words not counted) — the phrase stays
                                    // whole on one card («אחי תקשיב», «בית ספר»; אלון+אייל+דולב 26.10.2026)
};

// a range in reel seconds, or anchored to words: ["word#n", "word#n"] = from that caption start to the next one's,
// ["word#n", 1.7] = 1.7 s from that word — anchors survive a re-cut (a stutter taken out shifts every second after it)
export type Range = [number | string, number | string];
export const resolve = (cut: Cut, rs: Range[] | undefined): [number, number][] => (rs ?? []).map(([a, b]) => {
  const at = (k: string) => { const w = findWord(cut, k); if (!w) throw new Error(`anchor word not found: ${k}`); return w.at - 0.06; };
  const s = typeof a === "string" ? at(a) : a;
  const e = typeof b === "string" ? at(b) : typeof a === "string" ? s + b : b;
  return [s, e];
});

export type Shot = { at: number; end: number; cam: 1 | 2 | 3; src: number; kind: "main" | "react" | "split"; clip: number; z: number; jump?: boolean;
  top?: 1 | 2 | 3; bottom?: 1 | 2 | 3; shift?: number; run0?: number };   // run0: start of this camera's unbroken stretch (the drift's clock)   // a "duo" split: which camera crop on top / at the bottom

const camOf = (who: string): 1 | 2 | 3 => (who === "host" ? 1 : who === "guest2" ? 3 : 2);
export const WIDE = 1.0, TIGHT = 1.2;

/** n-th word whose text contains s ("שכחתי#1" = the second) → reel time, or -1 */
export const findWord = (cut: Cut, key: string) => {
  const [s, n] = key.split("#");
  const bare = (x: string) => x.replace(/[.,?!]/g, "");
  // exact word first ("או" must never find "אותנטיות"); a substring only when nothing matches exactly
  let hits = cut.words.filter((w) => w.text === s);
  if (!hits.length) hits = cut.words.filter((w) => bare(w.text) === bare(s));
  if (!hits.length) hits = cut.words.filter((w) => w.text.includes(s));
  return hits[Number(n ?? 0)] ?? null;
};
export const srcAt = (cut: Cut, t: number) => {
  const i = cut.clips.findIndex((c) => t >= c.at - 1e-3 && t < c.end - 1e-3);
  const c = cut.clips[i < 0 ? cut.clips.length - 1 : i];
  return { clip: i < 0 ? cut.clips.length - 1 : i, src: c.src + (t - c.at) };
};

/** who is on camera at reel time t from speech alone (runs of one speaker; a turn ≥ 0.15 s gets its face, held ≥ 0.5 s) */
const speakerTrack = (cut: Cut) => {
  const marks: { at: number; cam: 1 | 2 | 3 }[] = [];
  cut.clips.forEach((c, ci) => {
    const ws = cut.words.filter((w) => w.clip === ci);
    const runs: { i: number; j: number; cam: 1 | 2 | 3 }[] = [];
    ws.forEach((w, i) => { const r = runs[runs.length - 1]; if (r && r.cam === camOf(w.who)) r.j = i; else runs.push({ i, j: i, cam: camOf(w.who) }); });
    const dur = (r: { i: number; j: number }) => ws[r.j].end - ws[r.i].at;
    let cur = (runs.find((r) => dur(r) >= 0.25) ?? runs[0])?.cam ?? c.cam;
    marks.push({ at: c.at, cam: cur });
    let hold = c.at, last = c.at;
    for (const r of runs) {
      if (r.cam === cur) continue;
      const w = ws[r.i];
      if (dur(r) < 0.15 || w.at - last < 0.2) continue;
      const at = Math.max(c.at, w.at - 0.08, hold);
      if (at >= c.end - 0.15) continue;
      marks.push({ at, cam: r.cam });
      cur = r.cam; last = at; hold = at + 0.5;
    }
  });
  return (t: number) => { let cam: 1 | 2 | 3 = 2; for (const m of marks) if (m.at <= t + 1e-4) cam = m.cam; return cam; };
};

export const shotsOf = (cut: Cut, plan0: Plan): Shot[] => {
  // an overlay edge within 0.3 s of a cut snaps onto it — otherwise a 0.1 s sliver of the old shot flashes by
  const cuts = cut.clips.map((c) => c.at).concat(cut.duration);
  const snapT = (t: number) => { const c = cuts.reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a)); return Math.abs(c - t) < 0.3 ? c : t; };
  const snapR = (rs: [number, number][]) => rs.map(([a, b]) => [snapT(a), snapT(b)] as [number, number]);
  const plan = { react: snapR(resolve(cut, plan0.react)), react3: snapR(resolve(cut, plan0.react3)), split: snapR(resolve(cut, plan0.split)),
    split3: snapR(resolve(cut, plan0.split3)),
    duo: (plan0.duo ?? []).map(([a, b, top, bottom, shift]) => { const [r] = snapR(resolve(cut, [[a, b]])); return { r, top, bottom, shift: shift ?? 0 }; }) };
  const speaker = speakerTrack(cut);
  const inR = (rs: [number, number][] | undefined, t: number) => (rs ?? []).some(([a, b]) => t >= a - 1e-4 && t < b - 1e-4);
  const state = (t: number) => {
    const { clip } = srcAt(cut, t);
    if (inR(plan.split, t)) return { kind: "split" as const, cam: 2 as const, clip };
    if (inR(plan.split3, t)) return { kind: "split" as const, cam: 3 as const, clip };
    const d = plan.duo.find(({ r: [a, b] }) => t >= a - 1e-4 && t < b - 1e-4);
    if (d) return { kind: "split" as const, cam: 2 as const, clip, top: d.top, bottom: d.bottom, shift: d.shift };
    const h = (plan0.hold ?? []).find(([a, b]) => t >= a - 1e-4 && t < b - 1e-4);
    if (h) return { kind: "react" as const, cam: h[2], clip };
    const s = speaker(t);
    if (inR(plan.react3, t)) return { kind: "react" as const, cam: 3 as const, clip };
    if (inR(plan.react, t)) return { kind: "react" as const, cam: (s === 1 ? 2 : 1) as 1 | 2, clip };
    return { kind: "main" as const, cam: s, clip };
  };
  // boundaries: every clip edge, speaker mark and overlay edge — sample the state just after each
  const edges = new Set<number>([0]);
  cut.clips.forEach((c) => { edges.add(c.at); });
  for (const [a, b] of [...(plan.react ?? []), ...(plan.react3 ?? []), ...(plan.split ?? []), ...(plan.split3 ?? []), ...plan.duo.map((d) => d.r)]) { edges.add(a); edges.add(b); }
  for (const z of plan0.zcut ?? []) edges.add(z);   // a framing change inside one long take, at a sentence start
  for (const [a, b] of plan0.hold ?? []) { edges.add(a); edges.add(b); }
  for (let t = 0; t < cut.duration; t += 1 / 30) { if (speaker(t) !== speaker(t + 1 / 30)) edges.add(Math.round((t + 1 / 30) * 30) / 30); }
  const ts = [...edges].filter((t) => t < cut.duration - 1e-3).sort((a, b) => a - b);
  const zc = (t: number) => (plan0.zcut ?? []).some((x) => Math.abs(x - t) < 0.06);
  const raw: Omit<Shot, "z">[] = [];
  for (let i = 0; i < ts.length; i++) {
    const at = ts[i], end = ts[i + 1] ?? cut.duration, st = state(at + 1e-3);
    const prev = raw[raw.length - 1];
    // a listener's reaction plays straight on over a cut in the voice — the cut is hidden under it, not shown twice
    const tb = st as { top?: 1 | 2 | 3; bottom?: 1 | 2 | 3; shift?: number };
    if (prev && prev.kind === st.kind && prev.cam === st.cam && prev.top === tb.top && prev.bottom === tb.bottom && (prev.clip === st.clip || st.kind === "react") && !(st.kind === "main" && zc(at))) { prev.end = end; continue; }
    raw.push({ at, end, cam: st.cam, kind: st.kind, clip: st.clip, src: srcAt(cut, at).src, top: tb.top, bottom: tb.bottom, shift: tb.shift });
  }
  // a shot shorter than 0.25 s takes the look of the shot before it (it keeps its own source time — the picture stays in sync)
  for (let i = 1; i < raw.length; i++) if (raw[i].end - raw[i].at < 0.25) { raw[i].kind = raw[i - 1].kind; raw[i].cam = raw[i - 1].cam;
    raw[i].top = raw[i - 1].top; raw[i].bottom = raw[i - 1].bottom; raw[i].shift = raw[i - 1].shift; }   // a duo sliver kept its default crops → one frame of cam 1 under the split (עומר 11.11.2026)
  // framing: every jump cut (same camera, the voice cut) changes the framing — the same framing across a cut is the
  // «קפיצה מוזרה» (אלון+אייל+דולב 26.10.2026). Only a seam where the source plays straight on keeps it.
  const out: Shot[] = [];
  let framing = WIDE;
  raw.forEach((s, i) => {
    const p = raw[i - 1];
    const c0 = cut.clips[p?.clip ?? 0], c1 = cut.clips[s.clip];
    const seamless = !!p && Math.abs(c1.src - (c0.src + c0.end - c0.at)) < 0.05;
    const jump = !!p && p.kind === "main" && s.kind === "main" && p.cam === s.cam && p.clip !== s.clip && !seamless;
    if (s.kind !== "main") { out.push({ ...s, z: s.kind === "react" ? WIDE : 1.0, jump }); return; }
    if (!p || p.cam !== s.cam || p.kind !== "main") framing = WIDE;
    else if ((jump && !(plan0.mix ?? []).some((x) => Math.abs(x - s.at) < 0.06)) || zc(s.at)) framing = framing === WIDE ? TIGHT : WIDE;
    out.push({ ...s, z: framing, jump });
  });
  // the drift's clock: a main shot that continues the same camera at the same framing carries the stretch's start
  out.forEach((s, i) => { const p = out[i - 1];
    s.run0 = p && p.kind === "main" && s.kind === "main" && p.cam === s.cam && Math.abs(p.z - s.z) < 1e-3 ? p.run0 ?? p.at : s.at; });
  return out;
};

/** eased push on a keyword: rises over 0.7 s to land on the word, holds 1.1 s, falls back over 0.9 s (tsomet 15.10 "זום ease") */
export const pushes = (cut: Cut, plan: Plan) => (plan.push ?? []).map((k) => findWord(cut, k)?.at ?? -1).filter((t) => t > 0);
