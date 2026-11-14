import React, { createContext, useContext, useEffect, useState } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { fitText } from "@remotion/layout-utils";
import { evolvePath } from "@remotion/paths";
import { B, FONT, GRAD, WHO_COLOR, clamp, fontReady, ink, inOut, outline, ramp } from "./look";
import { Card, cardsOf } from "./cards";
import { graphicsOf } from "./graphics";
import { Cut, Plan, Shot, Word, findWord, pushes, resolve, shotsOf } from "./timeline";
import { Face, SessionData, loadSession, selOf } from "./data";
import { Badge, CtaImg, Stat, Trip } from "./extras";
import { Lux, LuxP } from "./lux";
import { Flow, FlowP, GlassList, ListP } from "./glassList";
import { BOARD_THEMES, Board, BoardP, HAND, boardSfx } from "./boards";
import { GridFlow } from "./gridFlow";
import { AeBorder } from "./border";
import { AeBeat, AeCal, AeCard, AeClip, AeDrain, AeGlass, AeGlow, AeMap, AeMsgs, AeNum, AeMeter, AeProfile, AeRain, AeRows, AeScale, AeShrinkFrame, AeShrinkStage, AeType, AeIcon, AeLogo, AeArrow, AeChecks, AeBrands, AeAnger, AeDm, AeSite, AeNotes, AeGap, AeMarks, AeYear, AeWorld, Grain, Leak, aeLeaks, aeSfx, inShrink, shrinkStyle } from "./ae";

export const OUTRO = 1.6;
// beds: music in pieces (דין r7 2.11.2026: «בום דרמטי, תכבה את המוזיקה, בילדאפ מחדש… עצירה קומית ותמשיך עם המוזיקה המקורית מאותה נקודה»)
// at/until = reel seconds, from = the place in the track it starts from, fin/fout = fades (s)
type Bed = { file: string; vol: number; at: number; until?: number; from?: number; fin?: number; fout?: number;
  drops?: [number, number][];            // reel seconds: the bed stops on a beat («לא.») and comes back after it
  rise?: { at: number; dur: number; vol: number } };   // reel seconds: the level climbs toward the call to action // the brand card after the last word

// A session's own look (plans.json "_look") — אלון+אייל+דולב 26.10.2026: the CapCut route showed broken Hebrew captions he
// had to find himself, so these reels render here, in the approved project style: Fredoka, a colour per speaker, the logo
// pair under the captions, everything inside the IG/TikTok safe area, no music, his poster as the end card.
export type Look = { font?: string; colors?: { host: string; guest: string }; hotSame?: boolean; capX?: number; capY?: number; capYSplit?: number;
  safeW?: number; capFixed?: boolean; logoY?: number; splitSeam?: number; size?: number; soft?: boolean; logoW?: number; logoBottom?: number; end?: string; outro?: number; music?: boolean; fadeOut?: boolean;
  audio?: boolean;                       // one crossfaded dialogue track per reel (scripts/mk_audio.py → a/<id>.wav)
  clicks?: boolean;                      // a click on camera changes (false: only the opening one — «יותר מדיי מהסאונד של הקליק»)
  cta?: { title: string; sub?: string; y?: number; size?: number };
  ctaImg?: { file: string; y?: number; k?: number };   // the teaser's own CTA overlay instead of the pill (אורח K 28.10: «שתהיה מילה עקבית»)
  intro?: boolean;                      // false: no shutter on the first frame (ניב/דין 2.11.2026: «בלי הסאונד קליק בפתיחה»)
  review?: boolean };                    // review renders: the reel number + a running clock on top, so notes come as «ריל 3, שנייה 12.4»  // the comment keyword on the end card («תוסיף בסוף הנעה לפעולה להגיב כלוב»)
export const lookOf = (plans: Record<string, unknown>): Look => ((plans as { _look?: Look })._look ?? {});
export const outroOf = (plans: Record<string, unknown>) => lookOf(plans).outro ?? OUTRO;
const LookCtx = createContext<Look>({});

const sec = () => { const { fps } = useVideoConfig(); return useCurrentFrame() / fps; };
// the session's graded-selects map and face positions, loaded once per bundle (data.ts)
const Ctx = createContext<{ sel: (t: number) => number; face: Face }>({ sel: (t) => t, face: { "1": { x: 0.5, y: 0.35 }, "2": { x: 0.5, y: 0.35 } } });

// ── camera ────────────────────────────────────────────────────────────────────────────────────────────────
// The 1920×1080 camera reframed to 9:16 around the face. z = zoom over "fill the height"; the face sits at faceY of the box.
type CamP = { cam: 1 | 2 | 3; src: number; z: (t: number) => number; box?: { w: number; h: number }; faceY?: number; matte?: { file: string; src0: number };
  track?: number[][] };
// track: the speaker's face per source time [[src, x, y], …] (plan "follow", from a face tracker) — the frame glides with him
// instead of holding the session's one face position (אורח B r2, 29.10.2026: «שהמצלמה תעקוב אחריו ככה שיהיה בדיוק באמצע»)
const trackAt = (tr: number[][], t: number) => {
  let lo = 0, hi = tr.length - 1;
  if (t <= tr[0][0]) return tr[0]; if (t >= tr[hi][0]) return tr[hi];
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (tr[m][0] <= t) lo = m; else hi = m; }
  const a = tr[lo], b = tr[hi], k = (t - a[0]) / Math.max(1e-3, b[0] - a[0]);
  return b[0] - a[0] > 1.2 ? (k < 0.5 ? a : b) : [t, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
};
const Cam: React.FC<CamP> = ({ cam, src, z, box, faceY = 0.36, matte, track }) => {
  const t = sec();
  const { fps, width, height } = useVideoConfig();
  const W = box?.w ?? width, H = box?.h ?? height;
  const s = (H / 1080) * z(t), w = 1920 * s, h = 1080 * s;
  const { sel, face } = useContext(Ctx);
  const f0 = (face as Record<string, { x: number; y: number; cam?: number }>)[String(cam)];
  const tk = track?.length ? trackAt(track, src + t) : null;
  const f = tk ? { ...f0, x: tk[1], y: tk[2] } : f0;
  const left = Math.min(0, Math.max(W - w, W / 2 - f.x * w));
  const top = Math.min(0, Math.max(H - h, H * faceY - f.y * h));
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: matte ? "transparent" : "#000", width: W, height: H }}>
      {matte
        ? <OffthreadVideo src={staticFile(matte.file)} transparent startFrom={Math.round((src - matte.src0) * fps)} muted style={{ position: "absolute", left, top, width: w, height: h }} />
        : <OffthreadVideo src={staticFile(`cam${cam === 3 ? f.cam ?? 3 : cam}s.mp4`)} startFrom={Math.round(sel(src) * fps)} muted style={{ position: "absolute", left, top, width: w, height: h }} />}
    </AbsoluteFill>
  );
};

/** the zoom of one shot at shot-time u: its framing, the settle of the opening, keyword pushes, a slow drift */
// soft: a slower, smaller push (ניב r8 2.11.2026: «כמה קיפריימים חדים מדיי ולא נעימים, בוא נעדן אותם»)
const zoomFn = (s: Shot, push: number[], first: boolean, close: number[] = [], soft = false, punch: number[][] = []) => (u: number) => {
  const t = s.at + u;
  let z = s.z;
  if (first) z += 0.22 * (1 - ramp(u, 0, 0.83, inOut)); // Alon's opening: the frame settles in, 0.83 s FreeCurveInOut
  if (s.kind === "react") return z * (1 + 0.06 * Math.min(1, u / Math.max(0.6, s.end - s.at))); // a slow push over the reaction
  for (const p of push) {
    const k = (s.z > 1.1 ? 0.07 : 0.14) * (soft ? 0.6 : 1); // ×1.14 from wide, ×1.07 from tight
    const up = soft ? 1.3 : 0.7, rise = ramp(t, p - up, up, inOut), fall = ramp(t, p + 1.1, soft ? 1.6 : 0.9, inOut);
    if (t > p - up && p - up >= s.at - 0.05) z += k * rise * (1 - fall);
  }
  // close: an eased push into a close-up that stays to the end of the shot (round 7: «המילים האחרונות עם קלוז אפ על אורח B»)
  for (const p of close) if (t > p - 0.6) z += 0.32 * ramp(t, p - 0.6, 0.8, inOut);
  // punch: a dramatic push that lands with the hit and holds across the cuts, then eases back (דין r7 3.11: «כשהסאונד נכנס ב״לא״ צריך שיהיה זום אין דרמטי»)
  for (const [a, b] of punch) if (t > a - 0.05) z += 0.3 * ramp(t, a - 0.05, 1.3, (v) => 1 - Math.pow(1 - v, 3)) * (1 - ramp(t, b, 0.9, inOut));
  // never fully static — the drift runs over the whole stretch of one camera, so an edit inside it (a dissolve, a seam) does not
  // snap the size back (עומר 12.11.2026: «קפיצות זומים שבורות»)
  return z * (1 + 0.006 * (t - (s.run0 ?? s.at)));
};

// seam: where the two halves meet — the fixed caption line when the look has one (the captions sit on the seam)
const Split: React.FC<{ src: number; u0: number; top?: 1 | 2 | 3; bottom?: 1 | 2 | 3; shift?: number; seam?: number }> = ({ src, top = 2, bottom = 1, shift = 0, seam = 960 }) => (
  <AbsoluteFill>
    <div style={{ position: "absolute", top: 0, left: 0, width: 1080, height: seam - 3, overflow: "hidden" }}>
      <Cam cam={top} src={src + shift} z={() => 1.3} box={{ w: 1080, h: seam - 3 }} faceY={0.46} />
    </div>
    <div style={{ position: "absolute", top: seam + 3, left: 0, width: 1080, height: 1917 - seam, overflow: "hidden" }}>
      <Cam cam={bottom} src={src} z={() => (bottom === 3 ? 1.55 : 1.3)} box={{ w: 1080, h: 1917 - seam }} faceY={0.46} />
    </div>
    <div style={{ position: "absolute", top: seam - 3, left: 0, right: 0, height: 6, background: "#000" }} />
  </AbsoluteFill>
);

const MIX_F = 10;   // 0.33 s
const MixIn: React.FC<{ on: boolean; children: React.ReactNode }> = ({ on, children }) => {
  const f = useCurrentFrame();
  return on ? <AbsoluteFill style={{ opacity: inOut(Math.min(1, f / MIX_F)) }}>{children}</AbsoluteFill> : <>{children}</>;
};

// ── captions ──────────────────────────────────────────────────────────────────────────────────────────────
const SAFE_W = 860, SIZE = 92;
const Captions: React.FC<{ cards: Card[]; yAt: (t: number) => number }> = ({ cards, yAt }) => {
  const t = sec();
  const L = useContext(LookCtx); const F = L.font ? "ReelLook" : FONT, W_ = L.safeW ?? SAFE_W, SZ = L.size ?? SIZE, X = L.capX ?? 540;
  const shadow = L.soft ? `${ink(2.2)}, 0 3px 10px rgba(0,0,0,0.3)` : outline;
  const c = cards.find((x) => t >= x.from && t < x.to + 0.2);
  if (!c) return null;
  const grow = ramp(t, c.from, 0.26, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2)); // Grow in, a touch of overshoot
  const out = ramp(t, c.to, 0.2); // Mini Zoom out
  const color = L.colors ? L.colors[c.who] : WHO_COLOR[c.who];
  const y = yAt(t);
  return (
    <div style={{ position: "absolute", left: X - W_ / 2, width: W_, top: y, transform: `translateY(-50%) scale(${(0.6 + 0.4 * grow) * (1 - 0.1 * out)})`,
      opacity: Math.min(1, grow * 1.6) * (1 - out), direction: "rtl", textAlign: "center", fontFamily: F, fontWeight: 900 }}>
      {c.rows.map((row, i) => {
        const text = row.map((w) => w.text).join(" ");
        const size = Math.min(SZ, fitText({ text, withinWidth: W_, fontFamily: F, fontWeight: "900" }).fontSize);
        return (
          <div key={i} style={{ fontSize: size, lineHeight: 1.12, whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>
            {row.map((w, k) => (
              <span key={k} style={{ color: w.hot && !L.hotSame ? ((L as { hot?: string }).hot ?? B.accent) : color, textShadow: shadow }}>{w.text}{k < row.length - 1 ? " " : ""}</span>
            ))}
          </div>
        );
      })}
    </div>
  );
};

// ── brand graphics (spec: "תווית מעוגלת מוטה ‎-3°" for a keyword, "ספרות גדולות במעבר צבע" for a number) ──────
export const Pill: React.FC<{ at: number; until: number; text: string }> = ({ at, until, text }) => {
  const t = sec();
  if (t < at - 0.05 || t > until + 0.3) return null;
  const p = ramp(t, at, 0.32, (x) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2)), out = ramp(t, until, 0.25);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 205, display: "flex", justifyContent: "center", opacity: Math.min(1, p * 2) * (1 - out) }}>
      <div style={{ background: GRAD, color: "#fff", fontFamily: FONT, fontWeight: 900, fontSize: 70, lineHeight: 1, padding: "26px 48px 30px", borderRadius: 999,
        transform: `rotate(-3deg) scale(${0.5 + 0.5 * p - 0.08 * out})`, direction: "rtl", whiteSpace: "nowrap",
        boxShadow: "0 18px 40px rgba(211,32,32,0.35), 0 4px 0 rgba(0,0,0,0.25)" }}>{text}</div>
    </div>
  );
};

export const Counter: React.FC<{ at: number; until: number; to: number; suffix?: string; label?: string }> = ({ at, until, to, suffix = "", label }) => {
  const t = sec();
  if (t < at - 0.05 || t > until + 0.3) return null;
  const run = ramp(t, at, 0.9, inOut), p = ramp(t, at, 0.3), out = ramp(t, until, 0.25);
  const v = Math.round(to * run);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1490, display: "flex", flexDirection: "column", alignItems: "center", opacity: p * (1 - out),
      transform: `scale(${0.85 + 0.15 * p})` }}>
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 230, lineHeight: 0.9, direction: "ltr", background: GRAD, WebkitBackgroundClip: "text", color: "transparent",
        filter: "drop-shadow(0 6px 0 rgba(0,0,0,0.85)) drop-shadow(0 0 24px rgba(255,59,46,0.35))" }}>{v}{suffix}</div>
      {label && <div style={{ marginTop: 14, background: B.panel, borderRight: `8px solid ${B.accent}`, color: B.text, fontFamily: FONT, fontWeight: 800, fontSize: 48,
        padding: "12px 28px", borderRadius: 14, direction: "rtl", opacity: ramp(t, at + 0.5, 0.25) }}>{label}</div>}
    </div>
  );
};

const Logo: React.FC<{ hide: [number, number][]; y: number }> = ({ hide, y }) => {
  const t = sec();
  const L = useContext(LookCtx);
  // a slower, eased fade when the caption line is fixed — the logos give way to a card, never pop (אורח B 29.10)
  const fd = L.capFixed ? 0.45 : 0.25, ez = L.capFixed ? inOut : undefined;
  const h = Math.max(0, ...hide.map(([a, b]) => Math.min(ramp(t, a - fd, fd, ez), 1 - ramp(t, b, fd, ez))));
  const file = (L as { logoFile?: string }).logoFile ?? "logo.png";
  if (L.logoW) return <Img src={staticFile(file)} style={{ position: "absolute", width: L.logoW, left: (L.capX ?? 540) - L.logoW / 2, top: (L.logoBottom ?? 1432) - L.logoW * 400 / 840, opacity: 0.95 * (1 - h) }} />;
  return <Img src={staticFile("logo.png")} style={{ position: "absolute", width: 300, left: 390, top: y, opacity: 0.95 * (1 - h) }} />;
};

const Sfx: React.FC<{ at: number; file: string; vol?: number }> = ({ at, file, vol = 0.5 }) => {
  const { fps } = useVideoConfig();
  return <Sequence from={Math.max(0, Math.round(at * fps))} durationInFrames={Math.round(2.5 * fps)}><Audio src={staticFile(`sfx/${file}`)} volume={vol} /></Sequence>;
};

// the end card's call to action: a gold pill with the comment keyword under the poster's «הפרק המלא עכשיו בחוץ» line,
// inside the IG/TikTok safe width (centre x = capX), in after the poster settles
const Cta: React.FC<{ title: string; sub?: string; y?: number; u: number; size?: number }> = ({ title, sub, y = 1500, u, size = 84 }) => {
  const L = useContext(LookCtx);
  const p = ramp(u, 0.35, 0.45, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2)), q = ramp(u, 0.75, 0.35, inOut);
  const breathe = 1 + 0.025 * Math.sin(Math.max(0, u - 0.8) * 4.2);
  const F = L.font ? "ReelLook" : FONT;
  return (
    <div style={{ position: "absolute", left: (L.capX ?? 540) - 460, width: 920, top: y, transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", direction: "rtl" }}>
      <div style={{ position: "relative", fontFamily: F, fontWeight: 900, fontSize: size, lineHeight: 1, color: "#1a1206", padding: `${Math.round(size * 0.3)}px ${Math.round(size * 0.7)}px ${Math.round(size * 0.36)}px`, borderRadius: 999,
        background: "linear-gradient(180deg, #FFE7A3 0%, #F6C453 42%, #C98F1E 100%)", boxShadow: "0 0 0 3px rgba(255,231,163,0.55), 0 18px 46px rgba(246,196,83,0.38), 0 6px 0 rgba(0,0,0,0.5)",
        transform: `scale(${(0.55 + 0.45 * p) * breathe})`, opacity: Math.min(1, p * 2), whiteSpace: "nowrap" }}>{title}</div>
      {sub && <div style={{ position: "relative", marginTop: 26, fontFamily: F, fontWeight: 700, fontSize: 50, color: "#fff", textShadow: "0 3px 12px rgba(0,0,0,0.8)",
        opacity: q, transform: `translateY(${(1 - q) * 18}px)`, whiteSpace: "nowrap" }}>{sub}</div>}
    </div>
  );
};

type BehindP = { from: number; to: number; file: string; src0: number; kind?: "claude" | "screens" | "code" | "graph" | "crash"; img?: string; srcs?: string[];
  x?: number; y?: number; size?: number; turn?: number; rise?: number };
/** WhiteBoard's real screens fanning out behind the speaker (teaser v9fx) */
const ScreensBehind: React.FC<{ from: number; to: number; srcs: string[] }> = ({ from, to, srcs }) => {
  const t = sec();
  const slots = [{ x: 60, y: 160, r: -9 }, { x: 560, y: 120, r: 7 }, { x: 20, y: 560, r: 6 }, { x: 600, y: 520, r: -7 }, { x: 300, y: 40, r: 2 }, { x: 330, y: 760, r: -3 }];
  const every = Math.min(0.6, (to - from - 0.8) / Math.max(1, srcs.length));
  const out = 1 - ramp(t, to - 0.25, 0.25);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      {srcs.slice(0, slots.length).map((src, i) => {
        const k = ramp(t, from + i * every, 0.4, (x) => 1 - Math.pow(1 - x, 3)), q = slots[i];
        return <Img key={src} src={staticFile(src)} style={{ position: "absolute", left: q.x, top: q.y, width: 460, borderRadius: 18, opacity: k,
          transform: `translateY(${(1 - k) * 80}px) rotate(${q.r}deg) scale(${0.85 + 0.15 * k})`, boxShadow: "0 20px 50px rgba(0,0,0,0.6)", border: "3px solid rgba(255,255,255,0.85)" }} />;
      })}
    </AbsoluteFill>
  );
};
/** the files of the repo running behind the speaker (teaser CodeBehind) */
const CodeBehind: React.FC<{ from: number; to: number; files: string[] }> = ({ from, to, files }) => {
  const t = sec();
  const k = ramp(t, from, 0.25) * (1 - ramp(t, to - 0.2, 0.2));
  const rowH = 46, y = -ramp(t, from, to - from, (x) => x) * rowH * 30;
  return (
    <AbsoluteFill style={{ background: "rgba(8,10,14,0.82)", overflow: "hidden", direction: "ltr", opacity: k }}>
      <div style={{ position: "absolute", left: 40, right: 40, top: 120 + y, fontFamily: "Menlo, monospace", fontSize: 26, color: "#7ee787", opacity: 0.85 }}>
        {[...files, ...files].map((f, i) => <div key={i} style={{ height: rowH, whiteSpace: "nowrap", overflow: "hidden" }}><span style={{ color: "#3fb950" }}>+ </span>{f}</div>)}
      </div>
    </AbsoluteFill>
  );
};

/** a rising chart behind the speaker (דין r3 2.11.2026: «תכניס גרף עולה מאחורי דין») — the cut-out lies over it */
const GraphBehind: React.FC<{ from: number; to: number }> = ({ from, to }) => {
  const t = sec();
  const k = ramp(t, from, 0.3, inOut) * (1 - ramp(t, to - 0.3, 0.3, inOut)), run = ramp(t, from + 0.15, Math.min(1.8, to - from - 0.4), inOut);
  const pts = [[60, 1000], [200, 930], [330, 960], [470, 800], [600, 830], [740, 600], [870, 520], [1020, 260]];
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
  const tip = (() => { const n = (pts.length - 1) * run, i = Math.min(pts.length - 2, Math.floor(n)), f = n - i;
    return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f]; })();
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <AbsoluteFill style={{ background: "rgba(6,8,10,0.55)" }} />
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="gb-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#F6C453" stopOpacity="0.45" /><stop offset="1" stopColor="#F6C453" stopOpacity="0" /></linearGradient>
          <clipPath id="gb-c"><rect x={0} y={0} width={tip[0]} height={1920} /></clipPath>
        </defs>
        {[300, 500, 700, 900].map((y) => <line key={y} x1={40} x2={1040} y1={y} y2={y} stroke="rgba(255,255,255,0.12)" strokeWidth={2} />)}
        <path d={`${d} L1020 1060 L60 1060 Z`} fill="url(#gb-a)" clipPath="url(#gb-c)" />
        <path d={d} fill="none" stroke="#F6C453" strokeWidth={12} strokeLinejoin="round" strokeLinecap="round" {...evolvePath(run, d)}
          style={{ filter: "drop-shadow(0 0 20px rgba(246,196,83,0.7))" }} />
        <circle cx={tip[0]} cy={tip[1]} r={18} fill="#FFF1C4" style={{ filter: "drop-shadow(0 0 24px rgba(246,196,83,1))" }} />
      </svg>
    </AbsoluteFill>
  );
};

/** a crash that turns into a climb behind the speaker (ניב r10 3.11.2026: «גרף יורד באדום מאחורי ניב — שיוצא מהצד השני
 * כעלייה תלולה בצבע ירוק»): the red line draws left→right falling, reaches him on the turn, and leaves his far side rising
 * steeply in green; the cut-out lies over the middle, so the line runs behind him */
const CrashBehind: React.FC<{ from: number; to: number; turn: number; rise: number }> = ({ from, to, turn, rise }) => {
  const t = sec();
  const k = ramp(t, from, 0.3, inOut) * (1 - ramp(t, to - 0.35, 0.35, inOut));
  const down = [[20, 400], [90, 480], [150, 450], [220, 630], [280, 600], [360, 790], [430, 760], [540, 980]];
  const up = [[540, 980], [640, 820], [700, 860], [790, 540], [850, 580], [950, 230], [1060, 50]];
  const path = (pts: number[][]) => pts.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
  const tipOf = (pts: number[][], run: number) => { const n = (pts.length - 1) * run, i = Math.min(pts.length - 2, Math.floor(n)), f = n - i;
    return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f]; };
  const r1 = ramp(t, from + 0.1, Math.max(0.4, turn - from - 0.1), (v) => v), r2 = ramp(t, turn, rise, (v) => 1 - Math.pow(1 - v, 2.4));
  const dd = path(down), du = path(up), onUp = t >= turn;
  const tip = onUp ? tipOf(up, r2) : tipOf(down, r1);
  const RED = "#FF3B4E", GREEN = "#2BEA8A", col = onUp ? GREEN : RED;
  const flash = ramp(t, turn, 0.12) * (1 - ramp(t, turn + 0.12, 0.5, inOut));
  return (
    <AbsoluteFill style={{ opacity: k }}>
      <AbsoluteFill style={{ background: "rgba(5,7,10,0.6)" }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 62%, ${onUp ? "rgba(43,234,138,0.22)" : "rgba(255,59,78,0.2)"} 0%, rgba(0,0,0,0) 60%)` }} />
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="cb-r" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={RED} stopOpacity="0.35" /><stop offset="1" stopColor={RED} stopOpacity="0" /></linearGradient>
          <linearGradient id="cb-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={GREEN} stopOpacity="0.4" /><stop offset="1" stopColor={GREEN} stopOpacity="0" /></linearGradient>
          <clipPath id="cb-c1"><rect x={0} y={0} width={onUp ? 1080 : tip[0]} height={1920} /></clipPath>
          <clipPath id="cb-c2"><rect x={0} y={0} width={onUp ? tip[0] : 0} height={1920} /></clipPath>
        </defs>
        {[300, 500, 700, 900, 1100].map((y) => <line key={y} x1={30} x2={1050} y1={y} y2={y} stroke="rgba(255,255,255,0.1)" strokeWidth={2} />)}
        {[200, 400, 600, 800].map((x) => <line key={x} x1={x} x2={x} y1={120} y2={1240} stroke="rgba(255,255,255,0.05)" strokeWidth={2} />)}
        <path d={`${dd} L540 1260 L20 1260 Z`} fill="url(#cb-r)" clipPath="url(#cb-c1)" opacity={onUp ? 1 - 0.6 * r2 : 1} />
        <path d={dd} fill="none" stroke={RED} strokeWidth={18} strokeLinejoin="round" strokeLinecap="round" {...evolvePath(onUp ? 1 : r1, dd)}
          opacity={onUp ? 1 - 0.55 * r2 : 1} style={{ filter: `drop-shadow(0 0 18px ${RED})` }} />
        <path d={`${du} L1050 1260 L540 1260 Z`} fill="url(#cb-g)" clipPath="url(#cb-c2)" />
        {onUp && <path d={du} fill="none" stroke={GREEN} strokeWidth={20} strokeLinejoin="round" strokeLinecap="round" {...evolvePath(r2, du)}
          style={{ filter: `drop-shadow(0 0 22px ${GREEN})` }} />}
        <circle cx={540} cy={980} r={30 + 90 * flash} fill="none" stroke={GREEN} strokeWidth={6} opacity={flash} />
        <circle cx={tip[0]} cy={tip[1]} r={22} fill={onUp ? "#D9FFE9" : "#FFD9DD"} style={{ filter: `drop-shadow(0 0 26px ${col})` }} />
      </svg>
    </AbsoluteFill>
  );
};

/** the Claude mark behind the speaker (the cut-out on top) — as in the teaser (v11: off his left shoulder, 600 px) */
const Behind: React.FC<BehindP & { files?: string[] }> = ({ from, to, img = "claude-symbol.png", x = 500, y = 190, size = 600, kind = "claude", srcs, files, turn, rise }) => {
  const t = sec();
  if (kind === "screens") return <ScreensBehind from={from} to={to} srcs={srcs ?? []} />;
  if (kind === "code") return <CodeBehind from={from} to={to} files={files ?? []} />;
  if (kind === "graph") return <GraphBehind from={from} to={to} />;
  if (kind === "crash") return <CrashBehind from={from} to={to} turn={turn ?? (from + to) / 2} rise={rise ?? 1.2} />;
  const k = ramp(t, from, 0.35, (v) => 1 - Math.pow(1 - v, 3)) * (1 - ramp(t, to - 0.25, 0.25));
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 74% 26%, rgba(217,119,87,0.38) 0%, rgba(217,119,87,0) 42%)", opacity: k }} />
      <Img src={staticFile(img)} style={{ position: "absolute", top: y, left: x, width: size, height: size, opacity: k,
        transform: `scale(${0.7 + 0.3 * k}) rotate(${((t - from) / Math.max(0.1, to - from)) * 25}deg)`, filter: "drop-shadow(0 0 40px rgba(217,119,87,0.7))" }} />
    </AbsoluteFill>
  );
};

/** a still from the day itself over the picture (אלון+אייל+דולב 26.10.2026: «בירולס מאותו היום») — the photo whole, over a
 * blurred copy of itself, with a slow push; the voice runs on under it */
const BRoll: React.FC<{ from: number; to: number; img: string; zoom?: number; cutIn?: boolean; cutOut?: boolean; still?: boolean }> = ({ from, to, img, zoom, cutIn, cutOut, still }) => {
  const t = sec();
  const { fps } = useVideoConfig();   // every hook before the early return (React #310)
  if (t < from - 0.01 || t > to + (cutOut ? -0.001 : 0.01)) return null;
  const k = Math.min(cutIn ? 1 : ramp(t, from, 0.12), cutOut ? 1 : 1 - ramp(t, to - 0.1, 0.1)), u = (t - from) / Math.max(0.1, to - from);
  if (/\.(mp4|mov)$/i.test(img)) return (   // 9:16 footage from the day: the whole frame, a slow push
    <AbsoluteFill style={{ opacity: k, background: "#000" }}>
      <Sequence from={Math.round(from * fps)} layout="none">
        <OffthreadVideo src={staticFile(img)} muted style={{ position: "absolute", inset: 0, width: 1080, height: 1920, objectFit: "cover",
          // zoom: a dramatic push-in that lands on the last word («זום אין דרמטי מהזוית העליונה»)
          // still: the clip as shot, no push (צומת 20 round 4: «מעברים נקיים בלי אפקטים»)
          transform: `scale(${still ? 1 : zoom ? 1.02 + (zoom - 1.02) * Math.pow(u, 3) : 1.02 + 0.04 * u})` }} />
      </Sequence>
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{ opacity: k, background: "#000" }}>
      <Img src={staticFile(img)} style={{ position: "absolute", inset: -60, width: 1200, height: 2040, objectFit: "cover", filter: "blur(38px) brightness(0.55)" }} />
      <Img src={staticFile(img)} style={{ position: "absolute", left: 40, top: 160, width: 1000, height: 1300, objectFit: "contain", transform: `scale(${1 + 0.05 * u})`,
        filter: "drop-shadow(0 24px 50px rgba(0,0,0,0.6))" }} />
    </AbsoluteFill>
  );
};

/** a white flash transition (2 frames up, a soft decay) — the hook landing into the story («אפקט פלאש אחרי אפס עגול») */
const Flash: React.FC<{ at: number }> = ({ at }) => {
  const t = sec();
  if (t < at - 0.1 || t > at + 0.4) return null;
  const k = t < at ? ramp(t, at - 0.067, 0.067) : 1 - ramp(t, at, 0.3, (x) => 1 - Math.pow(1 - x, 2));
  return <AbsoluteFill style={{ background: "#fff", opacity: k * 0.95 }} />;
};

// review stamp: reel number + reel clock (seconds, one decimal) — what Alon quotes in his notes; never in a final render
const Stamp: React.FC<{ n?: number }> = ({ n }) => {
  const t = sec();
  const m = Math.floor(t / 60), ss = (t - m * 60).toFixed(1).padStart(4, "0");
  return (
    <div style={{ position: "absolute", top: 46, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div style={{ direction: "ltr", fontFamily: "Menlo, monospace", fontWeight: 700, fontSize: 46, color: "#fff", background: "rgba(0,0,0,0.72)",
        padding: "10px 26px", borderRadius: 14, letterSpacing: "0.02em", border: "2px solid rgba(255,255,255,0.35)" }}>
        <span style={{ color: "#F6C453" }}>ריל {String(n ?? 0).padStart(2, "0")}</span>{`   ${m}:${ss}`}
      </div>
    </div>
  );
};

// money as green glass panels (אלון+אייל+דולב 26.10.2026: «בזמן שאני סופר את הכסף… חלוניות זכוכית ירוקות של הסכומים»; on
// «סורבו» they turn red and shatter with the sound of breaking glass). Top right, beside the face, never over it.
type GlassItem = { at: number; amount: string; label: string };
const SHARDS = [[0, 0, 38, 0, 30, 46, 0, 58], [38, 0, 100, 0, 72, 40, 30, 46], [72, 40, 100, 0, 100, 62], [0, 58, 30, 46, 46, 100, 0, 100],
  [30, 46, 72, 40, 60, 100, 46, 100], [72, 40, 100, 62, 100, 100, 60, 100]];
export const Glass: React.FC<{ items: GlassItem[]; hide: number; recall: number; shatter: number }> = ({ items, hide, recall, shatter }) => {
  const t = sec();
  const L = useContext(LookCtx); const F = L.font ? "ReelLook" : FONT;
  if (t < items[0].at - 0.1 || t > shatter + 1.6) return null;
  const on = t < hide + 0.3 || t >= recall - 0.05;
  if (!on) return null;
  const red = ramp(t, shatter, 0.18), brk = Math.max(0, t - shatter - 0.22);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {items.map((it, i) => {
        const inAt = t >= recall - 0.05 ? recall + i * 0.12 : it.at - 0.05;
        const p = ramp(t, inAt, 0.35, (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2));
        const out = t < recall - 0.05 ? ramp(t, hide, 0.3) : 0;
        if (p <= 0 || out >= 1) return null;
        const top = 200 + i * 128, left = 770, w = 280, h = 112;
        const tint = (g: number, r: number) => `rgba(${Math.round(40 + 215 * red)}, ${Math.round(210 - 160 * red)}, ${Math.round(120 - 70 * red)}, ${g + r * red})`;
        const face = (
          <div style={{ position: "absolute", inset: 0, borderRadius: 22, background: `linear-gradient(135deg, ${tint(0.34, 0.05)}, ${tint(0.12, 0.05)})`,
            border: `2px solid ${tint(0.75, 0)}`, boxShadow: `0 0 30px ${tint(0.35, 0)}, inset 0 1px 0 rgba(255,255,255,0.45)`, backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", direction: "rtl" }}>
            <div style={{ fontFamily: F, fontWeight: 900, fontSize: 46, lineHeight: 1, color: "#fff", direction: "ltr", textShadow: "0 2px 10px rgba(0,0,0,0.45)" }}>{it.amount}</div>
            <div style={{ fontFamily: F, fontWeight: 700, fontSize: 24, marginTop: 6, color: "rgba(255,255,255,0.92)", textShadow: "0 2px 8px rgba(0,0,0,0.5)" }}>{it.label}</div>
          </div>
        );
        const base: React.CSSProperties = { position: "absolute", left, top, width: w, height: h, opacity: Math.min(1, p * 1.6) * (1 - out),
          transform: `translateX(${(1 - p) * 60}px) scale(${0.85 + 0.15 * p})` };
        if (brk <= 0) {
          const crack = red > 0.5 ? (
            <svg style={{ position: "absolute", inset: 0 }} viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M38,0 L30,46 L0,58 M30,46 L72,40 L100,0 M72,40 L100,62 M30,46 L46,100 M72,40 L60,100" stroke="rgba(255,255,255,0.9)" strokeWidth={0.7} fill="none" />
            </svg>) : null;
          return <div key={i} style={{ ...base, transform: `${base.transform} translateX(${red > 0 ? Math.sin(t * 90) * 6 * (1 - red) : 0}px)` }}>{face}{crack}</div>;
        }
        // shards fly apart and fall
        return (
          <div key={i} style={{ ...base, transform: "none" }}>
            {SHARDS.map((pts, k) => {
              const poly = pts.reduce((acc: string[], v, j) => (j % 2 ? acc : [...acc, `${v}% ${pts[j + 1]}%`]), []).join(", ");
              const dx = (60 + (k % 3) * 70) * brk, dy = 900 * brk * brk - 80 * brk + (k > 2 ? 60 * brk : 0);   // away from the face: right and down
              const rot = (k % 2 ? 1 : -1) * 160 * brk;
              return <div key={k} style={{ position: "absolute", inset: 0, clipPath: `polygon(${poly})`, transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg)`,
                opacity: Math.max(0, 1 - brk * 0.9) }}>{face}</div>;
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const Outro: React.FC<{ at: number }> = ({ at }) => {
  const t = sec();
  if (t < at) return null;
  const u = t - at, slam = ramp(u, 0.12, 0.35);
  const L = useContext(LookCtx);
  // fade out (תוכן הבונקר 4.11.26: «פייד אאוט») — the picture and the CTA go to black over the outro, no card
  if (L.fadeOut) return <AbsoluteFill style={{ background: "#000", opacity: ramp(u, 0, L.outro ?? OUTRO, inOut) }} />;
  if (L.end) return (
    <AbsoluteFill style={{ background: "#000", opacity: ramp(u, 0, 0.2) }}>
      <Img src={staticFile(L.end)} style={{ position: "absolute", width: 1080, height: 1920, objectFit: "cover", transform: `scale(${1 + 0.035 * Math.min(1, u / (L.outro ?? OUTRO))})` }} />
      {L.ctaImg ? <CtaImg u={u} {...L.ctaImg} /> : L.cta && <Cta {...L.cta} u={u} />}
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{ background: B.bg, opacity: ramp(u, 0, 0.18), alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 46%, rgba(211,32,32,0.22) 0%, transparent 60%)" }} />
      <Img src={staticFile("logo.png")} style={{ width: 620, opacity: slam, transform: `scale(${1.25 - 0.25 * slam})`, filter: `blur(${(1 - slam) * 14}px)` }} />
    </AbsoluteFill>
  );
};

/** every camera shot inside the AE shrink window (ae.tsx) — one transform for the whole camera stack */
const CamWrap: React.FC<{ beats: AeBeat[]; children: React.ReactNode }> = ({ beats, children }) => {
  const t = sec();
  return <AbsoluteFill style={shrinkStyle(t, beats)}>{children}</AbsoluteFill>;
};

// ── the reel ──────────────────────────────────────────────────────────────────────────────────────────────
const useReel = (id: string) => {
  const [d, setD] = useState<{ plan: Plan; cut: Cut; data: SessionData } | null>(null);
  const [h] = useState(() => delayRender(id));
  useEffect(() => {
    loadSession().then(async (data) => {
      const plan = data.plans[id];
      if (plan) {
        const L = lookOf(data.plans as Record<string, unknown>);
        const font = L.font ? new FontFace("ReelLook", `url(${staticFile(L.font)})`).load().then((f) => { document.fonts.add(f); }) : Promise.resolve();
        // the handwritten boards (boards.tsx «paper» / «report») bring their own face — public/Hand.ttf
        const hand = /"theme":\s*"(paper|report)"/.test(JSON.stringify(plan)) ? new FontFace(HAND, `url(${staticFile("Hand.ttf")})`).load().then((f) => { document.fonts.add(f); }) : Promise.resolve();
        const [cut] = await Promise.all([fetch(staticFile(plan.file)).then((r) => r.json()), fontReady(), font, hand]);
        setD({ plan, cut, data });
      }
      continueRender(h);
    });
  }, [h, id]);
  return d;
};

export const Reel: React.FC<{ id: string; music?: boolean; review?: boolean }> = ({ id, music = true, review }) => {
  const r = useReel(id);
  const { fps } = useVideoConfig();
  if (!r) return null;
  const { plan, cut, data } = r;
  const D = cut.duration;
  const L0 = lookOf(data.plans as Record<string, unknown>), L = review === false ? { ...L0, review: false } : L0, OUT = outroOf(data.plans as Record<string, unknown>), withMusic = music && L.music !== false;
  const shots = shotsOf(cut, plan);
  // mix: a jump cut that dissolves — the outgoing shot plays on under the incoming one while it fades in (round 10)
  const isMix = (t?: number) => t !== undefined && (plan.mix ?? []).some((x) => Math.abs(x - t) < 0.06);
  // `music: false` on a plan = that reel goes out with no bed at all (אורח K r5, 29.10.2026: «בוא נעשה אותו בלי מוזיקה»)
  const pm0 = (plan as { music?: false | { file: string; vol: number; from?: number; drops?: [number, number][] } }).music;
  const pm = pm0 || undefined;
  const b0 = (plan as { behind?: BehindP | BehindP[] }).behind;
  const behinds: BehindP[] = !b0 ? [] : Array.isArray(b0) ? b0 : [b0];
  const wbFiles = (plan as { files?: string[] }).files ?? [];
  const wAt = (k: string | number) => { if (typeof k === "number") return k; const w = findWord(cut, k); if (!w) throw new Error(`glass anchor not found: ${k}`); return w.at; };
  const glass = plan.glass ? { items: plan.glass.items.map((g) => ({ ...g, at: wAt(g.at) })), hide: wAt(plan.glass.hide), recall: wAt(plan.glass.recall), shatter: wAt(plan.glass.shatter) } : null;
  const push = pushes(cut, plan);
  const soft = !!(plan as { pushSoft?: boolean }).pushSoft;
  const punch = (plan as { punch?: number[][] }).punch ?? [];
  const follow = (plan as { follow?: Record<string, number[][]> }).follow;
  const close = ((plan as { close?: string[] }).close ?? []).map((k) => findWord(cut, k)?.at ?? -1).filter((t) => t > 0);
  const X = plan as { trip?: [number | string, number | string][]; badge?: { img: string; at: string; until: number | string; cx?: number; cy?: number; r?: number };
    stat?: { title: string; sub: string; in: string; out: string; recall: string; gold: string; many: string; total: string; cols?: number; rows?: number; hits?: number[]; odds?: string; end?: number } };
  const trips = resolve(cut, X.trip);
  const st = X.stat ? { ...X.stat, inAt: wAt(X.stat.in) - 0.1, outAt: wAt(X.stat.out) - 0.15, recall: wAt(X.stat.recall) - 0.1, gold: wAt(X.stat.gold), many: wAt(X.stat.many) - 0.05, total: wAt(X.stat.total) - 0.04, until: X.stat.end ?? D + 1 } : null;
  const badge = X.badge ? { ...X.badge, at: wAt(X.badge.at) - 0.04, until: typeof X.badge.until === "string" ? wAt(X.badge.until) : X.badge.until } : null;
  // full-frame 3D inserts (lux.tsx) — anchored to words like the other graphics
  const luxes: LuxP[] = ((plan as { lux?: (Omit<LuxP, "from" | "to"> & { at: string; until: string | number })[] }).lux ?? [])
    .map((x) => { const from = wAt(x.at) - 0.08; const st = (x as { stepsAt?: string[] }).stepsAt;
      return { ...x, from, to: typeof x.until === "string" ? wAt(x.until) - 0.06 : x.until, ...(st ? { steps: st.map((k) => wAt(k) - from - 0.1) } : {}),
        ...((x as { strikeWord?: string }).strikeWord ? { strikeAt: wAt((x as { strikeWord?: string }).strikeWord!) - from } : {}) }; });
  // glass lists that build on the spoken words (glassList.tsx) — the logos step out while one is up
  const lists: ListP[] = ((plan as { list?: { title?: string; items: { at: string; text: string }[]; until: string | number; y?: number }[] }).list ?? [])
    .map((l) => { const items = l.items.map((it) => ({ ...it, at: wAt(it.at) })); return { ...l, items, from: items[0].at, until: typeof l.until === "string" ? wAt(l.until) : l.until }; });
  const flows: FlowP[] = ((plan as { flow?: { title?: string; nodes: { at: string; label?: string; text: string }[]; until: string | number; bg?: string }[] }).flow ?? [])
    .map((f) => { const nodes = f.nodes.map((n) => ({ ...n, at: wAt(n.at) })); return { ...f, nodes, from: nodes[0].at, until: typeof f.until === "string" ? wAt(f.until) : f.until }; });
  // the After Effects layer (ae.tsx): beats anchored to words; "type" shows the spoken words themselves, after the caption fixes
  const keyOf = (w: Word) => { const same = cut.words.filter((x) => x.text === w.text); return `${w.text}#${same.indexOf(w)}`; };
  const fixW = (w: Word): Word => ({ ...w, text: plan.fix?.[keyOf(w)] ?? plan.fix?.[w.text] ?? w.text });
  const aeT = (k: string | number, d: number) => (typeof k === "string" ? wAt(k) + d : k);
  // a quoted line (דין r4 2.11.2026: «במילים שאני מצטט את אייל תכניס ״ ״»): the marks ride on the first and last word
  const quoted = (x: { quote?: boolean }, ws: Word[]) => !x.quote || !ws.length ? ws
    : ws.map((w, i) => ({ ...w, text: `${i === 0 ? "״" : ""}${w.text}${i === ws.length - 1 ? "״" : ""}` }));
  const ae: AeBeat[] = ((plan as { ae?: (Omit<AeBeat, "from" | "to"> & { at: string | number; until: string | number })[] }).ae ?? []).map((x) => {
    const from = aeT(x.at, -0.08), to = aeT(x.until, -0.06);
    // glass breaks / calendar pages land on spoken words too (round 7)
    const y = x as unknown as { shatter?: string | number; days?: { title: string; text: string; at: string | number }[] };
    const hold = x.k === "type" && to >= cut.duration - 0.2;   // the layer that ends the reel stays until the end card covers it
    return { ...x, from, to: hold ? to + 0.7 : to, ...(hold ? { hold } : {}), ...(x.k === "type" ? { words: quoted(x, cut.words.filter((w) => w.at >= from - 0.02 && w.at < to - 0.05 && (!x.only || w.who === x.only) && !(x.skip ?? []).includes(keyOf(w))).map(fixW)) } : {}),
      ...(y.shatter !== undefined ? { shatter: aeT(y.shatter, -0.05) } : {}),
      ...((x as { again?: string | number }).again !== undefined ? { again: aeT((x as { again: string | number }).again, -0.05) } : {}), ...(y.days ? { days: y.days.map((d) => ({ ...d, at: aeT(d.at, -0.05) })) } : {}),
      ...((x as unknown as { bars?: { at: string | number }[] }).bars ? { bars: (x as unknown as { bars: { at: string | number }[] }).bars.map((d) => ({ ...d, at: aeT(d.at, -0.05) })) } : {}),
      ...((x as unknown as { stops?: { at: string | number }[] }).stops ? { stops: (x as unknown as { stops: { at: string | number }[] }).stops.map((d) => ({ ...d, at: aeT(d.at, -0.05) })) } : {}),
      ...((x as unknown as { items?: { at: string | number; markAt?: string | number }[] }).items ? { items: (x as unknown as { items: { at: string | number; markAt?: string | number }[] }).items.map((d) => ({ ...d, at: aeT(d.at, -0.05), ...(d.markAt !== undefined ? { markAt: aeT(d.markAt, -0.05) } : {}) })) } : {}),
      ...((x as unknown as { steps?: { at: string | number }[] }).steps ? { steps: (x as unknown as { steps: { at: string | number }[] }).steps.map((d) => ({ ...d, at: aeT(d.at, -0.05) })) } : {}) } as AeBeat;
  });
  // a graphic on its neutral backdrop covers the picture: the logos step out and the caption stays at its place
  const boards: [number, number][] = [...lists.filter((l) => l.bg).map((l) => [l.from - 0.3, l.until + 0.3] as [number, number]), ...flows.map((f) => [f.from - 0.3, f.until + 0.3] as [number, number])];
  const statUp: [number, number][] = st ? [[st.inAt - 0.1, st.outAt + 0.3], [st.recall - 0.1, D]] : [];
  const { skip, pills, counter } = graphicsOf(cut, plan);
  // a board with "caps": false is the only text on screen — the captions under it step out (צומת 20 round 4)
  const capsOff: [number, number][] = [...[...lists, ...flows].filter((b) => b.caps === false).map((b) => [b.from - 0.35, b.until] as [number, number]),
    ...ae.filter((b) => b.k === "type" || ((b.k === "checks" || b.k === "brands") && b.caps !== true) || (b.k === "rows" && (b as { caps?: boolean }).caps === false)).map((b) => [b.from - 0.1, b.to] as [number, number])];
  // a card goes only when most of it is under the board — a line that starts as the board leaves keeps its caption
  const cards = cardsOf(cut, plan, skip).filter((c) => !capsOff.some(([a, b]) => Math.min(c.to, b) - Math.max(c.from, a) > 0.5 * (c.to - c.from)));
  // every split on screen — guest/host, third person, the «duo» of two listeners — moves the captions to the seam and hides the
  // logos (אלון+אייל+דולב 27.10.2026: «למה הלוגואים והטקסט רצים על הפנים של האנשים?» — the duo splits were not counted)
  const splits = shots.filter((s) => s.kind === "split").map((s) => [s.at, s.end] as [number, number]);
  const inSplit = (t: number) => splits.some(([a, b]) => t >= a - 0.01 && t < b) || inShrink(t, ae);
  const lifted = (t: number) => statUp.some(([a, b]) => t >= a && t < b);
  // capFixed: one caption line for the whole reel — splits put their seam on it, cards and logos live under it (אורח B 29.10)
  const capY = (t: number) => (L.capFixed ? (L.capY ?? 1290) : inSplit(t) ? (L.capYSplit ?? 960) : lifted(t) ? 1100 : (L.capY ?? 1290));
  const logoHide: [number, number][] = [...splits, ...ae.filter((b) => b.k !== "leak").map((b) => [b.from, b.to] as [number, number]), ...boards, ...statUp, ...luxes.map((x) => [x.from, x.to] as [number, number]), ...(counter ? [[counter.at, counter.until] as [number, number]] : [])];
  // clicks: on a real camera change, never into a shot shorter than 1 s, ≥ 2 s apart, not on reactions (tsomet rules)
  const clicks: number[] = [];
  if (L.clicks !== false) shots.forEach((s, i) => {
    const p = shots[i - 1];
    if (!p || s.end - s.at < 1.0 || s.kind === "react" || p.kind === "react") return;
    const change = p.cam !== s.cam || p.kind !== s.kind || (s.jump && Math.abs(p.z - s.z) > 0.01);
    if (change && (!clicks.length || s.at - clicks[clicks.length - 1] >= 2.0)) clicks.push(s.at);
  });
  return (
    <LookCtx.Provider value={plan.logo ? { ...L, logoFile: plan.logo } as Look : L}>
    <Ctx.Provider value={{ sel: selOf(data.sel), face: data.face }}>
    <AbsoluteFill style={{ background: "#000" }}>
      {ae.filter((b) => b.k === "shrink").map((b, i) => <AeShrinkStage key={`as${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      <CamWrap beats={ae}>
      {shots.map((s, i) => (
        <Sequence key={i} from={Math.round(s.at * fps)} durationInFrames={Math.max(1, Math.round(s.end * fps) - Math.round(s.at * fps) + (i === shots.length - 1 ? Math.round(OUT * fps) : 1) + (isMix(shots[i + 1]?.at) ? MIX_F : 0))}>
          <MixIn on={isMix(s.at)}>
          {s.kind === "split" ? <Split src={s.src} u0={0} top={s.top ?? (s.cam === 3 ? 3 : 2)} bottom={s.bottom ?? 1} shift={s.shift ?? 0} seam={L.splitSeam} />
            : trips.some(([a, b]) => s.at < b + 0.3 && s.end > a - 0.3) ? <Trip t0={s.at} rs={trips}><Cam cam={s.cam} src={s.src} z={zoomFn(s, push, i === 0, close, soft, punch)} track={follow?.[String(s.cam)]} /></Trip>
            : <Cam cam={s.cam} src={s.src} z={zoomFn(s, push, i === 0, close, soft, punch)} track={follow?.[String(s.cam)]} />}
          {behinds.filter((b) => s.kind === "main" && s.at < b.to && s.end > b.from).map((b, k) => {
            // the cut-out lies over the camera only inside the graphic's window, from its own frame of the source
            // (a matte clamped to frame 0 ran 0.3–1.8 s off the speaker — «השכבה השניה נשברת», 27.10)
            const u0 = Math.max(0, b.from - s.at), u1 = Math.min(s.end, b.to) - s.at, z = zoomFn(s, push, i === 0, close, soft, punch);
            return <React.Fragment key={`bh${k}`}>
              <Sequence from={-Math.round(s.at * fps)}><Behind {...b} files={wbFiles} /></Sequence>
              <Sequence from={Math.round(u0 * fps)} durationInFrames={Math.max(1, Math.round((u1 - u0) * fps))}>
                <Cam cam={s.cam} src={s.src + u0} z={(u) => z(u + u0)} matte={{ file: b.file, src0: b.src0 }} track={follow?.[String(s.cam)]} />
              </Sequence>
            </React.Fragment>; })}
          </MixIn>
        </Sequence>
      ))}
      </CamWrap>
      {ae.filter((b) => b.k === "shrink").map((b, i) => <AeShrinkFrame key={`af${i}`} b={b} />)}
      {ae.filter((b) => b.k === "clip").map((b, i) => <AeClip key={`ac${i}`} b={b} />)}
      {ae.filter((b) => b.k === "card").map((b, i) => <AeCard key={`ak${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "type").map((b, i) => <AeType key={`at${i}`} b={b} font={L.font ? "ReelLook" : FONT} who={L.colors ?? WHO_COLOR} />)}
      {ae.filter((b) => b.k === "glass").map((b, i) => <AeGlass key={`ag${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "num").map((b, i) => <AeNum key={`an${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "cal").map((b, i) => <AeCal key={`ac${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "rain").map((b, i) => <AeRain key={`ar${i}`} b={b} />)}
      {ae.filter((b) => b.k === "map").map((b, i) => <AeMap key={`am${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "msgs").map((b, i) => <AeMsgs key={`ams${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "drain").map((b, i) => <AeDrain key={`ad${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "scale").map((b, i) => <AeScale key={`as${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "profile").map((b, i) => <AeProfile key={`ap${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "rows").map((b, i) => <AeRows key={`aro${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "meter").map((b, i) => <AeMeter key={`ame${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "world").map((b, i) => <AeWorld key={`aw${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "border").map((b, i) => <AeBorder key={`abd${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "gap").map((b, i) => <AeGap key={`agp${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "year").map((b, i) => <AeYear key={`ay${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "icon").map((b, i) => <AeIcon key={`ai${i}`} b={b} />)}
      {ae.filter((b) => b.k === "logo").map((b, i) => <AeLogo key={`alg${i}`} b={b} />)}
      {ae.filter((b) => b.k === "checks").map((b, i) => <AeChecks key={`ach${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "brands").map((b, i) => <AeBrands key={`abr${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "dm").map((b, i) => <AeDm key={`adm${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "anger").map((b, i) => <AeAnger key={`aan${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "site").map((b, i) => <AeSite key={`ase${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "notes").map((b, i) => <AeNotes key={`ano${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {ae.filter((b) => b.k === "marks").map((b, i) => <AeMarks key={`aq${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      {aeLeaks(ae).map((a, i) => <Leak key={`lk${i}`} at={a} seed={i} />)}
      {aeSfx(ae).map((x, i) => <Sfx key={`ax${i}`} {...x} />)}
      {luxes.map((x, i) => <React.Fragment key={`lx${i}`}><Lux {...x} /><Sfx at={x.from - 0.1} file="whoosh1.wav" vol={0.4} /></React.Fragment>)}
      {ae.filter((b) => b.k === "glow").map((b, i) => <AeGlow key={`aw${i}`} b={b} />)}
      {(plan.broll ?? []).map((b, i, all) => {
        // back-to-back B-roll is a straight cut, one swoosh for the run — not a dip to black between each («מעברים לא נקיים», 27.10)
        // "hard": a straight cut in and out — no fade over the picture (צומת 20 round 3: «מעברים לא נקיים עם הבירולים»)
        const hard = (b as { hard?: boolean }).hard ?? (L as { brollHard?: boolean }).brollHard;
        const cutIn = hard || all.some((x) => Math.abs(x.to - b.from) < 0.05), cutOut = hard || all.some((x) => Math.abs(x.from - b.to) < 0.05);
        return <React.Fragment key={`b${i}`}><BRoll {...b} cutIn={cutIn} cutOut={cutOut} />{!cutIn && <Sfx at={b.from - 0.05} file="swoosh-quick.wav" vol={0.22} />}</React.Fragment>; })}
      {behinds.filter((b) => b.kind === "screens").flatMap((b) => (b.srcs ?? []).slice(0, 6).map((_, k) => {
        const every = Math.min(0.6, (b.to - b.from - 0.8) / Math.max(1, (b.srcs ?? []).length));
        return <Sfx key={`ss${b.from}${k}`} at={b.from + k * every - 0.05} file="swoosh-quick.wav" vol={0.3} />; }))}
      {behinds.filter((b) => b.kind === "code").map((b) => <Sfx key={`cs${b.from}`} at={b.from} file="typing.wav" vol={0.35} />)}
      {((plan as { sfx?: { at: number; file: string; vol?: number }[] }).sfx ?? []).map((x, i) => <Sfx key={`x${i}`} at={x.at} file={x.file} vol={x.vol ?? 0.5} />)}
      {(plan.flash ?? []).map((f, i) => { const fs = (plan as { flashSfx?: { file: string; vol: number } }).flashSfx;
        return <React.Fragment key={`f${i}`}><Flash at={f} />{fs ? <Sfx at={f - 0.02} file={fs.file} vol={fs.vol} /> : <Sfx at={f - 0.15} file="whoosh1.wav" vol={0.4} />}</React.Fragment>; })}
      {st && <><Stat {...st} /><Sfx at={st.inAt - 0.05} file="whoosh1.wav" vol={0.35} /><Sfx at={st.recall - 0.05} file="whoosh1.wav" vol={0.35} />
        <Sfx at={st.gold - 0.03} file="text-appear.wav" vol={0.4} /><Sfx at={st.many} file="swoosh-quick.wav" vol={0.3} /></>}
      {badge && <><Badge {...badge} /><Sfx at={badge.at} file="swoosh-quick.wav" vol={0.35} /></>}
      {flows.map((f, i) => <React.Fragment key={`fl${i}`}>{f.theme === "grid" && f.grid ? <GridFlow {...f} grid={f.grid} font={L.font ? "ReelLook" : FONT} /> : <Flow {...f} font={L.font ? "ReelLook" : FONT} />}
        <Sfx at={f.from - 0.3} file="whoosh1.wav" vol={0.3} />{f.nodes.map((n, k) => <Sfx key={k} at={n.at - 0.1} file="swoosh-quick.wav" vol={0.28} />)}</React.Fragment>)}
      {lists.map((l, i) => BOARD_THEMES.includes(l.theme ?? "")
        ? <React.Fragment key={`gl${i}`}><Board {...(l as BoardP)} font={L.font ? "ReelLook" : FONT} />
          {boardSfx(l as BoardP).map((x, k) => <Sfx key={k} at={x.at} file={x.file} vol={x.vol} />)}</React.Fragment>
        : <React.Fragment key={`gl${i}`}><GlassList {...l} font={L.font ? "ReelLook" : FONT} />
          {l.items.map((it, k) => <Sfx key={k} at={it.at - 0.1} file="swoosh-quick.wav" vol={0.28} />)}</React.Fragment>)}
      {trips.map(([a], i) => <Sfx key={`tr${i}`} at={a - 0.3} file="swoosh-low.wav" vol={0.35} />)}
      <Captions cards={cards} yAt={capY} />
      <Logo hide={logoHide} y={L.logoY ?? 1475} />
      {pills.map((p, i) => <React.Fragment key={i}><Pill {...p} /><Sfx at={p.at} file="swoosh-quick.wav" vol={0.35} /></React.Fragment>)}
      {counter && <><Counter {...counter} /><Sfx at={counter.at} file="text-appear.wav" vol={0.35} /></>}
      {ae.filter((b) => b.k === "arrow").map((b, i) => <AeArrow key={`aar${i}`} b={b} font={L.font ? "ReelLook" : FONT} />)}
      <Outro at={D + 0.05} />
      {glass && <><Glass {...glass} />{glass.items.map((g, i) => <Sfx key={`gs${i}`} at={g.at - 0.12} file="whoosh1.wav" vol={0.5} />)}
        <Sfx at={glass.recall - 0.12} file="whoosh1.wav" vol={0.5} />
        <Sfx at={glass.shatter - 0.04} file="glass-break.mp3" vol={0.9} /></>}
      {ae.length > 0 && <Grain />}
      {L.review && <Stamp n={(plan as { num?: number }).num} />}
      {/* sound */}
      {L.intro !== false && <Sfx at={0} file="shutter.wav" vol={L.clicks === false ? 0.5 : 0.8} />}
      {clicks.map((t, i) => <Sfx key={i} at={t} file="click.wav" vol={0.5} />)}
      {(L as { outroSfx?: boolean }).outroSfx !== false && <Sfx at={D - 0.1} file="woosh2.wav" vol={0.7} />}   {/* after the last word, not over it (דין r8 2.11: «המילה תיכשל נחתכת») */}
      {L.audio && <Audio src={staticFile(`a/${id}.wav`)} />}
      {!L.audio && cut.clips.map((c, i) => (
        <Sequence key={`a${i}`} from={Math.round(c.at * fps)} durationInFrames={Math.max(1, Math.round(c.end * fps) - Math.round(c.at * fps))}>
          <Audio src={staticFile("dialogue.m4a")} startFrom={Math.round(c.src * fps)}
            volume={(f) => interpolate(f, [0, 1, (c.end - c.at) * fps - 1, (c.end - c.at) * fps], [0.2, 1, 1, 0.2], clamp)} />
        </Sequence>
      ))}
      {pm && <Audio src={staticFile(pm.file)} startFrom={Math.round((pm.from ?? 0) * fps)} volume={(f) => {
        const t = f / fps;
        // the drop: out in 0.12 s on the word («צרצרים.»), back in 0.25 s when the action returns
        const drop = Math.max(0, ...(pm.drops ?? []).map(([a, b]) => Math.min(ramp(t, a - 0.12, 0.12), 1 - ramp(t, b, 0.25))));
        return pm.vol * interpolate(t, [0, 0.4, D, D + OUT], [0, 1, 1, 0.0], clamp) * (1 - drop);
      }} />}
      {((plan as { beds?: Bed[] }).beds ?? []).map((b, i) => {
        const until = b.until ?? D + OUT, len = until - b.at;
        return <Sequence key={`bd${i}`} from={Math.round(b.at * fps)} durationInFrames={Math.max(1, Math.round(len * fps))}>
          <Audio src={staticFile(b.file)} startFrom={Math.round((b.from ?? 0) * fps)} volume={(f) => {
            const u = f / fps, t = b.at + u;
            const drop = Math.max(0, ...(b.drops ?? []).map(([a, c]) => Math.min(ramp(t, a - 0.08, 0.08), 1 - ramp(t, c, 0.3, inOut))));
            const v = b.rise ? b.vol + (b.rise.vol - b.vol) * ramp(t, b.rise.at, b.rise.dur, inOut) : b.vol;
            return v * (1 - drop) * Math.min(ramp(u, 0, Math.max(0.01, b.fin ?? 0.3), inOut), 1 - ramp(u, len - Math.max(0.01, b.fout ?? 0.3), Math.max(0.01, b.fout ?? 0.3), inOut));
          }} /></Sequence>; })}
      {withMusic && pm0 !== false && !pm && <Audio src={staticFile("music.mp3")} volume={(f) => 0.085 * interpolate(f / fps, [0, 0.6, D, D + OUT], [0, 1, 1, 0.0], clamp)} />}
    </AbsoluteFill>
    </Ctx.Provider>
    </LookCtx.Provider>
  );
};
