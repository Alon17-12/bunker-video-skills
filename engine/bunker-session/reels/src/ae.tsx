// The "After Effects" layer (אורח B 28.10.2026: «כל הסרטונים צריכים להראות כמו סרטוני אפטר אפקטס עם אנימציות מתקדמות,
// אלגנטיות ונקיות — שהעריכה תעביר את המסר»). Plan key "ae": beats anchored to spoken words, each one a clean motion piece:
//   clip   — full-frame B-roll in/out through a zoom-through, a whip with directional blur, an iris or a rise
//   shrink — the camera settles into a rounded window on top, the B-roll rises into a card below (face never covered)
//   type   — full-screen kinetic type of the spoken words themselves (captions step out), masked reveals, numbers count up
//   leak   — a warm light sweep (added on every zoom / whip / shrink by itself)
//   num    — a big counted number laid over the picture (round 7: «2,000 קורסים שיהיו על הפריים של אורח B בגדול»)
//   rain   — bills falling over the frame with the till («שטרות שנופלים על אורח B… עם סאונד של קופה»)
//   glow   — red alarm lights over a loss («אורות אדומים של הפסד»)
//   cal    — a calendar: today / tomorrow / the day after, each filled as it is said («אפקט של יומן»)
//   glass  — a big number in glass beside the speaker that cracks and falls («ישברו ויפלו כשהוא אומר נכשלו קשה»)
// round 8: drain (a sum that pieces fly out of until what is left), msgs (a flood of messages), scale (two things weighed),
//   map (pins dropping on a map in the card strip), profile (a mock social profile); cards chain with in/out "fade"
// plus a film grain and a soft vignette over the whole reel. Every element eases in and out — no shake, no pops.
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { noise2D } from "@remotion/noise";
import { evolvePath } from "@remotion/paths";
import { fitText } from "@remotion/layout-utils";
import { ramp, inOut } from "./look";
import { Word } from "./timeline";

export type AeIn = "cut" | "zoom" | "whip" | "iris" | "rise" | "fade";
export type AeBeat = {
  k: "clip" | "shrink" | "card" | "type" | "leak" | "num" | "rain" | "glow" | "cal" | "glass" | "drain" | "msgs" | "scale" | "map" | "profile" | "rows" | "meter"
    | "icon" | "marks" | "year" | "world" | "gap" | "border" | "logo" | "arrow" | "checks" | "brands" | "anger" | "dm" | "site" | "notes";
  from: number; to: number;
  again?: number;                 // arrow: reel second of its second call (resolved from a word anchor in Reel)
  show?: number;                  // arrow: seconds on screen per call — it leaves, and comes back only at "again" (round 7)
  file?: string; ss?: number;            // B-roll (public/…) and its start inside the file, seconds
  in?: AeIn; out?: AeIn; dir?: 1 | -1;   // transitions; dir = whip direction (1 = enters from the left)
  grade?: "warm" | "mono" | "cool" | "none";
  speed?: number;                        // B-roll playback rate (0.5 = slow motion)
  push?: number;                         // how far the B-roll pushes in over its time (default 0.08)
  fit?: boolean;                         // the B-roll exactly fills the frame: no base overscan, no push, no drift
  fd?: number;                           // a longer "fade" in/out (s) — round 10: «2 קאטים חדים ומוזרים בתחילת הסרטון»
  words?: Word[]; gold?: string[];       // type: the spoken words in its window (after the plan's fixes), gold ones by text
  big?: Record<string, string>;          // type: a word shown as a huge counted number («שמונה» → "8")
  label?: string;                        // shrink: a small gold label on the B-roll card
  bg?: string; bgSs?: number;            // type: a B-roll behind the words (blurred, dark); default = the camera, blurred
  bgBlur?: number;
  focus?: { x: number; y: number; ty?: number };   // B-roll framing by a point of the 9:16 source (x, y 0–1) placed at the box's centre / ty — a face
  bars?: { at: number; label: string; fill: number; bad?: boolean }[];   // meter: bars that fill as they are said                       // type: how soft that B-roll is (px, default 18) — 4 keeps it readable as footage (r1 round 9)
  pos?: number; zoom?: number;           // B-roll framing: vertical anchor 0–100 % and an extra zoom — to keep a clip's burned-in text out
  rowsAt?: string[];                     // type + one: start a new row on these words (else balanced automatically)
  hold?: boolean;                        // type: runs under the end card, no fade-out over the picture
  one?: boolean;                         // type: every word on one screen, building line by line (round 7: «שכל המילים יופיעו באותו מסך»)
  text?: string; y?: number; size?: number;   // num / glass: the number, its centre line and size
  ty?: number;                           // anger: the line's top (default 300 px over the head)
  x?: number; w?: number; h?: number;    // glass: the panel's box
  shatter?: number;                      // glass: when it cracks and falls (reel time)
  count?: number;                        // rain: how many bills
  days?: { title: string; text: string; at: number }[];   // cal: the three pages, each lit when its words are said
  only?: "host" | "guest";               // type: only this speaker's words (the other one keeps the camera and the caption)
  start?: number; suffix?: string;       // drain: the sum it starts from
  steps?: { at: number; icon: string; label: string; value: number }[];   // drain: each piece that leaves and what is left after it
  pans?: { file: string; label: string }[];   // scale: [right pan, left pan] — the right one is the heavier, it tips down
  pins?: number;                         // map: how many pins drop
  name?: string; handle?: string; bio?: string; img?: string; followers?: number;   // profile · type: a round photo over the quote
  skip?: string[];                       // type: spoken words left out of the animation ("text#n") — they stay in the sound
  quote?: boolean; typing?: boolean;     // type: ״ ״ round the line · a key click on every word as it lands
  drama?: boolean;                       // type: slow and heavy — words land from a blurred zoom, slow push, long exit (דין r1 3.11: «יותר חלק ודרמטי»)
  stops?: { at: number; lon: number; lat: number; flag: string; name: string }[];   // world: the places the map flies to
  items?: { at: number; label: string; mark?: "v" | "x"; markAt?: number; icon?: string; x?: number; y?: number;
    sub?: string; file?: string; ih?: number; y0?: number; y1?: number }[];   // notes: the grey line under a note · site: a page image, its pixel height and scroll (image px)
  shine?: boolean;                       // glass: the word revealed letter-light, a light sweep across the gold (round 8, «אורגנית»)
  orbit?: { x: number; y: number };     // brands: the tiles float around the speaker — each comes out of this point (his face) to its own x/y   // checks / brands: the lines (and icons) as they are said
  title?: string;                        // checks: a small gold heading over the list
  max?: number;                          // checks (centred): at most this many lines at once — the oldest rolls up and out as a new one lands
  center?: boolean;                      // checks: the block centred and clear of Instagram's right-hand buttons (round 5: «שיהיה ממורכז ובמקום שאפשר לקרוא»)
  caps?: boolean;                        // checks / brands: true = the captions stay under it (round 5: «0:48 הכתוביות נעלמות»)
};

const sec = () => { const { fps } = useVideoConfig(); return useCurrentFrame() / fps; };
const GOLD = "linear-gradient(180deg, #FFF1C4 0%, #F6C453 45%, #B7811B 100%)";
const GRADE: Record<string, string> = {
  warm: "contrast(1.08) saturate(0.92) sepia(0.12) brightness(0.95)",
  mono: "grayscale(1) contrast(1.15) brightness(0.9)",
  cool: "contrast(1.06) saturate(0.85) hue-rotate(-6deg) brightness(0.95)",
  none: "none",
};

/** directional blur as an SVG filter (CSS blur() is round; a whip needs it along the motion) */
const DirBlur: React.FC<{ id: string; x: number; y: number }> = ({ id, x, y }) => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <filter id={id} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation={`${Math.max(0, x)} ${Math.max(0, y)}`} /></filter>
  </svg>
);

/** the B-roll footage itself: plays from ss, a slow push with a breath of drift, graded to sit with the cameras */
const Footage: React.FC<{ b: AeBeat; w?: number; h?: number; extra?: string }> = ({ b, w = 1080, h = 1920, extra = "" }) => {
  const t = sec();
  const { fps } = useVideoConfig();
  const u = (t - b.from) / Math.max(0.1, b.to - b.from);
  const s = b.fit ? 1 : 1.04 + (b.push ?? 0.08) * inOut(Math.min(1, Math.max(0, u)));
  const dx = b.fit ? 0 : noise2D("fx" + b.from, t * 0.25, 0) * 10, dy = b.fit ? 0 : noise2D("fy" + b.from, 0, t * 0.25) * 10;
  const pos = b.pos ?? 50, z = b.zoom ?? 1;
  return (
    <Sequence from={Math.round(b.from * fps) - 8} layout="none">
      {b.focus ? (() => {
        // a point of the 9:16 source lands at (centre, ty) of the box: cover-size, then zoom around it, clamped to the box
        const ar = 9 / 16, iw0 = w / h > ar ? w : h * ar, ih0 = w / h > ar ? w / ar : h, Z = s * z, iw = iw0 * Z, ih = ih0 * Z;
        const left = Math.min(0, Math.max(w - iw, w / 2 - b.focus.x * iw)) + dx, top = Math.min(0, Math.max(h - ih, h * (b.focus.ty ?? 0.4) - b.focus.y * ih)) + dy;
        return <OffthreadVideo src={staticFile(b.file!)} startFrom={Math.max(0, Math.round(((b.ss ?? 0) - 8 / fps * (b.speed ?? 1)) * fps))} playbackRate={b.speed ?? 1} muted
          style={{ position: "absolute", left, top, width: iw, height: ih, filter: `${GRADE[b.grade ?? "warm"]} ${extra}`.trim() }} />;
      })() : /\.(jpe?g|png|webp)$/i.test(b.file!) ? <Img src={staticFile(b.file!)} style={{ position: "absolute", inset: 0, width: w, height: h, objectFit: "cover",
        objectPosition: `50% ${pos}%`, transformOrigin: `50% ${pos}%`, transform: `translate(${dx}px, ${dy}px) scale(${s * z})`,
        filter: `${GRADE[b.grade ?? "warm"]} ${extra}`.trim() }} /> :
      <OffthreadVideo src={staticFile(b.file!)} startFrom={Math.max(0, Math.round(((b.ss ?? 0) - 8 / fps * (b.speed ?? 1)) * fps))} playbackRate={b.speed ?? 1} muted
        style={{ position: "absolute", inset: 0, width: w, height: h, objectFit: "cover", objectPosition: `50% ${pos}%`,
          transformOrigin: `50% ${pos}%`, transform: `translate(${dx}px, ${dy}px) scale(${s * z})`,
          filter: `${GRADE[b.grade ?? "warm"]} ${extra}`.trim() }} />}
    </Sequence>
  );
};

/** how far a transition is: 0 = not on screen, 1 = settled */
const IN_D: Record<AeIn, number> = { cut: 0.001, fade: 0.3, zoom: 0.42, whip: 0.36, iris: 0.5, rise: 0.45 };
const dur = (k: AeIn, b: AeBeat) => (k === "fade" && b.fd ? b.fd : IN_D[k]);
const enter = (t: number, b: AeBeat) => ramp(t, b.from, dur(b.in ?? "zoom", b), inOut);
const leave = (t: number, b: AeBeat) => ramp(t, b.to - dur(b.out ?? "fade", b), dur(b.out ?? "fade", b), inOut);
const vel = (p: number) => Math.sin(Math.PI * Math.min(1, Math.max(0, p)));   // 0 at rest, 1 mid-move — for the blur

/** a transition applied to a full-frame layer: returns style for p = in-progress (0→1) and q = out-progress (0→1) */
const transit = (kind: AeIn, p: number, outKind: AeIn, q: number, dir: number, id: string) => {
  const st: React.CSSProperties = {};
  const tf: string[] = [];
  let bx = 0, by = 0, opacity = 1;
  const apply = (k: AeIn, x: number, entering: boolean) => {   // x: 0 = off, 1 = on
    const v = vel(entering ? x : 1 - x);
    if (k === "fade") opacity *= x;
    if (k === "zoom") { tf.push(`scale(${entering ? 1 + 0.35 * (1 - x) : 1 - 0.12 * (1 - x)})`); opacity *= Math.min(1, x * 1.6); bx += 14 * v; by += 14 * v; }
    if (k === "whip") { tf.push(`translateX(${(entering ? -dir : dir) * 1150 * (1 - x)}px)`); bx += 36 * v; }
    if (k === "rise") { tf.push(`translateY(${(entering ? 1 : -1) * 1980 * (1 - x)}px)`); by += 34 * v; }
    if (k === "iris") st.clipPath = `circle(${(x * 120).toFixed(2)}% at 50% 46%)`;
  };
  apply(kind, p, true);
  if (q > 0) apply(outKind, 1 - q, false);
  st.transform = tf.join(" ");
  st.opacity = opacity;
  if (bx > 0.2 || by > 0.2) st.filter = `url(#${id})`;
  return { st, bx, by };
};

/** full-frame B-roll */
export const AeClip: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const id = `ae-c-${Math.round(b.from * 100)}`;
  const { st, bx, by } = transit(b.in ?? "zoom", enter(t, b), b.out ?? "fade", leave(t, b), b.dir ?? 1, id);
  return (
    <AbsoluteFill>
      <DirBlur id={id} x={bx} y={by} />
      <AbsoluteFill style={{ ...st, overflow: "hidden", background: "#000" }}>
        <Footage b={b} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── shrink: camera into a window on top, the B-roll card below ────────────────────────────────────────────────
export const SHRINK = { top: 54, side: 40, camBottom: 930, cardTop: 960, cardBottom: 1866, r: 44, lift: 150 };
/** the camera wrapper's style at time t (Reel wraps every camera shot in it) */
export const shrinkStyle = (t: number, beats: AeBeat[]): React.CSSProperties => {
  const b = beats.find((x) => x.k === "shrink" && t >= x.from - 0.01 && t <= x.to + 0.01);
  if (!b) return {};
  const k = enter(t, b) * (1 - ramp(t, b.to - 0.45, 0.45, inOut));
  const S = SHRINK;
  const top = S.top * k, side = S.side * k, bottom = (1920 - S.camBottom) * k;
  return { clipPath: `inset(${top + S.lift * k}px ${side}px ${bottom - S.lift * k}px ${side}px round ${S.r * k}px)`, transform: `translateY(${-S.lift * k}px)` };
};
export const inShrink = (t: number, beats: AeBeat[]) => beats.some((x) => x.k === "shrink" && t >= x.from && t < x.to);

/** what lies under the camera window during a shrink: a dark stage with a gold glow, and the B-roll card rising in */
export const AeShrinkStage: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = enter(t, b), q = ramp(t, b.to - 0.45, 0.45, inOut), S = SHRINK;
  const c = ramp(t, b.from + 0.12, 0.5, inOut);   // the card follows the window by a beat
  const id = `ae-s-${Math.round(b.from * 100)}`;
  const v = vel(c) * 30 + vel(q) * 30;
  const glow = 0.5 + 0.5 * noise2D("g" + b.from, t * 0.4, 0);
  const lab = ramp(t, b.from + 0.55, 0.4, inOut) * (1 - q);
  return (
    <AbsoluteFill style={{ opacity: Math.min(1, k * 3) }}>
      <AbsoluteFill style={{ background: "#07080A" }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 72%, rgba(246,196,83,${0.16 + 0.08 * glow}) 0%, rgba(246,196,83,0) 55%)` }} />
      <DirBlur id={id} x={0} y={v} />
      <div style={{ position: "absolute", left: S.side, right: S.side, top: S.cardTop, height: S.cardBottom - S.cardTop, borderRadius: S.r, overflow: "hidden",
        transform: `translateY(${(1 - c) * 1000 + q * 1000}px)`, filter: v > 0.3 ? `url(#${id})` : undefined,
        boxShadow: "0 30px 80px rgba(0,0,0,0.7), 0 0 0 2px rgba(246,196,83,0.55)" }}>
        <Footage b={b} w={1080 - 2 * S.side} h={S.cardBottom - S.cardTop} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 60%, rgba(0,0,0,0.45) 100%)" }} />
        {b.label && <div style={{ position: "absolute", bottom: 46, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: lab,
          transform: `translateY(${(1 - lab) * 24}px)` }}>
          <div style={{ fontFamily: font, fontWeight: 900, fontSize: 52, color: "#1a1206", background: GOLD, padding: "12px 34px 14px", borderRadius: 999,
            direction: "rtl", boxShadow: "0 10px 30px rgba(0,0,0,0.45)" }}>{b.label}</div>
        </div>}
      </div>
    </AbsoluteFill>
  );
};
/** the hairline around the camera window, over the camera */
export const AeShrinkFrame: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from || t > b.to) return null;
  const k = enter(t, b) * (1 - ramp(t, b.to - 0.45, 0.45, inOut)), S = SHRINK;
  return <div style={{ position: "absolute", left: S.side, right: S.side, top: S.top, height: S.camBottom - S.top, borderRadius: S.r,
    boxShadow: "0 0 0 2px rgba(246,196,83,0.55), 0 30px 80px rgba(0,0,0,0.6)", opacity: k * k }} />;
};

// ── card: the B-roll rises into the strip under the captions (אורח B 29.10.2026: «הכתוביות במקום קבוע שלא זז, ומתחתיהן
// הלוגואים או הבירולים — כשנכנס משהו כזה, פייד אאוט ללוגואים»). The camera stays full frame; only the strip below the
// captions changes, so the faces and the caption line never move.
export type CardBox = { top: number; bottom: number; side: number; r: number };
export const CARD: CardBox = { top: 1290, bottom: 1858, side: 44, r: 38 };
export const AeCard: React.FC<{ b: AeBeat; font: string; box?: CardBox }> = ({ b, font, box = CARD }) => {
  const t = sec();
  // chained cards (round 8: «שהבירולים יתחלפו בפייד מאחד לשני»): "fade" in/out = the frame stays put and the pictures cross-fade
  const fin = b.in === "fade", fout = b.out === "fade";
  if (t < b.from - (fin ? 0.27 : 0.02) || t > b.to + (fout ? 0.3 : 0.02)) return null;
  const c = fin ? 1 : ramp(t, b.from, 0.5, inOut), q = fout ? 0 : ramp(t, b.to - 0.4, 0.4, inOut);
  const alpha = (fin ? ramp(t, b.from - 0.25, 0.3, inOut) : 1) * (fout ? 1 - ramp(t, b.to, 0.3, inOut) : 1);
  const id = `ae-k-${Math.round(b.from * 100)}`;
  const v = vel(c) * 24 + vel(q) * 24;
  const lab = ramp(t, b.from + 0.45, 0.4, inOut) * (1 - q);
  const H = box.bottom - box.top;
  return (
    <AbsoluteFill>
      {/* a soft floor under the strip, so the card sits on the picture rather than on a busy shirt */}
      <AbsoluteFill style={{ opacity: c * (1 - q), background: `linear-gradient(180deg, rgba(0,0,0,0) ${box.top - 160}px, rgba(0,0,0,0.55) ${box.top + 40}px, rgba(0,0,0,0.7) 100%)` }} />
      <DirBlur id={id} x={0} y={v} />
      <div style={{ position: "absolute", left: box.side, right: box.side, top: box.top, height: H, borderRadius: box.r, overflow: "hidden", opacity: alpha,
        transform: `translateY(${(1 - c) * (1920 - box.top + 40) + q * (1920 - box.top + 40)}px) scale(${0.94 + 0.06 * c})`, transformOrigin: "50% 0%",
        filter: v > 0.3 ? `url(#${id})` : undefined, boxShadow: "0 24px 70px rgba(0,0,0,0.7), 0 0 0 2px rgba(246,196,83,0.55)" }}>
        <Footage b={b} w={1080 - 2 * box.side} h={H} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 62%, rgba(0,0,0,0.4) 100%)" }} />
        {b.label && <div style={{ position: "absolute", bottom: 34, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: lab,
          transform: `translateY(${(1 - lab) * 20}px)` }}>
          <div style={{ fontFamily: font, fontWeight: 900, fontSize: 46, color: "#1a1206", background: GOLD, padding: "10px 30px 12px", borderRadius: 999,
            direction: "rtl", boxShadow: "0 10px 30px rgba(0,0,0,0.45)" }}>{b.label}</div>
        </div>}
      </div>
    </AbsoluteFill>
  );
};

// ── kinetic type ─────────────────────────────────────────────────────────────────────────────────────────────
type Line = { words: Word[]; text: string };
const MAXC = 13;
const linesOf = (ws: Word[], big: Record<string, string>, MAXC = 13) => {
  const out: Line[] = [];
  let cur: Word[] = [];
  const len = (a: Word[]) => a.reduce((s, w) => s + (big[w.text] ?? w.text).length + 1, 0);
  ws.forEach((w) => {
    const isBig = big[w.text] !== undefined;
    if (cur.length && (isBig || cur.some((x) => big[x.text] !== undefined) || len([...cur, w]) > MAXC || /[.?!]$/.test(cur[cur.length - 1].text))) {
      out.push({ words: cur, text: cur.map((x) => big[x.text] ?? x.text).join(" ") }); cur = [];
    }
    cur.push(w);
  });
  if (cur.length) out.push({ words: cur, text: cur.map((x) => big[x.text] ?? x.text).join(" ") });
  return out;
};
/** one screen of a long line: rows of even width, a break after punctuation preferred, the same type size throughout */
const balancedLines = (ws: Word[], rowsAt?: string[]): Line[] => {
  const mk = (a: Word[]): Line => ({ words: a, text: a.map((x) => x.text).join(" ") });
  if (rowsAt?.length) {
    const out: Line[] = []; let cur: Word[] = [];
    const seen: Record<string, number> = {};   // "word" breaks on every occurrence, "word#1" only on that one
    ws.forEach((w) => { const n = seen[w.text] ?? 0; seen[w.text] = n + 1;
      if (cur.length && (rowsAt.includes(w.text) || rowsAt.includes(`${w.text}#${n}`))) { out.push(mk(cur)); cur = []; } cur.push(w); });
    if (cur.length) out.push(mk(cur));
    return out;
  }
  const n = ws.length, len = (i: number, j: number) => ws.slice(i, j).map((w) => w.text).join(" ").length;
  const total = len(0, n), R = Math.max(1, Math.ceil(total / 17)), avg = total / R;
  const best: { c: number; prev: number }[][] = Array.from({ length: R + 1 }, () => Array.from({ length: n + 1 }, () => ({ c: Infinity, prev: 0 })));
  best[0][0] = { c: 0, prev: 0 };
  for (let r = 1; r <= R; r++) for (let j = 1; j <= n; j++) for (let i = 0; i < j; i++) {
    if (best[r - 1][i].c === Infinity) continue;
    const l = len(i, j), over = l > 19 ? (l - 19) * 60 : 0;
    const punct = j < n && /[.,?!]$/.test(ws[j - 1].text) ? -18 : 0, orphan = j - i === 1 && l < 5 ? 40 : 0;
    const c = best[r - 1][i].c + (l - avg) ** 2 + over + punct + orphan;
    if (c < best[r][j].c) best[r][j] = { c, prev: i };
  }
  const out: Line[] = []; let j = n;
  for (let r = R; r >= 1; r--) { const i = best[r][j].prev; out.unshift(mk(ws.slice(i, j))); j = i; }
  return out.filter((l) => l.words.length);
};
const pagesOf = (lines: Line[]) => {
  const pages: Line[][] = [];
  lines.forEach((l) => { const p = pages[pages.length - 1]; if (!p || p.length >= 3 || /[.?!]$/.test(p[p.length - 1].words.slice(-1)[0].text)) pages.push([l]); else p.push(l); });
  return pages;
};

const Count: React.FC<{ value: string; at: number; size: number; font: string }> = ({ value, at, size, font }) => {
  const t = sec();
  const n = Number(value.replace(/[^\d.]/g, ""));
  // a year is a date, not an amount — it lands whole («408» on the way to 2008, round 7)
  const run = n >= 1900 && n <= 2100 && !value.includes(",") ? 1 : ramp(t, at - 0.05, 0.7, inOut);
  const shown = Number.isFinite(n) && n > 0 ? value.replace(/[\d,.]+/, (m) => {
    const v = Math.round(n * run);
    return m.includes(",") ? v.toLocaleString("en-US") : String(v);
  }) : value;
  // a number with Hebrew words reads right to left («10 שנים» came out «שנים 10», ניב r10 3.11)
  return <span style={{ fontFamily: font, fontWeight: 900, fontSize: size, lineHeight: 0.95, background: GOLD, WebkitBackgroundClip: "text", color: "transparent",
    direction: /[\u0590-\u05FF]/.test(value) ? "rtl" : "ltr", display: "inline-block", filter: "drop-shadow(0 10px 30px rgba(246,196,83,0.35))" }}>{shown}</span>;
};

export const AeType: React.FC<{ b: AeBeat; font: string; who: Record<string, string> }> = ({ b, font, who }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const big = b.big ?? {}, gold = new Set(b.gold ?? []);
  const ws = b.words ?? [];
  const pages = b.one ? [balancedLines(ws, b.rowsAt)] : pagesOf(linesOf(ws, big));
  const D = b.drama ? 1 : 0;
  const k = ramp(t, b.from - 0.25 * D, 0.35 + 0.4 * D, inOut) * (b.hold ? 1 : 1 - ramp(t, b.to - 0.3 - 0.35 * D, 0.3 + 0.35 * D, inOut));
  const textOut = b.hold ? 0 : ramp(t, b.to - 0.36 - 0.45 * D, 0.14 + 0.3 * D, inOut);   // the words leave before the blur does: never text on a sharp face
  const push = D ? 1 + 0.07 * ramp(t, b.from, Math.max(0.5, b.to - b.from), (v) => v) : 1;
  const pi = Math.max(0, pages.findIndex((p, i) => t >= p[0].words[0].at - 0.12 && (i === pages.length - 1 || t < pages[i + 1][0].words[0].at - 0.12)));
  const id = `ae-t-${Math.round(b.from * 100)}`;
  return (
    <AbsoluteFill style={{ opacity: D ? 1 : k }}>
      {b.bg ? <AbsoluteFill style={{ overflow: "hidden" }}><Footage b={{ ...b, file: b.bg, ss: b.bgSs }} extra={`blur(${b.bgBlur ?? 18}px) brightness(${(b.bgBlur ?? 18) < 10 ? 0.5 : 0.42})`} /></AbsoluteFill>
        : D ? (() => { const bf = `blur(${(26 * k).toFixed(1)}px) brightness(${(1 - 0.62 * k).toFixed(3)}) saturate(${(1 - 0.3 * k).toFixed(3)})`;   // drama: the blur itself eases out, no opacity pop
          return <AbsoluteFill style={{ backdropFilter: bf, WebkitBackdropFilter: bf }} />; })()
        : <AbsoluteFill style={{ backdropFilter: "blur(26px) brightness(0.38) saturate(0.7)", WebkitBackdropFilter: "blur(26px) brightness(0.38) saturate(0.7)" }} />}
      <AbsoluteFill style={{ opacity: D ? k : 1 }}>
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 30%, rgba(0,0,0,0.55) 100%)" }} />
        <Bokeh seed={b.from} />
      </AbsoluteFill>
      {b.img && (() => {   // who said it — a round photo over the quote (דין r4: «+ תמונה של אייל»)
        const p = ramp(t, b.from + 0.05, 0.45, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
        return <div style={{ position: "absolute", left: 540 - 150, top: 150, width: 300, height: 300, borderRadius: 150, overflow: "hidden", opacity: Math.min(1, p * 2) * (1 - textOut),
          transform: `scale(${0.6 + 0.4 * p})`, boxShadow: "0 0 0 6px #F6C453, 0 24px 60px rgba(0,0,0,0.6)" }}>
          <Img src={staticFile(b.img)} style={{ width: 300, height: 300, objectFit: "cover" }} /></div>;
      })()}
      {pages.map((page, i) => {
        if (Math.abs(i - pi) > 1) return null;
        const p0 = page[0].words[0].at - 0.12;
        const next = pages[i + 1]?.[0].words[0].at;
        const out = next ? ramp(t, next - 0.2, 0.28, inOut) : 0;
        if (t < p0 - 0.05 || out >= 1) return null;
        const sizes = page.map((l) => {
          const isBig = l.words.some((w) => big[w.text] !== undefined);
          return Math.min(isBig ? 330 : 150, fitText({ text: l.text, withinWidth: 900, fontFamily: font, fontWeight: "900" }).fontSize);
        });
        if (b.one) { const m = Math.min(...sizes); sizes.forEach((_, j) => { sizes[j] = m; }); }   // one size down the whole block
        const H0 = sizes.reduce((a, s) => a + s * 1.08, 0);
        if (H0 > 1150) sizes.forEach((v, j) => { sizes[j] = v * 1150 / H0; });   // one screen of a long line: it all fits
        const H = sizes.reduce((a, s) => a + s * 1.08, 0);
        let y = b.img ? Math.max(500, 1020 - H / 2) : 960 - H / 2;
        const lastAt = page[page.length - 1].words.slice(-1)[0].at;
        const line = ramp(t, lastAt, 0.5, inOut);
        return (
          <CameraMotionBlur key={i} shutterAngle={180} samples={5}>
            <AbsoluteFill style={{ transform: `translateY(${-90 * out}px) scale(${push * (1 + 0.05 * D * textOut)})`, opacity: (1 - out) * (1 - textOut), filter: out + D * textOut > 0 ? `blur(${10 * out + 14 * D * textOut}px)` : undefined }}>
              {page.map((l, li) => {
                const top = y; y += sizes[li] * 1.08;
                return (
                  <div key={li} style={{ position: "absolute", top, left: 60, right: 60, height: sizes[li] * 1.08, overflow: "hidden", display: "flex",
                    justifyContent: "center", alignItems: "center", direction: "rtl", gap: sizes[li] * 0.24 }}>
                    {l.words.map((w, wi) => {
                      const r = ramp(t, w.at - 0.08 - 0.1 * D, 0.34 + 0.4 * D, inOut);
                      const isBig = big[w.text] !== undefined;
                      const color = gold.has(w.text) ? undefined : who[w.who] ?? "#fff";
                      return (
                        <span key={wi} style={{ display: "inline-block", opacity: Math.min(1, r * 2), ...(D
                          ? { transform: `scale(${1 + 0.45 * (1 - r)})`, filter: r < 1 ? `blur(${16 * (1 - r)}px)` : undefined }
                          : { transform: `translateY(${(1 - r) * 105}%) scale(${0.96 + 0.04 * r})` }) }}>
                          {isBig ? <Count value={big[w.text]} at={w.at} size={sizes[li]} font={font} />
                            : <span style={{ fontFamily: font, fontWeight: 900, fontSize: sizes[li], lineHeight: 1, letterSpacing: "-0.01em",
                              ...(color ? { color } : { background: GOLD, WebkitBackgroundClip: "text", color: "transparent" }),
                              textShadow: color ? "0 8px 30px rgba(0,0,0,0.5)" : undefined }}>{w.text}</span>}
                        </span>
                      );
                    })}
                  </div>
                );
              })}
              <svg style={{ position: "absolute", left: 340, top: y + 26, width: 400, height: 10 }} viewBox="0 0 400 10">
                <path d="M0 5 L400 5" stroke="#F6C453" strokeWidth={4} strokeLinecap="round" {...evolvePath(line, "M0 5 L400 5")} fill="none" />
              </svg>
            </AbsoluteFill>
          </CameraMotionBlur>
        );
      })}
      <DirBlur id={id} x={0} y={0} />
    </AbsoluteFill>
  );
};

/** soft gold lights drifting behind the type — depth, never busy */
const Bokeh: React.FC<{ seed: number }> = ({ seed }) => {
  const t = sec();
  return (
    <AbsoluteFill style={{ mixBlendMode: "screen" }}>
      {Array.from({ length: 9 }, (_, i) => {
        const x = 540 + 520 * noise2D(`bx${seed}${i}`, t * 0.06, i), y = 960 + 900 * noise2D(`by${seed}${i}`, i, t * 0.05);
        const r = 70 + 90 * ((i * 37) % 10) / 10, a = 0.10 + 0.08 * (0.5 + 0.5 * noise2D(`ba${seed}${i}`, t * 0.3, i));
        return <div key={i} style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: "50%",
          background: `radial-gradient(circle, rgba(246,196,83,${a}) 0%, rgba(246,196,83,${a * 0.5}) 45%, rgba(246,196,83,0) 70%)`, filter: "blur(6px)" }} />;
      })}
    </AbsoluteFill>
  );
};

// ── light leak + grain ───────────────────────────────────────────────────────────────────────────────────────
export const Leak: React.FC<{ at: number; d?: number; seed?: number }> = ({ at, d = 0.8, seed = 0 }) => {
  const t = sec();
  if (t < at - 0.05 || t > at + d) return null;
  const u = (t - at) / d, k = Math.sin(Math.PI * Math.min(1, Math.max(0, u)));
  const x = -20 + 140 * u, y = 30 + 20 * noise2D("lk" + seed, u, 0);
  return <AbsoluteFill style={{ mixBlendMode: "screen", opacity: 0.85 * k,
    background: `radial-gradient(ellipse 60% 45% at ${x}% ${y}%, rgba(255,190,110,0.85) 0%, rgba(255,120,40,0.35) 40%, rgba(0,0,0,0) 75%)` }} />;
};

export const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.32) 100%)" }} />
      <svg width="1080" height="1920" style={{ position: "absolute", inset: 0, opacity: 0.07, mixBlendMode: "overlay" }}>
        <filter id="ae-grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f % 30} /></filter>
        <rect width="1080" height="1920" filter="url(#ae-grain)" />
      </svg>
    </AbsoluteFill>
  );
};

// ── round 7 pieces: a number over the picture, bills, red lights, a calendar, glass that breaks ─────────────────
/** a big gold number laid over the picture — counted up, with a short label under it */
export const AeNum: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const p = ramp(t, b.from, 0.45, inOut), q = ramp(t, b.to - 0.35, 0.35, inOut);
  const y = b.y ?? 1480, size = b.size ?? 230;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: p * (1 - q) }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 22% at 50% ${(y / 1920) * 100}%, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0) 100%)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: y - size * 0.62, display: "flex", flexDirection: "column", alignItems: "center",
        transform: `translateY(${(1 - p) * 60 - q * 40}px) scale(${0.9 + 0.1 * p})`, filter: p < 1 || q > 0 ? `blur(${(1 - p) * 14 + q * 10}px)` : undefined }}>
        <Count value={b.text ?? "0"} at={b.from + 0.05} size={size} font={font} />
        {b.label && <div style={{ fontFamily: font, fontWeight: 800, fontSize: size * 0.3, color: "#fff", marginTop: size * 0.04, direction: "rtl",
          textShadow: "0 6px 24px rgba(0,0,0,0.7)", opacity: ramp(t, b.from + 0.35, 0.35, inOut) }}>{b.label}</div>}
      </div>
    </AbsoluteFill>
  );
};

const rnd = (i: number) => { const x = Math.sin(i * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
/** bills falling over the whole frame (the צומת 20 teaser's money rain), each once, thinning out at the end */
export const AeRain: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from || t > b.to + 0.4) return null;
  const out = ramp(t, b.to, 0.4);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 1 - out }}>
      {Array.from({ length: b.count ?? 36 }, (_, i) => {
        const sp = b.speed ?? 1, d = 0.45 + 0.55 * rnd(i + 3), u = (t - (b.from + rnd(i + 11) * 1.2 / sp)) * sp;
        if (u < 0) return null;
        const y = -260 + u * (620 + 420 * d), x = rnd(i + 5) * 1080 + Math.sin(u * 2.2 + i) * 60 * d;
        const w = 200 + 190 * d;
        return <Img key={i} src={staticFile(b.file ?? "ig/bill.png")} style={{ position: "absolute", left: x - w / 2, top: y, width: w,
          transform: `rotate(${(rnd(i) - 0.5) * 80 + u * 60 * (rnd(i + 2) - 0.5)}deg) rotateX(${Math.sin(u * 5 + i) * 55}deg)`,
          filter: `blur(${(1 - d) * 3}px) drop-shadow(0 10px 18px rgba(0,0,0,0.35))`, zIndex: Math.round(d * 10) }} />;
      })}
    </AbsoluteFill>
  );
};

/** red alarm lights sweeping in from both sides over a loss — slow, two pulses a second, never a flash */
export const AeGlow: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  // round 8 («שזה יראה יותר דרמטי»): the frame goes red — a deep red grade, two alarm beams sweeping from the top corners and a
  // heavy red vignette that breathes with them. Slow (0.9 Hz), no flashes.
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.45, 0.45, inOut));
  const u = t - b.from, w = 0.5 + 0.5 * Math.sin(u * Math.PI * 2 * 0.9);
  const a1 = -35 + 70 * (0.5 + 0.5 * Math.sin(u * 2.2)), a2 = 35 - 70 * (0.5 + 0.5 * Math.sin(u * 2.2 + 1.4));
  const beam = (x: number, ang: number) => (
    <div style={{ position: "absolute", left: x - 700, top: -160, width: 1400, height: 2300, transformOrigin: "50% 0%", transform: `rotate(${ang}deg)`,
      background: "conic-gradient(from 168deg at 50% 0%, rgba(255,0,0,0) 0deg, rgba(255,40,30,0.75) 12deg, rgba(255,0,0,0) 24deg)", filter: "blur(18px)" }} />);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: k }}>
      <AbsoluteFill style={{ background: "rgba(200,10,10,1)", mixBlendMode: "multiply", opacity: 0.38 + 0.12 * w }} />
      <AbsoluteFill style={{ mixBlendMode: "screen", opacity: 0.55 + 0.35 * w }}>{beam(0, a1)}{beam(1080, a2)}</AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 30%, rgba(90,0,0,${0.55 + 0.2 * w}) 100%)` }} />
    </AbsoluteFill>
  );
};

/** a calendar of three pages — today, tomorrow, the day after — each lit and filled as it is said, a tick on the done ones */
export const AeCal: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.4, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const days = b.days ?? [];
  const cur = days.reduce((a, d, i) => (t >= d.at - 0.1 ? i : a), -1);
  const W = 316, G = 20, X0 = (1080 - 3 * W - 2 * G) / 2, Y = 300, H = 600;
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <AbsoluteFill style={{ backdropFilter: "blur(24px) brightness(0.36) saturate(0.7)", WebkitBackdropFilter: "blur(24px) brightness(0.36) saturate(0.7)" }} />
      <Bokeh seed={b.from} />
      {/* the timeline under the pages: a gold line that runs to the page being said */}
      <svg style={{ position: "absolute", left: 0, top: Y + H + 70, width: 1080, height: 40 }} viewBox="0 0 1080 40">
        <path d={`M${1080 - X0 - W / 2} 20 L${X0 + W / 2} 20`} stroke="rgba(255,255,255,0.18)" strokeWidth={4} strokeLinecap="round" />
        {cur >= 0 && <path d={`M${1080 - X0 - W / 2} 20 L${1080 - X0 - W / 2 - (W + G) * Math.min(2, cur + ramp(t, days[cur].at, 0.5, inOut) - 1)} 20`}
          stroke="#F6C453" strokeWidth={5} strokeLinecap="round" />}
      </svg>
      {days.map((d, i) => {
        const x = 1080 - X0 - W - i * (W + G);                 // right to left: today is the first page in Hebrew
        const p = ramp(t, b.from + 0.1 + i * 0.12, 0.45, inOut);
        const lit = ramp(t, d.at - 0.1, 0.4, inOut), done = i < cur ? 1 : 0;
        const lift = lit * (1 - 0.5 * ramp(t, (days[i + 1]?.at ?? 1e9) - 0.1, 0.4, inOut));
        return (
          <div key={i} style={{ position: "absolute", left: x, top: Y - 40 * lift + (1 - p) * 80, width: W, height: H, opacity: p, borderRadius: 30, overflow: "hidden",
            background: "linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.06))", border: `2px solid rgba(246,196,83,${0.25 + 0.65 * lit})`,
            boxShadow: `0 30px 60px rgba(0,0,0,0.45), 0 0 ${40 * lit}px rgba(246,196,83,${0.35 * lit})`, backdropFilter: "blur(10px)", direction: "rtl" }}>
            <div style={{ height: 110, background: `linear-gradient(180deg, rgba(246,196,83,${0.35 + 0.6 * lit}), rgba(183,129,27,${0.3 + 0.6 * lit}))`,
              display: "flex", alignItems: "center", justifyContent: "center", fontFamily: font, fontWeight: 900, fontSize: 56, color: lit > 0.5 ? "#1a1206" : "#fff" }}>{d.title}</div>
            <div style={{ position: "absolute", top: 110, left: 0, right: 0, height: 190, display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: font, fontWeight: 900, fontSize: 170, color: "rgba(255,255,255,0.92)", direction: "ltr" }}>{i + 1}</div>
            <div style={{ position: "absolute", top: 310, left: 18, right: 18, textAlign: "center", fontFamily: font, fontWeight: 800, fontSize: 54, lineHeight: 1.12,
              color: "#fff", opacity: lit, transform: `translateY(${(1 - lit) * 24}px)` }}>{d.text}</div>
            {done > 0 && <svg style={{ position: "absolute", left: W / 2 - 40, top: H - 110, width: 80, height: 80 }} viewBox="0 0 68 68">
              <circle cx={34} cy={34} r={30} fill="rgba(246,196,83,0.95)" />
              <path d="M20 35 L30 45 L49 24" stroke="#1a1206" strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round"
                {...evolvePath(ramp(t, days[i + 1].at - 0.1, 0.35, inOut), "M20 35 L30 45 L49 24")} />
            </svg>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const SHARDS = [[0, 0, 38, 0, 30, 46, 0, 58], [38, 0, 100, 0, 72, 40, 30, 46], [72, 40, 100, 0, 100, 62], [0, 58, 30, 46, 46, 100, 0, 100],
  [30, 46, 72, 40, 60, 100, 46, 100], [72, 40, 100, 62, 100, 100, 60, 100]];
/** a big number in clear glass beside the speaker (never over the face); on `shatter` it cracks, then falls in shards */
export const AeGlass: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  const sh = b.shatter ?? b.to, keep = sh > b.to + 0.01;   // a shatter after its window = it never breaks, it leaves at `to` (ניב r10)
  if (t < b.from - 0.02 || t > (keep ? b.to + 0.35 : sh + 1.6)) return null;
  const gone = keep ? ramp(t, b.to, 0.3, inOut) : 0;
  const p = ramp(t, b.from, 0.55, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
  const x = b.x ?? 50, y = b.y ?? 330, w = b.w ?? 380, h = b.h ?? 330, size = b.size ?? 230;
  const red = ramp(t, sh - 0.12, 0.12), brk = Math.max(0, t - sh);
  const face = (
    <div style={{ position: "absolute", inset: 0, borderRadius: b.shine ? 44 : 34, background: b.shine ? "linear-gradient(160deg, rgba(28,28,30,0.66), rgba(10,10,12,0.5))"
        : "linear-gradient(135deg, rgba(255,255,255,0.30), rgba(255,255,255,0.07))",
      border: b.shine ? "2px solid rgba(246,196,83,0.45)" : "2px solid rgba(255,255,255,0.55)",
      boxShadow: b.shine ? "0 28px 70px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.22), 0 0 40px rgba(246,196,83,0.18)" : "0 30px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.7)", backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", direction: "rtl" }}>
      {b.shine ? (() => {
        // round 8 (reel 2, «שהמילה אורגנית תהיה גדולה ובולטת יותר, עם אנימציה יוקרתית»): the word opens from blur and wide
        // tracking, a white light runs across the gold once it has landed, and the gold breathes a soft glow
        const r = ramp(t, b.from + 0.05, 0.7, inOut), sw = ramp(t, b.from + 0.55, 0.9, inOut), gl = 0.5 + 0.5 * Math.sin((t - b.from) * 3.2);
        const st: React.CSSProperties = { fontFamily: font, fontWeight: 900, fontSize: size, lineHeight: 1.05, direction: "rtl", whiteSpace: "nowrap",
          letterSpacing: (1 - r) * 0.12 * size, padding: "0 0.06em" };
        return <div style={{ position: "relative", filter: `blur(${(1 - r) * 14}px) drop-shadow(0 0 ${18 + 16 * gl}px rgba(246,196,83,${0.35 + 0.2 * gl}))`, opacity: Math.min(1, r * 1.6) }}>
          <div style={{ ...st, background: GOLD, WebkitBackgroundClip: "text", color: "transparent" }}>{b.text}</div>
          <div style={{ ...st, position: "absolute", inset: 0, color: "transparent", WebkitBackgroundClip: "text",
            backgroundImage: `linear-gradient(105deg, rgba(255,255,255,0) ${-30 + 160 * sw}%, rgba(255,255,255,0.95) ${-15 + 160 * sw}%, rgba(255,255,255,0) ${0 + 160 * sw}%)` }}>{b.text}</div>
        </div>;
      })() : <div style={{ fontFamily: font, fontWeight: 900, fontSize: size, lineHeight: 0.95, direction: "ltr", background: GOLD, WebkitBackgroundClip: "text", color: "transparent",
        filter: "drop-shadow(0 8px 24px rgba(0,0,0,0.4))" }}>{b.text}</div>}
      {b.label && <div style={{ fontFamily: font, fontWeight: 800, fontSize: size * 0.2, color: "#fff", marginTop: 6, textShadow: "0 3px 12px rgba(0,0,0,0.5)" }}>{b.label}</div>}
    </div>
  );
  const base: React.CSSProperties = { position: "absolute", left: x, top: y, width: w, height: h, opacity: Math.min(1, p * 1.5) * (1 - gone),
    transform: `translateY(${(1 - p) * 70}px) scale(${0.86 + 0.14 * p}) rotate(${-3 * (1 - p)}deg)` };
  if (brk <= 0) return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={base}>{face}{red > 0.4 && (
        <svg style={{ position: "absolute", inset: 0 }} viewBox="0 0 100 100" preserveAspectRatio="none">
          <path d="M38,0 L30,46 L0,58 M30,46 L72,40 L100,0 M72,40 L100,62 M30,46 L46,100 M72,40 L60,100" stroke="rgba(255,255,255,0.95)" strokeWidth={0.8} fill="none" />
        </svg>)}</div>
    </AbsoluteFill>);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ ...base, transform: "none" }}>
        {SHARDS.map((pts, k) => {
          const poly = pts.reduce((acc: string[], v, j) => (j % 2 ? acc : [...acc, `${v}% ${pts[j + 1]}%`]), []).join(", ");
          const dx = (-40 - (k % 3) * 60) * brk, dy = 1100 * brk * brk - 60 * brk + (k > 2 ? 80 * brk : 0);   // away from the face: out to the side and down
          return <div key={k} style={{ position: "absolute", inset: 0, clipPath: `polygon(${poly})`, transform: `translate(${dx}px, ${dy}px) rotate(${(k % 2 ? 1 : -1) * 170 * brk}deg)`,
            opacity: Math.max(0, 1 - brk * 0.85) }}>{face}</div>;
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── round 8 pieces ───────────────────────────────────────────────────────────────────────────────────────────
const fmt = (v: number) => Math.round(v).toLocaleString("en-US");
const Backdrop8: React.FC<{ b: AeBeat }> = ({ b }) => (
  <><AbsoluteFill style={{ backdropFilter: "blur(24px) brightness(0.34) saturate(0.7)", WebkitBackdropFilter: "blur(24px) brightness(0.34) saturate(0.7)" }} />
    <Bokeh seed={b.from} /></>);

/** a sum that pieces fly out of — products, shipping, taxes — each one knocking it down, until only what is left stays (comic) */
export const AeDrain: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const steps = b.steps ?? [];
  let val = b.start ?? 0, prev = val, hit = -1;
  steps.forEach((st, i) => { if (t >= st.at) { prev = i ? steps[i - 1].value : (b.start ?? 0); hit = i; } });
  if (hit >= 0) { const st = steps[hit]; val = prev + (st.value - prev) * ramp(t, st.at, 0.45, inOut); }
  const last = hit === steps.length - 1, endK = last ? ramp(t, steps[hit].at + 0.35, 0.4, inOut) : 0;
  const bump = hit >= 0 ? Math.sin(Math.min(1, (t - steps[hit].at) / 0.35) * Math.PI) : 0;   // the number is hit: a squash, no shake
  const Y = 560;
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <Backdrop8 b={b} />
      <div style={{ position: "absolute", left: 0, right: 0, top: Y - 210, textAlign: "center", fontFamily: font, fontWeight: 800, fontSize: 52, direction: "rtl",
        color: last ? "#ff8a7a" : "rgba(255,255,255,0.85)", opacity: 0.5 + 0.5 * endK || 0.85 }}>{last && endK > 0.5 ? "נשאר" : "מחזור"}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: Y - 130, display: "flex", justifyContent: "center",
        transform: `scale(${1 + 0.1 * bump}, ${1 - 0.12 * bump})`, transformOrigin: "50% 60%" }}>
        <div style={{ padding: "26px 54px", borderRadius: 40, background: "linear-gradient(135deg, rgba(255,255,255,0.22), rgba(255,255,255,0.06))",
          border: `2px solid ${last ? `rgba(255,120,100,${0.4 + 0.5 * endK})` : "rgba(246,196,83,0.6)"}`, boxShadow: "0 30px 70px rgba(0,0,0,0.5)", backdropFilter: "blur(14px)" }}>
          <span style={{ fontFamily: font, fontWeight: 900, fontSize: 170, lineHeight: 1, direction: "ltr", display: "inline-block",
            ...(last && endK > 0 ? { color: "#ff7a68", textShadow: "0 8px 30px rgba(255,80,60,0.45)" } : { background: GOLD, WebkitBackgroundClip: "text", color: "transparent" }) }}>{fmt(val)} {b.suffix ?? ""}</span>
        </div>
      </div>
      {steps.map((st, i) => {
        const u = t - st.at;
        if (u < 0 || u > 1.6) return null;
        const side = i % 2 ? 1 : -1, x = 540 + side * (60 + 260 * Math.min(1, u / 0.9)), y = Y + 120 + 520 * u * u - 240 * u;   // pops out and falls away
        const o = Math.min(1, u * 5) * (1 - ramp(u, 1.1, 0.5));
        return (
          <div key={i} style={{ position: "absolute", left: x - 230, top: y, width: 460, display: "flex", flexDirection: "column", alignItems: "center", opacity: o,
            transform: `rotate(${side * 18 * u}deg) scale(${0.6 + 0.4 * Math.min(1, u * 4)})` }}>
            <div style={{ fontSize: 150, lineHeight: 1 }}>{st.icon}</div>
            <div style={{ fontFamily: font, fontWeight: 900, fontSize: 54, color: "#fff", direction: "rtl", textShadow: "0 6px 20px rgba(0,0,0,0.6)" }}>{st.label}</div>
            <div style={{ fontFamily: font, fontWeight: 900, fontSize: 50, color: "#ff7a68", direction: "ltr" }}>-{fmt((i ? steps[i - 1].value : (b.start ?? 0)) - st.value)}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** a flood of messages — notification cards piling up faster and faster in the strip, a counter racing on top */
export const AeMsgs: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.3, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const D = b.to - b.from, u = Math.max(0, t - b.from);
  const N = b.count ?? 42;
  const at = (i: number) => D * 0.85 * Math.pow(i / N, 0.6);          // faster and faster
  const shown = Array.from({ length: N }, (_, i) => i).filter((i) => u >= at(i));
  const NAMES = ["#3a7bd5", "#e94e77", "#f6c453", "#2ecc71", "#9b59b6", "#e67e22", "#1abc9c", "#e74c3c"];
  const total = Math.round((b.followers ?? 500) * ramp(t, b.from + 0.2, D * 0.8, inOut));
  return (
    <AbsoluteFill style={{ opacity: k, pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 45%, rgba(0,0,0,0.65) 70%, rgba(0,0,0,0.8) 100%)" }} />
      {shown.slice(-7).map((i, j, arr) => {
        const age = u - at(i), pos = arr.length - 1 - j;                 // newest at the bottom, the stack climbs
        const y = 1700 - pos * 64 - (1 - ramp(age, 0, 0.25, inOut)) * -120, x = 90 + (rnd(i) - 0.5) * 50;
        const o = Math.min(1, age * 6) * (pos > 5 ? 0.5 : 1);   // the stack stays under the caption line
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: 900, height: 112, borderRadius: 30, opacity: o, direction: "rtl",
            transform: `scale(${1 - pos * 0.02}) rotate(${(rnd(i + 7) - 0.5) * 3}deg)`, transformOrigin: "50% 100%",
            background: "linear-gradient(135deg, rgba(255,255,255,0.24), rgba(255,255,255,0.10))", border: "1.5px solid rgba(255,255,255,0.35)",
            boxShadow: "0 14px 34px rgba(0,0,0,0.45)", backdropFilter: "blur(16px)", display: "flex", alignItems: "center", padding: "0 26px", gap: 22 }}>
            <div style={{ width: 70, height: 70, borderRadius: 35, background: NAMES[i % NAMES.length], flex: "none" }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: font, fontWeight: 800, fontSize: 30, color: "#fff" }}>הודעה חדשה</div>
              <div style={{ height: 14, width: `${50 + 40 * rnd(i + 3)}%`, borderRadius: 7, background: "rgba(255,255,255,0.45)", marginTop: 10 }} />
            </div>
            <div style={{ fontFamily: font, fontSize: 24, color: "rgba(255,255,255,0.7)" }}>עכשיו</div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center" }}>
        <div style={{ padding: "14px 40px", borderRadius: 999, background: "linear-gradient(180deg,#ff5b5b,#d81f2a)", boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
          fontFamily: font, fontWeight: 900, fontSize: 64, color: "#fff", direction: "rtl" }}>{fmt(total)} הודעות</div>
      </div>
    </AbsoluteFill>
  );
};

/** two things on a balance — the beam tips to the heavier one on `shatter` (spring, one overshoot) */
export const AeScale: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const tip = b.shatter ?? b.from + 1, x = Math.max(0, t - tip);
  const ang = t < tip ? 3 * Math.sin((t - b.from) * 3) * (1 - ramp(t, tip - 0.6, 0.6)) : 14 * (1 - Math.exp(-6 * x) * Math.cos(9 * x));
  const pans = b.pans ?? [];
  const CX = 540, CY = 470, L = 400, r = (ang * Math.PI) / 180;
  const end = (s: number) => ({ x: CX + s * L * Math.cos(r), y: CY + s * L * Math.sin(r) });    // s = 1 right pan, -1 left pan
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <Backdrop8 b={b} />
      <div style={{ position: "absolute", left: CX - 14, top: CY, width: 28, height: 520, background: GOLD, borderRadius: 14, boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }} />
      <div style={{ position: "absolute", left: CX - 160, top: CY + 500, width: 320, height: 40, background: GOLD, borderRadius: 20 }} />
      <div style={{ position: "absolute", left: CX - L - 20, top: CY - 10, width: 2 * L + 40, height: 20, background: GOLD, borderRadius: 10,
        transform: `rotate(${ang}deg)`, transformOrigin: "50% 50%", boxShadow: "0 8px 24px rgba(0,0,0,0.5)" }} />
      <div style={{ position: "absolute", left: CX - 34, top: CY - 34, width: 68, height: 68, borderRadius: 34, background: GOLD, boxShadow: "0 0 30px rgba(246,196,83,0.6)" }} />
      {pans.map((pn, i) => {
        const e = end(i === 0 ? 1 : -1);
        const heavy = i === 0 ? ramp(t, tip, 0.6, inOut) : 0;     // the right pan goes down: it is the heavier one
        return (
          <div key={i} style={{ position: "absolute", left: e.x - 170, top: e.y, width: 340, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <svg width={340} height={120} style={{ overflow: "visible" }}><path d="M170 0 L40 110 M170 0 L300 110" stroke="rgba(246,196,83,0.9)" strokeWidth={4} fill="none" /></svg>
            <div style={{ width: 340, height: 230, marginTop: -110, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
              <Img src={staticFile(pn.file)} style={{ maxWidth: 320, maxHeight: 220, objectFit: "contain", filter: "drop-shadow(0 14px 24px rgba(0,0,0,0.6))" }} />
            </div>
            <div style={{ width: 340, height: 26, borderRadius: "0 0 170px 170px", background: GOLD, marginTop: -6 }} />
            <div style={{ marginTop: 18, fontFamily: font, fontWeight: 900, fontSize: 46, direction: "rtl", textAlign: "center", lineHeight: 1.1, whiteSpace: "pre-line",
              color: heavy > 0.5 ? "#F6C453" : "#fff", textShadow: "0 6px 20px rgba(0,0,0,0.6)" }}>{pn.label}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** a map in the card strip; `pins` pins drop on it one after another from `shatter`, each with a little flag (icon) */
export const AeMap: React.FC<{ b: AeBeat; font: string; box?: CardBox }> = ({ b, box = CARD }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const c = ramp(t, b.from, 0.5, inOut), q = ramp(t, b.to - 0.4, 0.4, inOut);
  const H = box.bottom - box.top, W = 1080 - 2 * box.side, n = b.pins ?? 8, t0 = b.shatter ?? b.from + 0.3;
  const spots = Array.from({ length: n }, (_, i) => ({ x: 0.12 + 0.76 * rnd(i * 3 + 1), y: 0.22 + 0.62 * rnd(i * 5 + 2) }));
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: c * (1 - q), background: `linear-gradient(180deg, rgba(0,0,0,0) ${box.top - 160}px, rgba(0,0,0,0.55) ${box.top + 40}px, rgba(0,0,0,0.7) 100%)` }} />
      <div style={{ position: "absolute", left: box.side, top: box.top, width: W, height: H, borderRadius: box.r, overflow: "hidden",
        transform: `translateY(${(1 - c) * (1920 - box.top + 40) + q * (1920 - box.top + 40)}px) scale(${0.94 + 0.06 * c})`, transformOrigin: "50% 0%",
        boxShadow: "0 24px 70px rgba(0,0,0,0.7), 0 0 0 2px rgba(246,196,83,0.55)" }}>
        <Img src={staticFile(b.file!)} style={{ position: "absolute", inset: 0, width: W, height: H, objectFit: "cover", transform: `scale(${1.05 + 0.05 * ramp(t, b.from, b.to - b.from)})` }} />
        {spots.map((sp, i) => {
          const d = ramp(t, t0 + i * 0.16, 0.32, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
          if (d <= 0) return null;
          const px = sp.x * W, py = sp.y * H;
          return (
            <div key={i} style={{ position: "absolute", left: px - 40, top: py - 110 - (1 - d) * 160, width: 80, height: 120, opacity: Math.min(1, d * 2) }}>
              <div style={{ position: "absolute", left: 38, top: 0, width: 4, height: 100, background: "#fff", borderRadius: 2 }} />
              <div style={{ position: "absolute", left: 42, top: 2, padding: "2px 8px", borderRadius: "4px 14px 14px 4px", background: "#F6C453", fontSize: 40, lineHeight: 1.1,
                transform: `scaleX(${ramp(t, t0 + i * 0.16 + 0.25, 0.3, inOut)})`, transformOrigin: "0% 50%" }}>{b.label ?? "🍦"}</div>
              <div style={{ position: "absolute", left: 26, top: 92, width: 28, height: 28, borderRadius: 14, background: "radial-gradient(circle at 35% 35%, #ff8a8a, #d81f2a)",
                boxShadow: "0 6px 14px rgba(0,0,0,0.5)" }} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** a mock social profile on a phone, sliding up over the blurred picture; the follower count runs up to `followers` */
export const AeProfile: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.4, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const up = ramp(t, b.from, 0.55, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
  const fol = Math.round((b.followers ?? 15000) * ramp(t, b.from + 0.3, 0.9, inOut));
  const TILE = ["#f6c453", "#e94e77", "#3a7bd5", "#2ecc71", "#9b59b6", "#e67e22"];
  const stat = (v: string, l: string) => (
    <div style={{ textAlign: "center" }}><div style={{ fontWeight: 900, fontSize: 40, color: "#111" }}>{v}</div><div style={{ fontSize: 26, color: "#555" }}>{l}</div></div>);
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <Backdrop8 b={b} />
      <div style={{ position: "absolute", left: 200, top: 150 + (1 - up) * 900, width: 680, height: 960, borderRadius: 70, background: "#111", padding: 18,
        boxShadow: "0 40px 90px rgba(0,0,0,0.6), 0 0 0 3px rgba(246,196,83,0.6)" }}>
        <div style={{ width: "100%", height: "100%", borderRadius: 54, background: "#fff", overflow: "hidden", fontFamily: font, direction: "ltr" }}>
          <div style={{ height: 90, display: "flex", alignItems: "center", justifyContent: "center", gap: 10, fontWeight: 800, fontSize: 32, color: "#111", borderBottom: "1px solid #eee" }}>
            {b.handle}<span style={{ display: "inline-block", width: 30, height: 30, borderRadius: 15, background: "#3897f0", color: "#fff", fontSize: 22, lineHeight: "30px", textAlign: "center" }}>✓</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", padding: "26px 30px", gap: 26 }}>
            <div style={{ width: 190, height: 190, borderRadius: 95, padding: 6, background: "conic-gradient(#f9ce34, #ee2a7b, #6228d7, #f9ce34)", flex: "none" }}>
              <Img src={staticFile(b.img!)} style={{ width: 178, height: 178, borderRadius: 89, border: "5px solid #fff", objectFit: "cover" }} />
            </div>
            <div style={{ flex: 1, display: "flex", justifyContent: "space-around" }}>
              {stat("248", "פוסטים")}{stat(fol >= 1000 ? `${(fol / 1000).toFixed(fol >= 10000 ? 0 : 1)}K` : String(fol), "עוקבים")}{stat("31", "נעקבים")}
            </div>
          </div>
          <div style={{ padding: "0 34px", fontSize: 32, fontWeight: 800, color: "#111" }}>{b.name}</div>
          <div style={{ padding: "6px 34px 0", fontSize: 28, color: "#333", lineHeight: 1.3 }}>{b.bio}</div>
          <div style={{ margin: "22px 34px", height: 64, borderRadius: 16, background: "#3897f0", color: "#fff", fontWeight: 800, fontSize: 30,
            display: "flex", alignItems: "center", justifyContent: "center", direction: "rtl" }}>עקוב</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4, padding: "0 0" }}>
            {TILE.map((c, i) => <div key={i} style={{ height: 160, background: `linear-gradient(135deg, ${c}, rgba(0,0,0,0.25))` }} />)}
          </div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1130 - (1 - up) * 0, display: "flex", justifyContent: "center", opacity: ramp(t, b.from + 0.6, 0.4, inOut) }} />
    </AbsoluteFill>
  );
};

/** big glass rows over the blurred picture, one landing on each of its words — the last one lit gold (round 8, r8:
 * «משהו אחר עם אפקט זכוכית יוקרתית אבל אנימציה פשוטה») */
export const AeRows: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const rows = b.steps ?? [], H = 140, G = 30, Y0 = (b.y ?? 560) - (rows.length * (H + G) - G) / 2;   // y: the list's centre (IG keeps the top ~250 px)
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <Backdrop8 b={b} />
      {rows.map((r, i) => {
        const p = ramp(t, r.at - 0.1, 0.45, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
        const lit = i === rows.length - 1 ? ramp(t, r.at + 0.2, 0.4, inOut) : 0;
        return (
          <div key={i} style={{ position: "absolute", left: 90, right: 90, top: Y0 + i * (H + G), height: H, borderRadius: 36, opacity: Math.min(1, p * 1.5),
            transform: `translateX(${(1 - p) * 90}px)`, display: "flex", alignItems: "center", justifyContent: "center", direction: "rtl",
            background: lit ? `linear-gradient(135deg, rgba(246,196,83,${0.35 * lit + 0.18}), rgba(183,129,27,${0.2 * lit + 0.06}))` : "linear-gradient(135deg, rgba(255,255,255,0.22), rgba(255,255,255,0.06))",
            border: `2px solid rgba(${lit ? "246,196,83" : "255,255,255"},${0.45 + 0.4 * lit})`, backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
            boxShadow: `0 20px 50px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.5), 0 0 ${40 * lit}px rgba(246,196,83,${0.4 * lit})` }}>
            <span style={{ fontFamily: font, fontWeight: 900, fontSize: 72, color: "#fff", textShadow: "0 6px 24px rgba(0,0,0,0.5)" }}>{r.label}</span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** money that is all there and a sense of safety that is not — bars that fill as they are said, the last one stuck near empty
 * (r1 round 10: «משהו קומי / ויזואלי שמראה שיש לו מלא כסף אבל הוא עדיין לא מרגיש בטוח») */
export const AeMeter: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const bars = b.bars ?? [], H = 190, G = 80, Y0 = 560 - (bars.length * (H + G) - G) / 2;
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <Backdrop8 b={b} />
      {bars.map((r, i) => {
        const p = ramp(t, r.at - 0.15, 0.35, inOut), fill = ramp(t, r.at, r.bad ? 0.5 : 0.9, inOut) * r.fill;
        const throb = r.bad ? 0.5 + 0.5 * Math.sin((t - r.at) * Math.PI * 2 * 1.2) : 0;
        return (
          <div key={i} style={{ position: "absolute", left: 80, right: 80, top: Y0 + i * (H + G), height: H, opacity: p, direction: "rtl" }}>
            <div style={{ fontFamily: font, fontWeight: 900, fontSize: 66, color: r.bad ? "#ff8a7a" : "#fff", marginBottom: 12, textShadow: "0 6px 20px rgba(0,0,0,0.6)" }}>{r.label}</div>
            <div style={{ height: 92, borderRadius: 46, background: "rgba(255,255,255,0.12)", border: "2px solid rgba(255,255,255,0.35)", overflow: "hidden",
              boxShadow: "inset 0 2px 10px rgba(0,0,0,0.4)", backdropFilter: "blur(10px)" }}>
              <div style={{ height: "100%", width: `${Math.max(fill, 0.001) * 100}%`, borderRadius: 46,
                background: r.bad ? `linear-gradient(90deg, rgba(255,${60 + 40 * throb},50,1), #d81f2a)` : GOLD,
                boxShadow: r.bad ? `0 0 ${20 + 20 * throb}px rgba(255,60,50,0.8)` : "0 0 30px rgba(246,196,83,0.6)" }} />
            </div>
            <div style={{ position: "absolute", left: 0, top: 4, fontFamily: font, fontWeight: 900, fontSize: 54, color: r.bad ? "#ff8a7a" : "#F6C453", direction: "ltr" }}>{Math.round(fill * 100)}%</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** sound for each beat: one sound per graphic, on the frame it lands */
export const aeSfx = (beats: AeBeat[]) => beats.flatMap((b) => {
  const s: { at: number; file: string; vol: number }[] = [];
  if (b.k === "clip" && b.in === "whip") s.push({ at: b.from - 0.08, file: "whoosh1.wav", vol: 0.4 });
  if (b.k === "clip" && (b.in ?? "zoom") === "zoom") s.push({ at: b.from - 0.1, file: "swoosh-low.wav", vol: 0.42 });
  if (b.k === "clip" && b.in === "rise") s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.3 });
  if (b.k === "shrink") s.push({ at: b.from - 0.05, file: "whoosh1.wav", vol: 0.35 });
  if (b.k === "card") s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.2 });
  // the type's entrance under the dialogue, not over it (אורח B 29.10.2026: «הסאונד כניסה חזק מדיי»)
  if (b.k === "type" && !b.drama) s.push({ at: b.from - 0.05, file: "swoosh-low.wav", vol: 0.13 });
  if (b.k === "type" && b.drama) {
    s.push({ at: b.from - 0.3, file: "swoosh-low.wav", vol: 0.32 });
    const g = (b.words ?? []).find((w) => (b.gold ?? []).includes(w.text));
    if (g) s.push({ at: g.at - 0.04, file: "impact.wav", vol: 0.5 });
  }
  if (b.k === "type" && b.typing) (b.words ?? []).forEach((w) => s.push({ at: w.at - 0.06, file: "key.wav", vol: 0.55 }));
  if (b.k === "icon") s.push({ at: b.from + 0.04, file: "pop.wav", vol: 0.6 });
  if (b.k === "logo") { s.push({ at: b.from - 0.12, file: "whoosh1.wav", vol: 0.4 }); s.push({ at: b.from + 0.2, file: "text-appear.wav", vol: 0.35 }); }
  // the red ✕ builds: each «לא» lands harder than the one before, the last one with a low hit (תוכן הבונקר 4.11.26 round 4)
  if (b.k === "checks") { const xs = (b.items ?? []).filter((it) => it.mark === "x"); (b.items ?? []).forEach((it) => {
    s.push({ at: it.at - 0.1, file: "swoosh-quick.wav", vol: 0.2 });
    const m = (it.markAt ?? it.at + 0.3) + 0.05, k = xs.indexOf(it);
    if (it.mark !== "x") { s.push({ at: m, file: "click.wav", vol: 0.4 }); return; }
    s.push({ at: m, file: "stamp.wav", vol: 0.3 + 0.12 * k });
    if (k === xs.length - 1 && xs.length > 2) s.push({ at: m, file: "boom.wav", vol: 0.32 }); }); }
  if (b.k === "brands") (b.items ?? []).forEach((it) => s.push({ at: it.at - 0.08, file: "swoosh-quick.wav", vol: 0.28 }));
  if (b.k === "anger") s.push({ at: b.from - 0.02, file: "boom.wav", vol: 0.6 });
  if (b.k === "site") { s.push({ at: b.from - 0.08, file: "whoosh1.wav", vol: 0.38 }); (b.items ?? []).slice(1).forEach((it) => s.push({ at: it.at - 0.06, file: "swoosh-quick.wav", vol: 0.3 })); }
  if (b.k === "notes") (b.items ?? []).forEach((it) => s.push({ at: it.at - 0.02, file: "notify.wav", vol: it.mark === "v" ? 0.38 : 0.26 }));
  if (b.k === "glass" && b.shine) { s.push({ at: b.from - 0.05, file: "swoosh-low.wav", vol: 0.3 }); s.push({ at: b.from + 0.35, file: "sparkle.wav", vol: 0.4 }); }
  if (b.k === "dm") { s.push({ at: b.from + 0.02, file: "notify.wav", vol: 0.4 }); s.push({ at: b.from + 0.72, file: "swoosh-quick.wav", vol: 0.3 }); }
  // no Pop in the Bunker's reels (house rule) — the pill lands with the text sound, and the arrow's second call gets a swoosh
  if (b.k === "arrow") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.3 }); s.push({ at: b.from + 0.1, file: "text-appear.wav", vol: 0.35 });
    if (b.again !== undefined) s.push({ at: b.again - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); }
  if (b.k === "marks") [0, 1, 2].forEach((i) => s.push({ at: b.from + i * 0.22, file: "swoosh-quick.wav", vol: 0.22 }));
  if (b.k === "year") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); for (let i = 0; i < 12; i++) s.push({ at: b.from + 0.35 + i * (b.to - b.from - 0.9) / 12, file: "click.wav", vol: 0.2 }); }
  if (b.k === "gap") { s.push({ at: b.from - 0.05, file: "whoosh1.wav", vol: 0.35 }); (b.steps ?? []).forEach((st) => s.push({ at: st.at - 0.05, file: "swoosh-quick.wav", vol: 0.3 }));
    s.push({ at: (b.shatter ?? b.to) - 0.04, file: "boom.wav", vol: 0.45 }); }
  if (b.k === "border") { s.push({ at: b.from - 0.05, file: "whoosh1.wav", vol: 0.35 }); if (b.shatter !== undefined) s.push({ at: b.shatter - 0.1, file: "swoosh-quick.wav", vol: 0.3 }); }
  if (b.k === "world") { s.push({ at: b.from - 0.05, file: "whoosh1.wav", vol: 0.35 }); (b.stops ?? []).forEach((st) => s.push({ at: st.at - 0.05, file: "swoosh-quick.wav", vol: 0.3 })); }
  if (b.k === "num") s.push({ at: b.from - 0.02, file: "text-appear.wav", vol: 0.35 });
  if (b.k === "rain") s.push({ at: b.from, file: "cash.mp3", vol: 0.6 });
  if (b.k === "glow") { s.push({ at: b.from, file: "cash.mp3", vol: 0.5 }); s.push({ at: b.from + 0.05, file: "boom.wav", vol: 0.55 }); }   // the money that went
  if (b.k === "drain") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); (b.steps ?? []).forEach((st) => s.push({ at: st.at - 0.02, file: "woosh2.wav", vol: 0.35 })); }
  if (b.k === "msgs") { s.push({ at: b.from, file: "swoosh-quick.wav", vol: 0.25 }); for (let i = 0; i < 8; i++) s.push({ at: b.from + (b.to - b.from) * 0.85 * Math.pow(i / 8, 0.6), file: "click.wav", vol: 0.22 }); }
  if (b.k === "scale") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); s.push({ at: (b.shatter ?? b.from + 1) - 0.02, file: "impact.wav", vol: 0.5 }); }
  if (b.k === "map") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.2 }); for (let i = 0; i < (b.pins ?? 8); i++) s.push({ at: (b.shatter ?? b.from + 0.3) + i * 0.16, file: "click.wav", vol: 0.25 }); }
  if (b.k === "profile") s.push({ at: b.from - 0.05, file: "whoosh1.wav", vol: 0.35 });
  if (b.k === "meter") (b.bars ?? []).forEach((r) => s.push({ at: r.at - 0.05, file: r.bad ? "impact.wav" : "swoosh-quick.wav", vol: r.bad ? 0.4 : 0.28 }));
  if (b.k === "rows") (b.steps ?? []).forEach((st) => s.push({ at: st.at - 0.1, file: "swoosh-quick.wav", vol: 0.28 }));
  if (b.k === "cal") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); (b.days ?? []).forEach((d) => s.push({ at: d.at - 0.1, file: "click.wav", vol: 0.35 })); }
  if (b.k === "glass") { s.push({ at: b.from - 0.05, file: "swoosh-quick.wav", vol: 0.25 }); s.push({ at: (b.shatter ?? b.to) - 0.05, file: "boom.wav", vol: 0.7 });
    s.push({ at: (b.shatter ?? b.to) - 0.03, file: "impact.wav", vol: 0.55 }); }
  return s;
});
/** a warm light sweep on every zoom / whip / shrink entrance */
export const aeLeaks = (beats: AeBeat[]) => beats.filter((b) => (b.k === "clip" && ["zoom", "whip"].includes(b.in ?? "zoom")) || b.k === "shrink" || b.k === "leak")
  .map((b) => b.from - 0.15);

// ── round 2.11 pieces (ניב / דין) ──────────────────────────────────────────────────────────────────────────────
const pop = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
/** a logo that pops in beside the face as the word is said (ניב r5: «אייקון של טסלה ושל מרצדס כשהוא אומר עם סאונד של פופ») */
export const AeIcon: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.3) return null;
  const p = ramp(t, b.from, 0.4, pop), q = ramp(t, b.to - 0.05, 0.3, inOut), size = b.size ?? 260;
  const bob = Math.sin((t - b.from) * 2.4) * 6;
  return (
    <div style={{ position: "absolute", left: (b.x ?? 760) - size / 2, top: (b.y ?? 330) - size / 2 + bob, width: size, height: size, borderRadius: size * 0.24,
      background: "linear-gradient(135deg, rgba(255,255,255,0.32), rgba(255,255,255,0.10))", border: "2px solid rgba(255,255,255,0.6)",
      boxShadow: "0 24px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.7)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)",
      display: "flex", alignItems: "center", justifyContent: "center", opacity: Math.min(1, p * 2) * (1 - q), transform: `scale(${(0.3 + 0.7 * p) * (1 - 0.2 * q)}) rotate(${(1 - p) * -12}deg)` }}>
      <Img src={staticFile(b.file!)} style={{ width: size * 0.62, height: size * 0.62, objectFit: "contain", filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.35))" }} />
    </div>
  );
};

/** question marks rising round the asking face (דין r9: «אני שואל - תכניס סימני שאלה») */
export const AeMarks: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.3) return null;
  const q = ramp(t, b.to - 0.1, 0.35, inOut);
  const spots = [{ x: (b.x ?? 540) - 360, y: (b.y ?? 330) - 40, s: 1.3, r: -14 }, { x: (b.x ?? 540) + 360, y: (b.y ?? 330) - 90, s: 1.6, r: 12 }, { x: (b.x ?? 540) - 300, y: (b.y ?? 330) - 330, s: 1.0, r: -6 }];
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 1 - q }}>
      {spots.map((sp, i) => {
        const p = ramp(t, b.from + i * 0.22, 0.42, pop), u = t - b.from - i * 0.22;
        if (p <= 0) return null;
        return <div key={i} style={{ position: "absolute", left: sp.x - 90, top: sp.y - 110 - Math.max(0, u) * 14 + Math.sin(u * 3 + i) * 8, width: 180, textAlign: "center",
          fontFamily: font, fontWeight: 900, fontSize: 210 * sp.s, lineHeight: 1, background: GOLD, WebkitBackgroundClip: "text", color: "transparent",
          filter: "drop-shadow(0 10px 24px rgba(0,0,0,0.55))", opacity: Math.min(1, p * 2), transform: `scale(${0.3 + 0.7 * p}) rotate(${sp.r + Math.sin(u * 2 + i) * 4}deg)` }}>?</div>;
      })}
    </AbsoluteFill>
  );
};

/** a year passing: a ring that fills month by month over the blurred picture, the label under it (דין r8: «אנימציה שממחישה זמן ב״שנה של פיתוח״») */
export const AeYear: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.4, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const run = ramp(t, b.from + 0.35, b.to - b.from - 0.9, (x) => x), m = Math.min(12, Math.floor(run * 12) + (run > 0 ? 1 : 0));
  const R0 = 240, C = 2 * Math.PI * R0, CX = 540, CY = 560;   // above the caption line (1170)
  const months = ["ינו׳", "פבר׳", "מרץ", "אפר׳", "מאי", "יוני", "יולי", "אוג׳", "ספט׳", "אוק׳", "נוב׳", "דצמ׳"];
  const lab = ramp(t, b.from + 0.5, 0.4, inOut);
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <AbsoluteFill style={{ backdropFilter: "blur(26px) brightness(0.34) saturate(0.7)", WebkitBackdropFilter: "blur(26px) brightness(0.34) saturate(0.7)" }} />
      <Bokeh seed={b.from} />
      <svg style={{ position: "absolute", left: 0, top: 0 }} width={1080} height={1920}>
        <circle cx={CX} cy={CY} r={R0} fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth={34} />
        <circle cx={CX} cy={CY} r={R0} fill="none" stroke="#F6C453" strokeWidth={34} strokeLinecap="round" strokeDasharray={`${C * run} ${C}`}
          transform={`rotate(-90 ${CX} ${CY})`} style={{ filter: "drop-shadow(0 0 18px rgba(246,196,83,0.6))" }} />
        {months.map((mn, i) => {
          const a = (-90 + (i + 0.5) * 30) * Math.PI / 180, on = i < m;
          return <text key={i} x={CX + Math.cos(a) * (R0 + 78)} y={CY + Math.sin(a) * (R0 + 78) + 14} textAnchor="middle" fontFamily={font} fontWeight={800} fontSize={34}
            fill={on ? "#F6C453" : "rgba(255,255,255,0.35)"}>{mn}</text>;
        })}
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: CY - 150, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 230, lineHeight: 1,
        color: "#fff", direction: "ltr" }}>{m}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: CY + 80, textAlign: "center", fontFamily: font, fontWeight: 800, fontSize: 52, color: "rgba(255,255,255,0.8)" }}>חודשים</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: CY + R0 + 130, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 96, direction: "rtl",
        background: GOLD, WebkitBackgroundClip: "text", color: "transparent", opacity: lab, transform: `translateY(${(1 - lab) * 30}px)` }}>{b.text}</div>
      {b.label && <div style={{ position: "absolute", left: 0, right: 0, top: CY + R0 + 250, textAlign: "center", fontFamily: font, fontWeight: 700, fontSize: 48, color: "#fff",
        opacity: lab, direction: "rtl" }}>{b.label}</div>}
    </AbsoluteFill>
  );
};

/** a flight over the world map from place to place, a flag landing on each as it is named (דין r6: «אנימציית מפה של מעבר מהיר על המדינות… עם דגלים וסימון שלהן»)
 * the map file is equirectangular: lon -180…180 over its width, lat 84…-60 over its height (scripts: worldmap.py) */
export const AeWorld: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const stops = b.stops ?? [];
  const MW = 4320, MH = 1732, LAT0 = 84, LAT1 = -60;   // the map image, px
  const px = (lon: number, lat: number) => ({ x: (lon + 180) / 360 * MW, y: (LAT0 - lat) / (LAT0 - LAT1) * MH });
  // the camera: zoomed out over the whole map first, then from stop to stop
  const Z = b.zoom ?? 1.25, CX = 540, CY = 820;
  let cx = MW / 2, cy = MH * 0.45, z = 1080 / MW * 1.6;
  stops.forEach((s, i) => {
    const p = ramp(t, s.at - 0.55, 0.55, inOut);
    if (p > 0) { const q = px(s.lon, s.lat); cx = cx + (q.x - cx) * p; cy = cy + (q.y - cy) * p; z = z + (Z * 1080 / 1600 - z) * (i === 0 ? p : 0); }
  });
  return (
    <AbsoluteFill style={{ opacity: k, background: "#05070a", overflow: "hidden" }}>
      <div style={{ position: "absolute", left: CX - cx * z, top: CY - cy * z, width: MW * z, height: MH * z }}>
        <Img src={staticFile(b.file!)} style={{ position: "absolute", inset: 0, width: MW * z, height: MH * z }} />
        {stops.map((s, i) => {
          const d = ramp(t, s.at - 0.05, 0.4, pop);
          if (d <= 0) return null;
          const q = px(s.lon, s.lat), ring = ramp(t, s.at, 0.9);
          return (
            <div key={i} style={{ position: "absolute", left: q.x * z, top: q.y * z }}>
              <div style={{ position: "absolute", left: -90 * ring - 10, top: -90 * ring - 10, width: 180 * ring + 20, height: 180 * ring + 20, borderRadius: "50%",
                border: "4px solid #F6C453", opacity: 1 - ring }} />
              <div style={{ position: "absolute", left: -14, top: -14, width: 28, height: 28, borderRadius: 14, background: "#F6C453", boxShadow: "0 0 24px rgba(246,196,83,0.9)" }} />
              <div style={{ position: "absolute", left: -150, top: -250, width: 300, display: "flex", flexDirection: "column", alignItems: "center",
                opacity: Math.min(1, d * 2), transform: `translateY(${(1 - d) * 60}px) scale(${0.5 + 0.5 * d})` }}>
                <div style={{ fontSize: 120, lineHeight: 1 }}>{s.flag}</div>
                <div style={{ marginTop: 8, fontFamily: font, fontWeight: 900, fontSize: 52, color: "#1a1206", background: GOLD, padding: "6px 26px 10px", borderRadius: 999,
                  direction: "rtl", whiteSpace: "nowrap", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>{s.name}</div>
              </div>
            </div>
          );
        })}
      </div>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.7) 100%)" }} />
    </AbsoluteFill>
  );
};

/** two groups of people pulling apart (ניב r10 3.11: «אנימציה יותר מתקדמת ויוקרתית שממחישה ויזואלית פער בין שתי קבוצות אנשים»):
 * steps[0] = the group that uses it (gold, rises), steps[1] = the group that does not (grey, sinks); at `shatter` the gap opens wide */
const Person: React.FC<{ x: number; y: number; s: number; fill: string }> = ({ x, y, s, fill }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <circle cx={0} cy={-62} r={20} fill={fill} />
    <path d="M-28 -32 Q0 -46 28 -32 L34 22 Q0 30 -34 22 Z" fill={fill} />
  </g>
);
export const AeGap: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.4, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const st = b.steps ?? [], aAt = st[0]?.at ?? b.from + 0.3, bAt = st[1]?.at ?? b.from + 1.2, wide = b.shatter ?? b.to - 1;
  const pa = ramp(t, aAt - 0.1, 0.6, inOut), pb = ramp(t, bAt - 0.1, 0.6, inOut);
  const open = ramp(t, wide - 0.15, 0.9, (x) => 1 - Math.pow(1 - x, 3)), drift = ramp(t, aAt, Math.max(0.5, wide - aAt), (x) => x);
  const up = 120 * drift + 330 * open, down = 40 * drift + 170 * open;   // px the gold group rises, the grey one sinks
  const FLOOR = 900, XA = 760, XB = 320;
  const yA = FLOOR - up, yB = FLOOR + down;
  const gold = "#F6C453", grey = "rgba(210,215,222,0.55)";
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <AbsoluteFill style={{ backdropFilter: "blur(26px) brightness(0.32) saturate(0.6)", WebkitBackdropFilter: "blur(26px) brightness(0.32) saturate(0.6)" }} />
      <Bokeh seed={b.from} />
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="gp-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#FFF1C4" stopOpacity="0.55" /><stop offset="1" stopColor="#B7811B" stopOpacity="0.05" /></linearGradient>
          <linearGradient id="gp-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffffff" stopOpacity="0.18" /><stop offset="1" stopColor="#ffffff" stopOpacity="0.02" /></linearGradient>
        </defs>
        {/* the gold pillar the users stand on, the grey floor that drops away */}
        <g opacity={pa}><rect x={XA - 190} y={yA + 34} width={380} height={1300 - yA} rx={26} fill="url(#gp-p)" stroke="rgba(246,196,83,0.75)" strokeWidth={3} />
          {[0, 1, 2, 3, 4].map((i) => <Person key={i} x={XA - 128 + i * 64} y={yA + (i % 2 ? 6 : 0)} s={0.85} fill={gold} />)}</g>
        <g opacity={pb}><rect x={XB - 190} y={yB + 34} width={380} height={1300 - yB} rx={26} fill="url(#gp-g)" stroke="rgba(255,255,255,0.3)" strokeWidth={2} />
          {[0, 1, 2, 3, 4].map((i) => <Person key={i} x={XB - 128 + i * 64} y={yB + (i % 2 ? 6 : 0)} s={0.85} fill={grey} />)}</g>
        {/* the gap, measured: a bracket between the two floors that grows and glows */}
        {open > 0.02 && <g opacity={open}>
          <line x1={540} x2={540} y1={yA + 34} y2={yB + 34} stroke={gold} strokeWidth={6} strokeLinecap="round" style={{ filter: "drop-shadow(0 0 14px rgba(246,196,83,0.9))" }} />
          <path d={`M520 ${yA + 58} L540 ${yA + 34} L560 ${yA + 58} M520 ${yB + 10} L540 ${yB + 34} L560 ${yB + 10}`} stroke={gold} strokeWidth={6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>}
      </svg>
      <div style={{ position: "absolute", left: XA - 220, width: 440, top: yA - 210, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 52, direction: "rtl",
        background: GOLD, WebkitBackgroundClip: "text", color: "transparent", opacity: pa, transform: `translateY(${(1 - pa) * 30}px)` }}>{st[0]?.label}</div>
      <div style={{ position: "absolute", left: XB - 220, width: 440, top: yB - 210, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 52, direction: "rtl",
        color: "rgba(255,255,255,0.75)", opacity: pb, transform: `translateY(${(1 - pb) * 30}px)` }}>{st[1]?.label}</div>
      {open > 0.02 && <div style={{ position: "absolute", left: 540 - 130, width: 260, top: (yA + yB) / 2 + 4, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 64,
        color: "#1a1206", background: GOLD, borderRadius: 999, padding: "6px 0 10px", direction: "rtl", opacity: open, transform: `scale(${0.6 + 0.4 * open})`,
        boxShadow: "0 12px 40px rgba(0,0,0,0.5), 0 0 30px rgba(246,196,83,0.5)" }}>{b.text ?? "הפער"}</div>}
    </AbsoluteFill>
  );
};


/** the brand's own round logo when the brand is named (תוכן הבונקר 4.11.26: «תשלב את הלוגו של הבונקר כשמספרים עליו»):
 * it lands from a soft zoom with a gold ring that draws round it, a light sweep across, a slow float, and leaves with a fade */
export const AeLogo: React.FC<{ b: AeBeat }> = ({ b }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.4) return null;
  const size = b.size ?? 360, x = b.x ?? 540, y = b.y ?? 520;
  const p = ramp(t, b.from, 0.55, pop), ring = ramp(t, b.from + 0.15, 0.6, inOut), q = ramp(t, b.to - 0.05, 0.35, inOut);
  const sweep = ramp(t, b.from + 0.45, 0.7, inOut), bob = Math.sin((t - b.from) * 1.8) * 6;
  const R = size / 2 + 22, C = 2 * Math.PI * R;
  return (
    <div style={{ position: "absolute", left: x - size / 2 - 40, top: y - size / 2 - 40 + bob, width: size + 80, height: size + 80, opacity: Math.min(1, p * 2) * (1 - q),
      transform: `scale(${(0.55 + 0.45 * p) * (1 + 0.04 * q)})`, filter: `blur(${(1 - Math.min(1, p)) * 10 + q * 6}px)` }}>
      <div style={{ position: "absolute", inset: 40, borderRadius: "50%", boxShadow: `0 0 ${60 + 40 * ring}px rgba(246,196,83,${0.35 * ring}), 0 30px 70px rgba(0,0,0,0.55)` }} />
      <div style={{ position: "absolute", inset: 40, borderRadius: "50%", overflow: "hidden", background: "rgba(10,10,10,0.55)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
        <Img src={staticFile(b.file ?? "logo_round.png")} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        <div style={{ position: "absolute", top: 0, bottom: 0, width: "45%", left: `${-50 + 160 * sweep}%`, transform: "skewX(-18deg)", opacity: sweep < 1 ? 0.55 : 0,
          background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.75), transparent)" }} />
      </div>
      <svg width={size + 80} height={size + 80} style={{ position: "absolute", left: 0, top: 0, transform: "rotate(-90deg)" }}>
        <circle cx={(size + 80) / 2} cy={(size + 80) / 2} r={R} fill="none" stroke="#F6C453" strokeWidth={7} strokeLinecap="round"
          strokeDasharray={C} strokeDashoffset={C * (1 - ring)} style={{ filter: "drop-shadow(0 0 10px rgba(246,196,83,0.8))" }} />
      </svg>
    </div>
  );
};

/** the call to action: a gold pill with the line and a gold arrow bouncing down to where the link sits under the reel
 * (תוכן הבונקר 4.11.26: «תוסיף חץ הנעה לפעולה») — it stays to the end and fades with the picture */
export const AeArrow: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02) return null;
  // round 7: with "show" it calls and leaves (its 12 s on screen competed with the captions), and comes back only at "again"
  let vis = 1, from = b.from;
  if (b.show !== undefined) {
    const win = (a: number) => ramp(t, a - 0.02, 0.01) * (1 - ramp(t, a + b.show! - 0.4, 0.4, inOut));
    const again = b.again !== undefined && t >= b.again - 0.02;
    if (again) from = b.again!;
    vis = again ? win(b.again!) : win(b.from);
    if (vis <= 0) return null;
  }
  const p = ramp(t, from, 0.5, pop), y = b.y ?? 1430, u = t - from;
  // it bounces for 2.6 s, then rests on a slow breath, and calls once more at "again" (round 4: 13 s of bouncing got tiring)
  const live = (a: number, d: number) => (t < a ? 0 : Math.min(1, (t - a) / 0.4) * (1 - ramp(t, a + d - 0.6, 0.6, inOut)));
  const act = Math.max(live(b.from, 2.6), b.again !== undefined ? live(b.again, 2.2) : 0);
  const bounce = Math.abs(Math.sin(u * 3.2)) * 26 * act;
  const breath = 1 + 0.018 * Math.sin(u * 2.2) * (1 - act) + (b.again !== undefined ? 0.07 * Math.sin(Math.PI * ramp(t, b.again, 0.45, inOut)) : 0);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: Math.min(1, p * 2) * vis }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: y, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${(0.6 + 0.4 * p) * breath * (0.85 + 0.15 * vis)})` }}>
        <div style={{ direction: "rtl", fontFamily: font, fontWeight: 900, fontSize: b.size ?? 66, color: "#141414", padding: "18px 46px", borderRadius: 999,
          background: "linear-gradient(180deg, #FFE7A3 0%, #F6C453 55%, #D9A23A 100%)", boxShadow: "0 18px 44px rgba(0,0,0,0.5), 0 0 40px rgba(246,196,83,0.45), inset 0 2px 0 rgba(255,255,255,0.7)" }}>
          {b.text ?? "לחצו על הקישור"}
        </div>
        <svg width={150} height={190} viewBox="0 0 150 190" style={{ marginTop: 18 + bounce, filter: "drop-shadow(0 10px 18px rgba(0,0,0,0.55)) drop-shadow(0 0 14px rgba(246,196,83,0.6))" }}>
          <defs><linearGradient id="arrg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#FFF1C4" /><stop offset="0.5" stopColor="#F6C453" /><stop offset="1" stopColor="#B7811B" /></linearGradient></defs>
          <path d="M55 0 H95 V105 H140 L75 185 L10 105 H55 Z" fill="url(#arrg)" stroke="rgba(255,255,255,0.7)" strokeWidth={3} strokeLinejoin="round" />
        </svg>
      </div>
    </AbsoluteFill>
  );
};


/** a checklist low in the frame over the live picture — nothing covers the speaker (תוכן הבונקר 4.11.26: «במקום שיהיה בזכוכית
 * שתסתיר אותי, שיהיה בלמטה, בצ'קבוקסים כאלה שמתמלאים בצורה אלגנטית ומודרנית»). Each line slides in when it is said and its box
 * fills — gold with a drawn tick ("v"), or red with a drawn ✕ ("x", the comic «לא») — a beat later. */
export const AeChecks: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.3 || t > b.to + 0.45) return null;
  const items = b.items ?? [], H = b.size ?? 96, G = 18, bottom = b.y ?? 1660;
  const rows = b.center && b.max ? Math.min(items.length, b.max) : items.length;
  const top = bottom - rows * (H + G) + G - (b.title ? 70 : 0);
  const k = ramp(t, b.from - 0.3, 0.4, inOut) * (1 - ramp(t, b.to, 0.4, inOut));
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: k }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: top - 260, bottom: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.55) 45%, rgba(0,0,0,0.72) 100%)" }} />
      {b.title && !b.center && <div style={{ position: "absolute", right: 110, top, direction: "rtl", fontFamily: font, fontWeight: 800, fontSize: 44, letterSpacing: "0.02em",
        color: "#F6C453", opacity: ramp(t, b.from - 0.2, 0.4, inOut), textShadow: "0 4px 18px rgba(0,0,0,0.6)" }}>{b.title}</div>}
      {b.center ? <CheckBlock b={b} t={t} font={font} top={top} H={H} G={G} /> : items.map((it, i) => {
        const y = top + (b.title ? 70 : 0) + i * (H + G);
        const p = ramp(t, it.at - 0.12, 0.45, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
        const m = ramp(t, it.markAt ?? it.at + 0.3, 0.35, inOut), x = it.mark === "x";
        const col = x ? "#E5484D" : "#F6C453", B = H * 0.62;
        return (
          <div key={i} style={{ position: "absolute", right: 90, left: 90, top: y, height: H, direction: "rtl", display: "flex", alignItems: "center", gap: 30,
            opacity: Math.min(1, p * 1.4), transform: `translateX(${(1 - p) * -60}px)` }}>
            <div style={{ width: B, height: B, flex: "none", borderRadius: B * 0.26, position: "relative",
              border: `3px solid ${m > 0.05 ? col : "rgba(255,255,255,0.75)"}`, background: m > 0 ? `rgba(${x ? "229,72,77" : "246,196,83"},${0.95 * m})` : "rgba(255,255,255,0.08)",
              boxShadow: m > 0 ? `0 0 ${28 * m}px rgba(${x ? "229,72,77" : "246,196,83"},${0.55 * m})` : "none", transform: `scale(${1 + 0.18 * Math.sin(Math.PI * m)})` }}>
              <svg viewBox="0 0 40 40" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
                {x ? <><path d="M12 12 L28 28" stroke="#fff" strokeWidth={5} strokeLinecap="round" fill="none" strokeDasharray={23} strokeDashoffset={23 * (1 - Math.min(1, m * 2))} />
                       <path d="M28 12 L12 28" stroke="#fff" strokeWidth={5} strokeLinecap="round" fill="none" strokeDasharray={23} strokeDashoffset={23 * (1 - Math.max(0, m * 2 - 1))} /></>
                   : <path d="M10 21 L17 28 L30 13" stroke="#1a1408" strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" fill="none" strokeDasharray={32} strokeDashoffset={32 * (1 - m)} />}
              </svg>
            </div>
            <span style={{ fontFamily: font, fontWeight: 800, fontSize: H * 0.56, color: "#fff", textShadow: "0 4px 18px rgba(0,0,0,0.65)", whiteSpace: "nowrap",
              opacity: x && m > 0.5 ? 0.75 : 1 }}>{it.label}</span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** the checklist as one centred block: the rows keep their right edge (RTL) inside it, and the block sits in the middle of
 * the readable band — Instagram's like/comment/share column covers x > 950 (round 5) */
const CheckBlock: React.FC<{ b: AeBeat; t: number; font: string; top: number; H: number; G: number }> = ({ b, t, font, top, H, G }) => (
  <div style={{ position: "absolute", left: 60, width: 880, top: top - 34, display: "flex", justifyContent: "center" }}>
    {/* round 7: one glass card behind the rows — over the mic and the shirt the thin lines did not read on a phone */}
    <div style={{ direction: "rtl", display: "flex", flexDirection: "column", gap: G, padding: "34px 52px", borderRadius: 44,
      background: "linear-gradient(160deg, rgba(28,28,30,0.72), rgba(10,10,12,0.62))", border: "2px solid rgba(255,255,255,0.16)",
      backdropFilter: "blur(18px) saturate(1.2)", WebkitBackdropFilter: "blur(18px) saturate(1.2)",
      boxShadow: "0 28px 70px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.22)",
      transform: `translateY(${(1 - ramp(t, b.from - 0.3, 0.5, inOut)) * 40}px) scale(${0.94 + 0.06 * ramp(t, b.from - 0.3, 0.5, inOut)})` }}>
      {b.title && <div style={{ fontFamily: font, fontWeight: 800, fontSize: H * 0.5, color: "#F6C453", opacity: ramp(t, b.from - 0.2, 0.4, inOut),
        textShadow: "0 4px 18px rgba(0,0,0,0.6)", marginBottom: 4 }}>{b.title}</div>}
      {(b.items ?? []).map((it, i, all) => {
        const p = ramp(t, it.at - 0.12, 0.45, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
        const m = ramp(t, it.markAt ?? it.at + 0.3, 0.35, inOut), x = it.mark === "x";
        const col = x ? "#E5484D" : "#F6C453", B = H * 0.62;
        // rolling: line i leaves (up, fading, its height folding) as line i + max comes in — the block never grows past max lines
        const nx = b.max ? all[i + b.max] : undefined, gone = nx ? ramp(t, nx.at - 0.3, 0.4, inOut) : 0;
        // a line takes no room until it comes in (round 7: the card was six lines tall with two empty)
        // and the card grows line by line — no empty glass waiting for lines that are not said yet
        const come = ramp(t, it.at - 0.3, 0.4, inOut), room = come * (1 - gone);
        return (
          <div key={i} style={{ height: H * room, marginBottom: room < 1 ? -G * (1 - room) : 0, display: "flex", alignItems: "center", gap: 28,
            opacity: Math.min(1, p * 1.4) * (1 - gone), transform: `translateX(${(1 - p) * -60}px) translateY(${-24 * gone}px)` }}>
            <div style={{ width: B, height: B, flex: "none", borderRadius: B * 0.26, position: "relative",
              border: `3px solid ${m > 0.05 ? col : "rgba(255,255,255,0.75)"}`, background: m > 0 ? `rgba(${x ? "229,72,77" : "246,196,83"},${0.95 * m})` : "rgba(255,255,255,0.08)",
              boxShadow: m > 0 ? `0 0 ${28 * m}px rgba(${x ? "229,72,77" : "246,196,83"},${0.55 * m})` : "none", transform: `scale(${1 + 0.18 * Math.sin(Math.PI * m)})` }}>
              <svg viewBox="0 0 40 40" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
                {x ? <><path d="M12 12 L28 28" stroke="#fff" strokeWidth={5} strokeLinecap="round" fill="none" strokeDasharray={23} strokeDashoffset={23 * (1 - Math.min(1, m * 2))} />
                       <path d="M28 12 L12 28" stroke="#fff" strokeWidth={5} strokeLinecap="round" fill="none" strokeDasharray={23} strokeDashoffset={23 * (1 - Math.max(0, m * 2 - 1))} /></>
                   : <path d="M10 21 L17 28 L30 13" stroke="#1a1408" strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" fill="none" strokeDasharray={32} strokeDashoffset={32 * (1 - m)} />}
              </svg>
            </div>
            <span style={{ fontFamily: font, fontWeight: 800, fontSize: H * 0.56, color: "#fff", textShadow: "0 4px 18px rgba(0,0,0,0.65)", whiteSpace: "nowrap",
              opacity: x && m > 0.5 ? 0.75 : 1 }}>{it.label}</span>
          </div>
        );
      })}
    </div>
  </div>
);

/** anime anger over the listener's head (round 5, reel 2 0:49: «סאונד בום ואת הכיתוב ״מה אתה משוגע?״ — קווים שיוצאים מהראש של
 * דולב, שיראה כמו דמות כועסת באנימה»): the cross-popping vein at the temple, two fans of strokes off the head that flicker,
 * and the line popping in over him. x/y = the top of his head in the frame; text sits above it */
export const AeAnger: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.05 || t > b.to + 0.35) return null;
  const hx = b.x ?? 600, hy = b.y ?? 420, S = b.size ?? 1;
  const k = ramp(t, b.from - 0.05, 0.12) * (1 - ramp(t, b.to, 0.3, inOut));
  const pop = ramp(t, b.from, 0.32, (x) => 1 + 2.6 * Math.pow(x - 1, 3) + 1.6 * Math.pow(x - 1, 2));
  const beat = 1 + 0.12 * Math.abs(Math.sin((t - b.from) * Math.PI * 5));        // the vein throbs ≈ 5 per second
  const flick = (i: number) => 0.55 + 0.45 * Math.abs(Math.sin((t - b.from) * 9 + i * 1.7));
  const fan = (cx: number, cy: number, a0: number, side: number) => [0, 1, 2].map((i) => {
    const a = (a0 + side * (i - 1) * 22) * Math.PI / 180, r0 = 70 * S, r1 = (125 + (i === 1 ? 30 : 0)) * S * (0.85 + 0.15 * flick(i));
    const d = `M${cx + Math.cos(a) * r0} ${cy + Math.sin(a) * r0} L${cx + Math.cos(a) * r1} ${cy + Math.sin(a) * r1}`;
    return <g key={`${side}${i}`} opacity={flick(i + side)}><path d={d} stroke="#111" strokeWidth={22 * S} strokeLinecap="round" /><path d={d} stroke="#fff" strokeWidth={12 * S} strokeLinecap="round" /></g>;
  });
  const vx = hx + 150 * S, vy = hy + 40 * S;   // the temple, just off his head
  const vein = [0, 90, 180, 270].map((r) => <path key={r} transform={`rotate(${r} 0 0)`} d="M 14 -48 Q 18 -18 48 -14" fill="none" stroke="#E5484D" strokeWidth={14} strokeLinecap="round" />);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: k }}>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <g transform={`translate(${hx} ${hy}) scale(${pop})`}>{fan(-120 * S, 10 * S, -150, 1)}{fan(120 * S, -10 * S, -30, -1)}</g>
        <g transform={`translate(${vx} ${vy}) scale(${S * pop * beat}) rotate(12)`}>
          <g stroke="#3a0d0f" strokeWidth={26} fill="none">{[0, 90, 180, 270].map((r) => <path key={r} transform={`rotate(${r} 0 0)`} d="M 14 -48 Q 18 -18 48 -14" strokeLinecap="round" />)}</g>
          {vein}
        </g>
      </svg>
      {b.text && <div style={{ position: "absolute", left: 60, right: 60, top: (b.ty ?? hy - 300), textAlign: "center", direction: "rtl",
        transform: `scale(${pop}) rotate(-4deg)`, fontFamily: font, fontWeight: 900, fontSize: 104 * S, color: "#fff", lineHeight: 1.1,
        WebkitTextStroke: `${10 * S}px #111`, paintOrder: "stroke fill", textShadow: "0 10px 30px rgba(0,0,0,0.55)" }}>{b.text}</div>}
    </AbsoluteFill>
  );
};

/** the automations, drawn (round 5, reel 1: «אלמנטים ציוריים מודרניים כשאני מדבר על האוטומציות — סימן של תגובה ושליחה של פרק
 * יוטיוב בהודעה»): a comment lands, a paper plane carries it over, and a DM opens with the episode's YouTube card in it, «נשלח».
 * Flat, rounded, the house gold — and nothing past x 930 (Instagram's buttons) */
export const AeDm: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.3 || t > b.to + 0.45) return null;
  const y = b.y ?? 1300, u = t - b.from;
  const k = ramp(t, b.from - 0.3, 0.3, inOut) * (1 - ramp(t, b.to, 0.4, inOut));
  const spring = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
  const c = ramp(u, 0, 0.45, spring), fly = ramp(u, 0.75, 0.6, inOut), d = ramp(u, 1.15, 0.5, spring), sent = ramp(u, 1.75, 0.3, inOut);
  // the plane on an arc from the comment (right) to the message (left)
  // round 7: everything ≈1.3× — at the old size the comment and the card did not read on a phone
  // the comment sits on the chest above the caption band, the message below it — the caption between them stays readable
  const px = 700 - 360 * fly, py = y - 280 + 340 * fly - Math.sin(Math.PI * fly) * 60;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: k }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: y - 160, bottom: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.5) 40%, rgba(0,0,0,0.7) 100%)" }} />
      {/* the comment */}
      <div style={{ position: "absolute", left: 590, width: 340, top: y - 360, direction: "rtl", opacity: Math.min(1, c * 1.5), transform: `translateY(${(1 - c) * 50}px) scale(${0.8 + 0.2 * c})`,
        transformOrigin: "right center", display: "flex", alignItems: "center", gap: 16, padding: "20px 22px", borderRadius: 36, background: "#fff",
        boxShadow: "0 18px 50px rgba(0,0,0,0.45)" }}>
        <svg viewBox="0 0 48 48" width={72} height={72} style={{ flex: "none" }}>
          <path d="M24 5C13 5 5 12.6 5 22c0 5 2.3 9.5 6 12.6V43l8.3-4.6c1.5.4 3.1.6 4.7.6 11 0 19-7.6 19-17S35 5 24 5z" fill="#F6C453" />
          <path d="M24 30.5s-8-4.6-8-9.6c0-2.6 2-4.4 4.2-4.4 1.6 0 3 .9 3.8 2.2.8-1.3 2.2-2.2 3.8-2.2 2.3 0 4.2 1.8 4.2 4.4 0 5-8 9.6-8 9.6z" fill="#fff" />
        </svg>
        <div style={{ fontFamily: font, lineHeight: 1.15 }}>
          <div style={{ fontSize: 36, fontWeight: 700, color: "#7a7a7a" }}>תגובה חדשה</div>
          <div style={{ fontSize: 58, fontWeight: 900, color: "#141414" }}>״פרק״</div>
        </div>
      </div>
      {/* the plane */}
      {fly > 0 && fly < 1 && <svg viewBox="0 0 48 48" width={104} height={104} style={{ position: "absolute", left: px - 52, top: py - 52, transform: `rotate(${-160 + 50 * fly}deg)` }}>
        <path d="M44 4 4 21l15 6 4 15 7-10 10 8z" fill="#fff" stroke="#111" strokeWidth={2.5} strokeLinejoin="round" /><path d="M19 27 44 4 23 42" fill="none" stroke="#111" strokeWidth={2.5} strokeLinejoin="round" />
      </svg>}
      {/* the message with the episode */}
      <div style={{ position: "absolute", left: 70, width: 540, top: y + 20, direction: "rtl", opacity: Math.min(1, d * 1.5), transform: `translateY(${(1 - d) * 60}px) scale(${0.8 + 0.2 * d})`,
        transformOrigin: "left center", padding: 18, borderRadius: 42, borderBottomLeftRadius: 12, background: "linear-gradient(140deg, #F9D57A, #E3A93A)", boxShadow: "0 18px 50px rgba(0,0,0,0.45)" }}>
        <div style={{ position: "relative", height: 250, borderRadius: 28, overflow: "hidden", background: "linear-gradient(160deg, #2a2a2a, #0d0d0d)" }}>
          <Img src={staticFile("logo_round.png")} style={{ position: "absolute", right: 20, top: 20, width: 80, height: 80, opacity: 0.92 }} />
          <svg viewBox="0 0 68 48" width={140} height={99} style={{ position: "absolute", left: "50%", top: "50%", transform: `translate(-50%, -50%) scale(${1 + 0.08 * Math.sin(Math.PI * ramp(u, 1.5, 0.4, inOut))})` }}>
            <path d="M66.5 7.7c-.8-2.9-2.5-5.4-5.4-6.2C55.8.1 34 0 34 0S12.2.1 6.9 1.6C4 2.4 2.3 4.8 1.5 7.7 0 13 0 24 0 24s0 11 1.5 16.3c.8 2.9 2.5 5.4 5.4 6.2C12.2 47.9 34 48 34 48s21.8-.1 27.1-1.6c2.9-.8 4.6-3.2 5.4-6.2C68 35 68 24 68 24s0-11-1.5-16.3z" fill="#FF0033" />
            <path d="M45 24 27 14v20z" fill="#fff" />
          </svg>
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 8, background: "rgba(255,255,255,0.18)" }}><div style={{ width: `${40 * d}%`, height: "100%", background: "#FF0033" }} /></div>
        </div>
        <div style={{ fontFamily: font, fontWeight: 900, fontSize: 50, color: "#1a1408", padding: "12px 8px 2px" }}>הפרק המלא ביוטיוב</div>
      </div>
      <div style={{ position: "absolute", left: 640, top: y + 270, direction: "rtl", display: "flex", alignItems: "center", gap: 12, fontFamily: font, fontWeight: 800,
        fontSize: 44, color: "#fff", opacity: sent, textShadow: "0 3px 12px rgba(0,0,0,0.7)" }}>
        <span>נשלח אוטומטית</span>
        <svg viewBox="0 0 34 20" width={58} height={34}><path d="M2 11l5 5L18 4M14 14l2 2L28 4" fill="none" stroke="#F6C453" strokeWidth={3.4} strokeLinecap="round" strokeLinejoin="round" /></svg>
      </div>
    </AbsoluteFill>
  );
};

/** the engines around the speaker (round 6, reel 1: «כשאני מספר את השמות של מנועי ה-AI שיקיפו אותי בצורה אלגנטית בריחוף חלק»):
 * each glass tile glides out from behind his head to its own place beside him as it is named, then floats — slow, out of
 * phase, a few px — and they all drift back in and fade when the line ends. Nothing crosses the face. */
const BrandOrbit: React.FC<{ b: AeBeat; font: string; t: number }> = ({ b, font, t }) => {
  const S = b.size ?? 170, O = b.orbit!;
  const k = 1 - ramp(t, b.to, 0.5, inOut);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {(b.items ?? []).map((it, i) => {
        const p = ramp(t, it.at - 0.12, 0.75, inOut), back = ramp(t, b.to, 0.5, inOut);
        const fx = (it.x ?? 540) + 9 * Math.sin(t * 0.9 + i * 1.7), fy = (it.y ?? 600) + 13 * Math.sin(t * 0.7 + i * 2.3);
        const x = O.x + (fx - O.x) * p * (1 - 0.35 * back), y = O.y + (fy - O.y) * p * (1 - 0.35 * back);
        const a = Math.min(1, p * 1.8) * k, sc = 0.55 + 0.45 * p;
        return (
          <div key={i} style={{ position: "absolute", left: x - S / 2, top: y - S / 2, width: S, opacity: a, transform: `scale(${sc}) rotate(${2.5 * Math.sin(t * 0.8 + i)}deg)` }}>
            <div style={{ width: S, height: S, borderRadius: S * 0.26, display: "flex", alignItems: "center", justifyContent: "center",
              background: "linear-gradient(145deg, rgba(255,255,255,0.28), rgba(255,255,255,0.08))", border: "2px solid rgba(255,255,255,0.6)",
              backdropFilter: "blur(16px) saturate(1.3)", WebkitBackdropFilter: "blur(16px) saturate(1.3)",
              boxShadow: `0 22px 50px rgba(0,0,0,0.45), 0 0 ${34 + 10 * Math.sin(t * 1.3 + i)}px rgba(246,196,83,0.38), inset 0 1px 0 rgba(255,255,255,0.75)` }}>
              {it.icon ? <Img src={staticFile(it.icon)} style={{ width: S * 0.56, height: S * 0.5, objectFit: "contain", filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.4))" }} />
                : <span style={{ fontFamily: font, fontWeight: 900, fontSize: S * 0.28, color: "#F6C453", direction: "rtl" }}>{it.label}</span>}
            </div>
            {it.icon && <div style={{ marginTop: 10, textAlign: "center", fontFamily: font, fontWeight: 800, fontSize: Math.round(S * 0.21), color: "#fff",
              textShadow: "0 4px 14px rgba(0,0,0,0.75)", whiteSpace: "nowrap" }}>{it.label}</div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** the AI engines as glass tiles with their own icons, low in the frame («שיכתבו את זה בזכוכית, עושים את האייקונים שלהם») */
export const AeBrands: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.3 || t > b.to + 0.45) return null;
  if (b.orbit) return <BrandOrbit b={b} font={font} t={t} />;
  const items = b.items ?? [], S = b.size ?? 210, G = 26, y = b.y ?? 1330;
  // the row is centred on what is already in — the first tile lands in the middle and slides over as the next ones come
  const grow = (i: number) => ramp(t, items[i].at - 0.1, 0.5, inOut);
  const W = items.reduce((a, _, i) => a + grow(i) * (S + G), 0) - G;
  const k = ramp(t, b.from - 0.3, 0.4, inOut) * (1 - ramp(t, b.to, 0.4, inOut));
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: k }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: y - 300, bottom: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.5) 45%, rgba(0,0,0,0.7) 100%)" }} />
      {items.map((it, i) => {
        const p = ramp(t, it.at - 0.1, 0.5, (x) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2)), bob = Math.sin((t - it.at) * 2 + i) * 5;
        const left = 540 + W / 2 - S - i * (S + G);   // RTL: the first one said sits on the right
        return (
          <div key={i} style={{ position: "absolute", left, top: y - S / 2 + bob, width: S, height: S + 70, opacity: Math.min(1, p * 1.6),
            transform: `translateY(${(1 - p) * 70}px) scale(${0.7 + 0.3 * p})` }}>
            <div style={{ width: S, height: S, borderRadius: S * 0.26, display: "flex", alignItems: "center", justifyContent: "center",
              background: "linear-gradient(145deg, rgba(255,255,255,0.26), rgba(255,255,255,0.07))", border: "2px solid rgba(255,255,255,0.55)",
              backdropFilter: "blur(18px) saturate(1.3)", WebkitBackdropFilter: "blur(18px) saturate(1.3)",
              boxShadow: "0 24px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.75)" }}>
              {it.icon ? <Img src={staticFile(it.icon)} style={{ width: S * 0.5, height: S * 0.5, objectFit: "contain", filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.4))" }} />
                : <span style={{ fontFamily: font, fontWeight: 900, fontSize: S * 0.3, color: "#F6C453" }}>AI</span>}
            </div>
            <div style={{ marginTop: 14, textAlign: "center", direction: "rtl", unicodeBidi: "plaintext", fontFamily: font, fontWeight: 800, fontSize: Math.round(S * 0.22), color: "#fff", textShadow: "0 4px 16px rgba(0,0,0,0.7)", whiteSpace: "nowrap" }}>{it.label}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ── round 8 (10.11.2026) ─────────────────────────────────────────────────────────────────────────────────────────
/** site: the Bunker's own episode pages in a glass phone, scrolled down to the full transcript (reel 1, «תראה את האתר כשאני
 * מדבר עליו — דוגמאות של פרקים מהאתר עם התמלולים»). A cutaway on a dark gold-lit stage: the phone above the caption band,
 * a gold pill under the captions. items = the pages (real captures of bunker.alon-gabay.co.il), each from its word; the
 * next page slides in over the last one; y0 → y1 = where the screen's top runs on the page, in image px */
export const AeSite: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.32) return null;
  const k = ramp(t, b.from, 0.3, inOut), q = ramp(t, b.to, 0.3, inOut);
  const P = { x: 130, y: 92, w: 820, h: 968, r: 70, bz: 14 };   // the phone: right edge 950 (Instagram's buttons start there)
  const SW = P.w - 2 * P.bz, SH = P.h - 2 * P.bz;
  const ph = ramp(t, b.from + 0.02, 0.6, (x) => 1 + 2.0 * Math.pow(x - 1, 3) + 1.0 * Math.pow(x - 1, 2));
  const items = b.items ?? [];
  const glow = 0.5 + 0.5 * noise2D("site" + b.from, t * 0.4, 0);
  const lab = ramp(t, b.from + 0.35, 0.4, inOut) * (1 - q);
  return (
    <AbsoluteFill style={{ opacity: k * (1 - q) }}>
      <AbsoluteFill style={{ background: "#07080A" }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, rgba(246,196,83,${0.15 + 0.07 * glow}) 0%, rgba(246,196,83,0) 58%)` }} />
      <div style={{ position: "absolute", left: P.x, top: P.y, width: P.w, height: P.h, borderRadius: P.r, background: "#0d0d0f",
        boxShadow: "0 40px 100px rgba(0,0,0,0.75), 0 0 0 2px rgba(246,196,83,0.55), inset 0 0 0 2px rgba(255,255,255,0.10)",
        transform: `translateY(${(1 - ph) * 160}px) scale(${0.9 + 0.1 * ph})`, opacity: Math.min(1, ph * 1.5) }}>
        <div style={{ position: "absolute", left: P.bz, top: P.bz, width: SW, height: SH, borderRadius: P.r - P.bz, overflow: "hidden", background: "#fff" }}>
          {items.map((it, i) => {
            const next = items[i + 1], end = next ? next.at : b.to;
            if (t < it.at - 0.45 || (next && t > next.at + 0.5)) return null;
            const s = SW / 1075, inn = i === 0 ? 1 : ramp(t, it.at - 0.05, 0.45, inOut), out = next ? ramp(t, next.at - 0.05, 0.45, inOut) : 0;
            const y = (it.y0 ?? 0) + ((it.y1 ?? 0) - (it.y0 ?? 0)) * ramp(t, it.at + (i === 0 ? 0.35 : 0.3), Math.max(0.4, end - it.at - 0.45), inOut);
            return <div key={i} style={{ position: "absolute", inset: 0, overflow: "hidden", zIndex: i,
              transform: `translateX(${(1 - inn) * -SW + out * SW * 0.25}px) scale(${1 - 0.06 * out})`, filter: out > 0 ? `brightness(${1 - 0.45 * out})` : undefined,
              boxShadow: i > 0 ? "30px 0 60px rgba(0,0,0,0.35)" : undefined }}>
              <Img src={staticFile(it.file!)} style={{ position: "absolute", left: 0, top: -y * s, width: SW, height: (it.ih ?? 4000) * s }} />
            </div>;
          })}
          {/* a soft glare across the glass */}
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(115deg, rgba(255,255,255,0) ${-20 + 140 * ramp(t, b.from + 0.3, 1.4, inOut)}%, rgba(255,255,255,0.22) ${-8 + 140 * ramp(t, b.from + 0.3, 1.4, inOut)}%, rgba(255,255,255,0) ${4 + 140 * ramp(t, b.from + 0.3, 1.4, inOut)}%)`, zIndex: 9 }} />
        </div>
        <div style={{ position: "absolute", left: P.w / 2 - 70, top: P.bz + 14, width: 140, height: 36, borderRadius: 18, background: "#000", zIndex: 10 }} />
      </div>
      {b.label && <div style={{ position: "absolute", top: 1300, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: lab, transform: `translateY(${(1 - lab) * 24}px)` }}>
        <div style={{ fontFamily: font, fontWeight: 900, fontSize: 54, color: "#1a1206", background: GOLD, padding: "14px 38px 16px", borderRadius: 999, direction: "rtl",
          boxShadow: "0 12px 34px rgba(0,0,0,0.5)" }}>{b.label}</div>
      </div>}
      {b.text && <div style={{ position: "absolute", top: 1420, left: 0, right: 0, textAlign: "center", fontFamily: font, fontWeight: 700, fontSize: 38, color: "rgba(255,255,255,0.78)",
        direction: "ltr", opacity: lab }}>{b.text}</div>}
    </AbsoluteFill>
  );
};

/** notes: glass notifications that land one under the other on the chest, each on its word (reel 2 round 8: «עוד אנימציות זכוכית
 * יוקרתיות»). A note with mark "v" is the gold one — the lead he wants. Same glass as the round-7 checklists */
export const AeNotes: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.3 || t > b.to + 0.35) return null;
  const q = ramp(t, b.to, 0.3, inOut), top = b.y ?? 1310, H = 150, G = 18;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 1 - q }}>
      <div style={{ position: "absolute", left: 120, width: 830, top, display: "flex", flexDirection: "column", gap: G }}>
        {(b.items ?? []).map((it, i) => {
          const p = ramp(t, it.at - 0.1, 0.5, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
          const room = ramp(t, it.at - 0.3, 0.4, inOut), v = it.mark === "v";
          const gl = v ? 0.5 + 0.5 * Math.sin((t - it.at) * 3) : 0;
          return (
            <div key={i} style={{ height: H * room, marginBottom: room < 1 ? -G * (1 - room) : 0, opacity: Math.min(1, p * 1.4),
              transform: `translateY(${(1 - p) * -50}px) scale(${0.92 + 0.08 * p})` }}>
              <div style={{ direction: "rtl", height: H, display: "flex", alignItems: "center", gap: 26, padding: "0 34px", borderRadius: 40,
                background: v ? "linear-gradient(160deg, rgba(48,38,14,0.78), rgba(14,12,8,0.66))" : "linear-gradient(160deg, rgba(28,28,30,0.72), rgba(10,10,12,0.62))",
                border: `2px solid ${v ? "rgba(246,196,83,0.75)" : "rgba(255,255,255,0.16)"}`, backdropFilter: "blur(18px) saturate(1.2)", WebkitBackdropFilter: "blur(18px) saturate(1.2)",
                boxShadow: `0 24px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.22)${v ? `, 0 0 ${30 + 20 * gl}px rgba(246,196,83,${0.3 + 0.15 * gl})` : ""}` }}>
                <div style={{ width: 92, height: 92, flex: "none", borderRadius: 46, display: "flex", alignItems: "center", justifyContent: "center",
                  background: v ? GOLD : "rgba(255,255,255,0.14)", border: v ? "none" : "2px solid rgba(255,255,255,0.35)" }}>
                  <svg viewBox="0 0 40 40" width={54} height={54}>
                    {v ? <path d="M10 21 L17 28 L30 13" stroke="#1a1408" strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" fill="none" strokeDasharray={32} strokeDashoffset={32 * (1 - ramp(t, it.at + 0.25, 0.4, inOut))} />
                       : <><circle cx={20} cy={14} r={7} fill="#fff" /><path d="M6 36 C6 26 34 26 34 36 Z" fill="#fff" /></>}
                  </svg>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                  <span style={{ fontFamily: font, fontWeight: 800, fontSize: 52, color: v ? "#F6C453" : "#fff", whiteSpace: "nowrap", textShadow: "0 3px 12px rgba(0,0,0,0.5)" }}>{it.label}</span>
                  {it.sub && <span style={{ fontFamily: font, fontWeight: 600, fontSize: 36, color: "rgba(255,255,255,0.7)", whiteSpace: "nowrap" }}>{it.sub}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
