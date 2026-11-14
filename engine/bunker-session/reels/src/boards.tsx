// צומת 20 extra reels, round 5 (29.10.2026). Alon on the Guest J lists, all four on רקע חללי as star → glass pill:
// «הבי רול שהכנסת חופר - תגוון קצת. גם בבי רול וגם באנימציה של הדוגמאות, לא הכל חייב להיות כזה זכוכית באותה צורה.
// אתה יכול למשל להכניס השוואה בין עצמאי לשכיר (יכול להיות קצת קומי, כמו קריקטורות משעשעות)».
// So every board gets its own backdrop from «מעברים ורקעים» AND its own way of building — never the same glass shape twice:
//   "paper"  — paper cards taped on, a red rubber stamp slams on each («ארוסתי» + stamp «שכירה»)       bg/paper.mp4
//   "vs"     — two caricatures face off on the blue/red neon, rows of «שכיר ↔ עצמאי» values slam in     bg/vs.mp4
//   "report" — a handwritten report card, each grade written in red marker and circled                  bg/report.mp4
//   "topo"   — pins drop on a contour map with a dashed flight path, a struck-out chip for the last item  bg/topo.mp4
// plans.json "list" entries take the theme plus, per theme: items[].stamp (paper), items[].a / .b + sides + art (vs),
// items[].grade (report). The hand face is public/Hand.ttf (Amatic SC — has Hebrew), loaded by Reel.tsx when a board asks.
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, inOut, ramp } from "./look";

export type BoardItem = { at: number; text: string; stamp?: string; a?: string; b?: string; grade?: string };
export type BoardP = { title?: string; items: BoardItem[]; from: number; until: number; bg?: string; theme?: string;
  sides?: [string, string]; art?: [string, string]; caps?: boolean };
export const BOARD_THEMES = ["paper", "vs", "report", "topo"];
export const HAND = "Hand";
const back = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
const LEAD = 0.35;

/** the backdrop as it was shot — sharp, full frame, a cut-in fade; push only where the texture allows it */
const Bg: React.FC<{ file: string; from: number; until: number; t: number; push?: number; filter?: string }> = ({ file, from, until, t, push = 0, filter }) => {
  const { fps } = useVideoConfig();
  const k = Math.min(ramp(t, from - LEAD, 0.25, inOut), 1 - ramp(t, until - 0.25, 0.25, inOut));
  return (
    <AbsoluteFill style={{ opacity: k, background: "#000" }}>
      <Sequence from={Math.round((from - LEAD) * fps)} layout="none">
        <OffthreadVideo src={staticFile(file)} muted style={{ position: "absolute", inset: 0, width: 1080, height: 1920, objectFit: "cover", filter,
          transform: `scale(${1 + push * ((t - from) / Math.max(0.5, until - from))})` }} />
      </Sequence>
    </AbsoluteFill>
  );
};
const fadeOut = (t: number, until: number) => 1 - ramp(t, until - 0.3, 0.3, inOut);

/** «מי סביבו» — paper cards taped to the paper, a stamp slams on each half a second after its word */
const PaperBoard: React.FC<BoardP & { font: string }> = ({ title, items, from, until, bg, font }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const n = items.length, y0 = title ? 560 : 470, gap = Math.min(330, 900 / Math.max(1, n));
  const tp = ramp(t, from - 0.3, 0.55, inOut);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Bg file={bg!} from={from} until={until} t={t} filter="brightness(1.02) contrast(1.05)" />
      <AbsoluteFill style={{ opacity: fadeOut(t, until), direction: "rtl" }}>
        {title && <div style={{ position: "absolute", top: y0 - 270, left: 0, right: 0, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 150,
          color: "#1f2340", clipPath: `inset(0 0 0 ${100 * (1 - tp)}%)` }}>{title}</div>}
        {items.map((it, i) => {
          const p = ramp(t, it.at - 0.18, 0.42), s = ramp(t, it.at + 0.32, 0.16, (x) => x);
          if (p <= 0) return null;
          const side = i % 2 ? -1 : 1, rot = side * (3 + i), y = y0 + i * gap;
          const hit = s > 0 && s < 1 ? 0 : s >= 1 ? Math.max(0, 1 - (t - it.at - 0.48) / 0.18) : 0;   // the card jolts as the stamp lands
          return (
            <div key={i} style={{ position: "absolute", left: 540 - 330 + side * 55, top: y, width: 660, height: 230,
              transform: `translateY(${(1 - back(Math.min(1, p))) * 160 + hit * 10}px) rotate(${rot * (0.4 + 0.6 * p)}deg)`, opacity: Math.min(1, p * 2) }}>
              <div style={{ position: "absolute", inset: 0, background: "#fbf8f1", boxShadow: "0 18px 34px rgba(40,30,10,0.28), 0 2px 0 rgba(0,0,0,0.05)",
                borderRadius: 6 }} />
              <div style={{ position: "absolute", top: -26, left: 250, width: 160, height: 52, background: "rgba(232,214,160,0.75)", transform: "rotate(-3deg)",
                boxShadow: "0 2px 4px rgba(0,0,0,0.12)" }} />
              <div style={{ position: "absolute", top: 34, right: 52, fontFamily: HAND, fontWeight: 700, fontSize: 132, lineHeight: 1, color: "#1f2340" }}>{it.text}</div>
              {it.stamp && s > 0 && (
                <div style={{ position: "absolute", left: 36, top: 52, padding: "6px 26px 2px", border: "8px solid #c8102e", borderRadius: 14, color: "#c8102e",
                  fontFamily: font, fontWeight: 900, fontSize: 70, lineHeight: 1.15, transform: `rotate(-12deg) scale(${2.3 - 1.3 * s})`, opacity: 0.88 * s,
                  mixBlendMode: "multiply", letterSpacing: "0.02em" }}>{it.stamp}</div>
              )}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** «שכיר ↔ עצמאי» — the two caricatures face off, each row of values slams in from its own side on its word */
const VsBoard: React.FC<BoardP & { font: string }> = ({ items, from, until, bg, font, sides = ["שכיר", "עצמאי"], art }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const open = ramp(t, from - 0.35, 0.5);
  const last = items[items.length - 1].at;
  const panic = 1 + 2.5 * ramp(t, last - 0.1, 0.3);                     // the freelancer shakes harder when the risk lands
  const jx = Math.sin(t * 47) * 3 * panic, jy = Math.cos(t * 39) * 2 * panic;
  const sway = Math.sin(t * 2.2) * 2;
  const vs = ramp(t, from - 0.1, 0.35);
  const R = "#FF4A5A", BL = "#47B8FF";
  const head = (txt: string, c: string, x: number) => (
    <div style={{ position: "absolute", top: 196, left: x - 230, width: 460, textAlign: "center", fontFamily: font, fontWeight: 900, fontSize: 88, color: "#fff",
      textShadow: `0 0 26px ${c}, 0 0 8px ${c}, 0 4px 10px rgba(0,0,0,0.6)`, opacity: open }}>{txt}</div>
  );
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Bg file={bg!} from={from} until={until} t={t} filter="brightness(0.8)" />
      <AbsoluteFill style={{ opacity: fadeOut(t, until), direction: "rtl" }}>
        {head(sides[0], BL, 790)}{head(sides[1], R, 290)}
        {art && <>
          <Img src={staticFile(art[0])} style={{ position: "absolute", top: 330, left: 790 - 230, width: 460, transformOrigin: "50% 100%",
            transform: `translateX(${(1 - open) * 420}px) rotate(${sway}deg)`, filter: `drop-shadow(0 0 22px ${BL}88)` }} />
          <Img src={staticFile(art[1])} style={{ position: "absolute", top: 320, left: 290 - 240, width: 480,
            transform: `translateX(${-(1 - open) * 420 + jx}px) translateY(${jy}px)`, filter: `drop-shadow(0 0 22px ${R}88)` }} />
        </>}
        <div style={{ position: "absolute", top: 560, left: 540 - 95, width: 190, height: 190, borderRadius: 999, display: "flex", alignItems: "center",
          justifyContent: "center", fontFamily: font, fontWeight: 900, fontSize: 92, color: "#FFD54A", background: "rgba(10,10,20,0.75)",
          border: "6px solid #FFD54A", boxShadow: "0 0 34px rgba(255,213,74,0.7)", transform: `scale(${back(Math.min(1, vs))}) rotate(${(1 - vs) * -40}deg)`,
          opacity: Math.min(1, vs * 2), direction: "ltr" }}>VS</div>
        {items.map((it, i) => {
          const p = ramp(t, it.at - 0.12, 0.34);
          if (p <= 0) return null;
          const y = 1080 + i * 205, q = back(Math.min(1, p));
          const pill = (txt: string, c: string, x: number, dir: number, up: boolean) => (
            <div style={{ position: "absolute", top: y + 62, left: x - 175, width: 350, height: 112, borderRadius: 22, display: "flex", alignItems: "center",
              justifyContent: "center", gap: 18, fontFamily: font, fontWeight: 900, fontSize: 64, color: "#fff", background: `${c}D9`,
              border: "3px solid rgba(255,255,255,0.7)", boxShadow: `0 0 30px ${c}AA`, transform: `translateX(${dir * (1 - q) * 380}px) skewX(${dir * (1 - Math.min(1, p)) * 14}deg)` }}>
              <span>{txt}</span>
              <svg width={40} height={46} viewBox="0 0 40 46" style={{ transform: up ? "none" : "rotate(180deg)" }}><path d="M20 2 L38 26 H27 V44 H13 V26 H2 Z" fill="#fff" /></svg>
            </div>
          );
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", top: y, left: 0, right: 0, textAlign: "center", fontFamily: font, fontWeight: 800, fontSize: 46, color: "#FFD54A",
                opacity: Math.min(1, p * 2), textShadow: "0 2px 8px rgba(0,0,0,0.8)" }}>{it.text}</div>
              {it.a && pill(it.a, BL, 790, 1, /גבוה|יותר/.test(it.a))}
              {it.b && pill(it.b, R, 290, -1, /גבוה|יותר/.test(it.b))}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** «5 יחידות» — a report card: the subject written in, the grade in red marker, a circle drawn round it */
const ReportBoard: React.FC<BoardP & { font: string }> = ({ title, items, from, until, bg, font }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const tp = ramp(t, from - 0.3, 0.5, inOut), line = ramp(t, from - 0.05, 0.45, inOut);
  const n = items.length, y0 = 560, gap = Math.min(190, 950 / Math.max(1, n));
  const ink = "#1d2a6b", red = "#cf1020";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Bg file={bg!} from={from} until={until} t={t} push={0.04} filter="brightness(1.03)" />
      <AbsoluteFill style={{ opacity: fadeOut(t, until), direction: "rtl" }}>
        {title && <div style={{ position: "absolute", top: 290, left: 0, right: 0, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 160,
          color: ink, clipPath: `inset(0 0 0 ${100 * (1 - tp)}%)` }}>{title}</div>}
        <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
          <path d="M 860 490 C 700 504, 420 482, 220 498" fill="none" stroke={ink} strokeWidth={6} strokeLinecap="round" pathLength={1}
            strokeDasharray="1 1" strokeDashoffset={1 - line} />
          {items.map((it, i) => {
            const y = y0 + i * gap, c = ramp(t, it.at + 0.12, 0.38, inOut);
            return <React.Fragment key={i}>
              {ramp(t, it.at - 0.15, 0.3) > 0 && <line x1={880} y1={y + 128} x2={130} y2={y + 128} stroke="rgba(29,42,107,0.18)" strokeWidth={3} />}
              {c > 0 && <ellipse cx={195} cy={y + 70} rx={78} ry={66} fill="none" stroke={red} strokeWidth={7} strokeLinecap="round" pathLength={1}
                strokeDasharray="1 1" strokeDashoffset={1 - c} transform={`rotate(-14 195 ${y + 70})`} />}
            </React.Fragment>;
          })}
        </svg>
        {items.map((it, i) => {
          const y = y0 + i * gap, w = ramp(t, it.at - 0.15, 0.32, inOut), g = ramp(t, it.at - 0.02, 0.2, inOut);
          if (w <= 0) return null;
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", top: y, right: 200, fontFamily: HAND, fontWeight: 700, fontSize: Math.min(120, 1500 / it.text.length), lineHeight: 1.1, color: ink, whiteSpace: "nowrap",
                clipPath: `inset(0 0 0 ${100 * (1 - w)}%)` }}>{it.text}</div>
              <div style={{ position: "absolute", top: y - 6, left: 112, width: 170, textAlign: "center", fontFamily: FONT, fontWeight: 900, fontSize: 92, lineHeight: 1, paddingTop: 26, whiteSpace: "nowrap",
                color: red, clipPath: `inset(0 0 ${100 * (1 - g)}% 0)`, transform: "rotate(-6deg)" }}>{it.grade ?? "5"}</div>
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** «אפליקציה לקסם» — the title over a contour map, pins drop for the places, the last item a struck-out chip */
const TopoBoard: React.FC<BoardP & { font: string }> = ({ title, items, from, until, bg, font }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const gold = "#FFD54A";
  const pins = items.slice(0, -1), chip = items[items.length - 1];
  const P = [{ x: 720, y: 760 }, { x: 330, y: 1010 }, { x: 700, y: 1180 }];
  const tp = ramp(t, from - 0.3, 0.45, inOut);
  const path = pins.length > 1 ? ramp(t, pins[1].at - 0.45, 0.45, inOut) : 0;
  const a = P[0], b = P[1];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Bg file={bg!} from={from} until={until} t={t} push={0.06} filter="brightness(0.85)" />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(255,213,74,0.10) 0%, rgba(0,0,0,0) 60%)", opacity: fadeOut(t, until) }} />
      <AbsoluteFill style={{ opacity: fadeOut(t, until), direction: "rtl", fontFamily: font }}>
        {title && <div style={{ position: "absolute", top: 380, left: 0, right: 0, textAlign: "center", fontSize: 84, fontWeight: 900, color: "#fff",
          transform: `translateY(${(1 - tp) * 30}px)`, opacity: tp, textShadow: "0 0 24px rgba(255,213,74,0.45), 0 4px 12px rgba(0,0,0,0.7)" }}>{title}</div>}
        <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
          {path > 0 && <path d={`M ${a.x} ${a.y} Q ${(a.x + b.x) / 2} ${Math.min(a.y, b.y) - 260} ${b.x} ${b.y}`} fill="none" stroke={gold} strokeWidth={5}
            strokeDasharray="14 16" strokeLinecap="round" opacity={0.85} strokeDashoffset={-t * 60}
            style={{ clipPath: `inset(0 ${100 * (1 - path)}% 0 0)` }} />}
          {pins.map((it, i) => {
            const { x, y } = P[i % P.length], land = it.at - 0.05;
            const d = ramp(t, land - 0.3, 0.3, (q) => q * q), r = ramp(t, land, 0.7, (q) => q);
            if (d <= 0) return null;
            const yy = y - (1 - d) * 380, sq = d >= 1 ? 1 - 0.18 * Math.max(0, 1 - (t - land) / 0.15) : 1;
            return <g key={i}>
              {r > 0 && r < 1 && <circle cx={x} cy={y} r={20 + 110 * r} fill="none" stroke={gold} strokeWidth={4} opacity={1 - r} />}
              <ellipse cx={x} cy={y} rx={26} ry={9} fill="rgba(0,0,0,0.5)" opacity={d} />
              <g transform={`translate(${x} ${yy}) scale(1 ${sq})`}>
                <path d="M 0 0 C -10 -26, -40 -50, -40 -82 A 40 40 0 1 1 40 -82 C 40 -50, 10 -26, 0 0 Z" fill={gold} stroke="#1a1206" strokeWidth={4} />
                <circle cx={0} cy={-84} r={15} fill="#1a1206" />
              </g>
            </g>;
          })}
        </svg>
        {pins.map((it, i) => {
          const { x, y } = P[i % P.length], p = ramp(t, it.at + 0.05, 0.3);
          if (p <= 0) return null;
          const right = x > 540;
          return <div key={i} style={{ position: "absolute", top: y - 150, ...(right ? { right: 1080 - x + 62 } : { left: x + 62 }), padding: "12px 30px 16px",
            borderRadius: 16, background: "rgba(12,12,16,0.85)", border: `3px solid ${gold}`, fontSize: 72, fontWeight: 900, color: "#fff", whiteSpace: "nowrap",
            opacity: p, transform: `translateX(${(right ? 1 : -1) * (1 - p) * 40}px)` }}>{it.text}</div>;
        })}
        {chip && (() => {
          const p = ramp(t, chip.at - 0.15, 0.3), s = ramp(t, chip.at + 0.75, 0.25, inOut);   // the strike on «AI», ~0.8 s after «לפני»
          if (p <= 0) return null;
          const [pre, word] = chip.text.split(/\s+(?=\S+$)/);
          return <div style={{ position: "absolute", top: 1330, left: 0, right: 0, display: "flex", justifyContent: "center", alignItems: "center", gap: 26,
            opacity: p, transform: `scale(${0.8 + 0.2 * back(Math.min(1, p))})` }}>
            <span style={{ fontSize: 78, fontWeight: 900, color: "#fff", textShadow: "0 4px 12px rgba(0,0,0,0.7)" }}>{pre}</span>
            <span style={{ position: "relative", fontSize: 92, fontWeight: 900, color: gold, padding: "4px 30px 10px", border: `5px solid ${gold}`, borderRadius: 18,
              direction: "ltr" }}>{word}
              <span style={{ position: "absolute", left: -14, right: -14, top: "50%", height: 9, background: "#FF4A5A", borderRadius: 9,
                transform: `rotate(-14deg) scaleX(${s})`, transformOrigin: "left center", boxShadow: "0 0 14px rgba(255,74,90,0.8)" }} />
            </span>
          </div>;
        })()}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Board: React.FC<BoardP & { font: string }> = (props) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < props.from - 0.45 || t > props.until + 0.1) return null;
  if (props.theme === "paper") return <PaperBoard {...props} />;
  if (props.theme === "vs") return <VsBoard {...props} />;
  if (props.theme === "report") return <ReportBoard {...props} />;
  return <TopoBoard {...props} />;
};

/** each board's own sound — paper slides and a stamp thud, marker strokes, swooshes for the slams and the pins */
export const boardSfx = (b: BoardP): { at: number; file: string; vol: number }[] => {
  const s: { at: number; file: string; vol: number }[] = [{ at: b.from - 0.35, file: "whoosh1.wav", vol: 0.3 }];
  for (const it of b.items) {
    if (b.theme === "paper") { s.push({ at: it.at - 0.18, file: "paper.wav", vol: 0.5 }); if (it.stamp) s.push({ at: it.at + 0.44, file: "stamp.wav", vol: 0.45 }); }
    else if (b.theme === "report") s.push({ at: it.at - 0.05, file: "marker.wav", vol: 0.45 });
    else s.push({ at: it.at - 0.12, file: "swoosh-quick.wav", vol: 0.3 });
  }
  return s;
};
