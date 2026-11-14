// צומת 20 extra reels (28.10.2026). Round 2 (Alon: «motion graphics להמחשה של מה שנאמר … כל 2-3 שניות צריך לקרות משהו»):
// a short list that builds on the spoken words — one glass row per item, landing on its word. Round 3 («מה זה האנימציות
// האלה? … תכניס את האנימציות זכוכית על רקע בירול נטרלי, אבל שלא יהיה על הראש של האנשים»): with `bg` the list sits
// centred on a full-frame neutral B-roll (blurred, dimmed) instead of over the speaker. The voice runs on under it and the
// caption keeps every spoken word. plans.json:
//   "list": [{ "title"?, "items": [{ "at": "word#n", "text" }], "until": "word#n" | s, "y"?, "wrap"?, "bg"?: "bg/neutral.mp4" }]
//   "flow": [{ "title"?, "nodes": [{ "at": "word#n", "label", "text" }], "until", "bg" }] — a chain of glass nodes, each one
//   drawn to by a dashed arrow from the one before («חצים מקווקים מודרניים שיוצרים את הנקודה הבאה בכל פעם»).
import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { inOut, ramp } from "./look";

// round 4: "theme" picks a backdrop treatment from the folder «מעברים ורקעים» ("space" → SpaceList here, "grid" → gridFlow.tsx);
// "caps": false hides the captions while the board is up («אל תשים במקביל את האנימציה עם הכיתוב ואת הכתוביות»)
export type ListP = { title?: string; items: { at: number; text: string }[]; from: number; until: number; y?: number; wrap?: boolean; bg?: string; theme?: string; caps?: boolean };
export type FlowP = { title?: string; nodes: { at: number; label?: string; text: string }[]; from: number; until: number; bg?: string; theme?: "grid";
  grid?: { x: number; v: number; pitch: number; y: number }; caps?: boolean };
const back = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
const glass: React.CSSProperties = {
  background: "linear-gradient(135deg, rgba(255,255,255,0.20), rgba(255,255,255,0.06))", border: "1.5px solid rgba(255,255,255,0.35)",
  boxShadow: "0 14px 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.4)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)",
};

/** the neutral B-roll behind a graphic: full frame, blurred and dimmed, a slow push; in/out over 0.25 s */
const Backdrop: React.FC<{ file: string; from: number; until: number; t: number }> = ({ file, from, until, t }) => {
  const { fps } = useVideoConfig();
  const k = Math.min(ramp(t, from - 0.25, 0.25, inOut), 1 - ramp(t, until, 0.25, inOut));
  return (
    <AbsoluteFill style={{ opacity: k, background: "#0c1412" }}>
      <Sequence from={Math.round((from - 0.25) * fps)} layout="none">
        <OffthreadVideo src={staticFile(file)} muted style={{ position: "absolute", inset: -80, width: 1240, height: 2080, objectFit: "cover",
          filter: "blur(16px) brightness(0.95) saturate(0.85)", transform: `scale(${1.04 + 0.03 * ((t - from) / Math.max(0.5, until - from))})` }} />
      </Sequence>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.35) 100%)" }} />
    </AbsoluteFill>
  );
};

/** round 4 (28.10.2026, «רקע חללי … להתאים את האנימציה לסגנון בצורה יצירתית ואלגנטית»): the list on the space backdrop
 * becomes a constellation — each item flares in as a star on its word and opens into a glass pill, a thin line joins it to
 * the one before, the items zig-zag down the frame. Above the caption band (≤ 1080) so the two never meet. */
const SpaceList: React.FC<ListP & { font: string }> = ({ title, items, from, until, font, bg }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  // gone as the board's last word ends — the next line's caption comes straight back (and may sit at the split seam)
  const out = ramp(t, until - 0.3, 0.3, inOut);
  const k = Math.min(ramp(t, from - 0.35, 0.3, inOut), 1 - ramp(t, until - 0.3, 0.3, inOut));
  const n = items.length, gap = n > 1 ? Math.min(180, 590 / (n - 1)) : 0, y0 = title ? 500 : 430;
  const at = (i: number) => ({ x: 540 + (n > 1 ? (i % 2 ? -1 : 1) * 115 : 0), y: y0 + i * gap });
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ opacity: k, background: "#000" }}>
        <Sequence from={Math.round((from - 0.35) * fps)} layout="none">
          <OffthreadVideo src={staticFile(bg!)} muted style={{ position: "absolute", inset: 0, width: 1080, height: 1920, objectFit: "cover",
            transform: `scale(${1.0 + 0.08 * ((t - from) / Math.max(0.5, until - from))})` }} />
        </Sequence>
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(40,60,120,0.18) 0%, rgba(0,0,0,0) 55%)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - out, direction: "rtl", fontFamily: font }}>
        {title && (() => {
          const p = ramp(t, from - 0.3, 0.6, inOut);
          return <div style={{ position: "absolute", top: y0 - 190, left: 0, right: 0, textAlign: "center", fontSize: 66, fontWeight: 900, color: "#FFD54A",
            opacity: p, letterSpacing: `${0.25 * (1 - p)}em`, textShadow: `0 0 ${28 * p}px rgba(255,213,74,0.55), 0 3px 12px rgba(0,0,0,0.6)` }}>{title}</div>;
        })()}
        <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
          {items.map((it, i) => {
            if (i === 0) return null;
            const a = at(i - 1), b = at(i), p = ramp(t, it.at - 0.3, 0.32, inOut);
            return p > 0 && <line key={i} x1={a.x} y1={a.y} x2={a.x + (b.x - a.x) * p} y2={a.y + (b.y - a.y) * p} stroke="rgba(200,215,255,0.55)" strokeWidth={2.5}
              strokeDasharray="2 10" strokeLinecap="round" style={{ filter: "drop-shadow(0 0 6px rgba(160,190,255,0.8))" }} />;
          })}
        </svg>
        {items.map((it, i) => {
          const { x, y } = at(i), s = ramp(t, it.at - 0.16, 0.5), p = ramp(t, it.at - 0.02, 0.36);
          if (s <= 0) return null;
          const flare = Math.sin(Math.PI * Math.min(1, s)) * (1 - 0.3 * p);   // the star: up and gone in half a second
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", left: x - 130, top: y - 3, width: 260, height: 6, opacity: flare, transform: `scaleX(${0.2 + 1.3 * s})`,
                background: "radial-gradient(ellipse at center, rgba(255,255,255,0.95) 0%, rgba(170,200,255,0.4) 35%, rgba(255,255,255,0) 70%)" }} />
              <div style={{ position: "absolute", left: x - 3, top: y - 80, width: 6, height: 160, opacity: flare * 0.8, transform: `scaleY(${0.2 + 0.9 * s})`,
                background: "radial-gradient(ellipse at center, rgba(255,255,255,0.95) 0%, rgba(170,200,255,0.35) 35%, rgba(255,255,255,0) 70%)" }} />
              <div style={{ position: "absolute", left: x - 26, top: y - 26, width: 52, height: 52, borderRadius: "50%", opacity: flare,
                background: "radial-gradient(circle, #fff 0%, rgba(190,210,255,0.6) 30%, rgba(255,255,255,0) 70%)" }} />
              {p > 0 && <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${0.86 + 0.14 * p})`, opacity: Math.min(1, p * 1.4),
                filter: `blur(${(1 - Math.min(1, p * 1.4)) * 8}px)`, whiteSpace: "nowrap", padding: "14px 40px 18px", borderRadius: 999,
                background: "linear-gradient(135deg, rgba(30,40,70,0.62), rgba(8,10,22,0.7))", border: "1.5px solid rgba(190,210,255,0.45)",
                boxShadow: `0 0 ${30 * p}px rgba(140,170,255,0.35), inset 0 1px 0 rgba(255,255,255,0.25)`, backdropFilter: "blur(8px)",
                fontSize: 62, fontWeight: 900, color: "#fff", letterSpacing: `${0.08 * (1 - p)}em` }}>{it.text}</div>}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const GlassList: React.FC<ListP & { font: string }> = (props) => {
  const { title, items, from, until, y, font, wrap, bg, theme } = props;
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < from - 0.4 || t > until + 0.4) return null;
  if (theme === "space" && bg) return <SpaceList {...props} />;
  const out = ramp(t, until, 0.35, inOut);
  const open = ramp(t, from - 0.1, 0.3, inOut);
  const Y = y ?? (bg ? 560 : 150), big = !!bg;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {bg && <Backdrop file={bg} from={from} until={until} t={t} />}
      <div style={{ position: "absolute", top: Y, left: 110, right: 110, direction: "rtl", fontFamily: font, display: "flex", flexDirection: wrap ? "row" : "column",
        flexWrap: wrap ? "wrap" : "nowrap", justifyContent: "center", gap: big ? 22 : wrap ? 12 : 14, opacity: 1 - out, transform: `translateY(${-30 * out}px)` }}>
        {title && (
          <div style={{ alignSelf: "center", width: wrap ? "100%" : undefined, textAlign: "center", fontSize: big ? 64 : 46, fontWeight: 900, color: "#FFD54A",
            opacity: open, textShadow: "0 3px 12px rgba(0,0,0,0.55)", transform: `scale(${0.85 + 0.15 * open})`, marginBottom: big ? 10 : 0 }}>{title}</div>
        )}
        {items.map((it, i) => {
          const p = ramp(t, it.at - 0.12, 0.34);
          if (p <= 0) return null;
          return (
            <div key={i} style={{ ...glass, alignSelf: "center", padding: wrap ? (big ? "16px 34px 20px" : "10px 24px 13px") : big ? "22px 50px 26px" : "14px 34px 18px",
              borderRadius: big ? 34 : wrap ? 22 : 26, fontSize: big ? (wrap ? 58 : 68) : wrap ? 42 : 52, fontWeight: 900, color: "#fff", whiteSpace: "nowrap",
              opacity: Math.min(1, p * 1.6), transform: `translateY(${(1 - Math.min(1, p)) * 26}px) scale(${0.7 + 0.3 * back(Math.min(1, p))})` }}>
              {it.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** a dashed arrow that draws itself down from one node to the next (0→1 over 0.45 s), the head landing last */
const Arrow: React.FC<{ y0: number; y1: number; p: number }> = ({ y0, y1, p }) => {
  const len = y1 - y0, drawn = len * Math.min(1, p);
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
      <defs>
        <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#FFD54A" stopOpacity="0.4" /><stop offset="1" stopColor="#FFD54A" /></linearGradient>
        <clipPath id={`ac${y0}`}><rect x={0} y={y0} width={1080} height={drawn} /></clipPath>
      </defs>
      <g clipPath={`url(#ac${y0})`}>
        <line x1={540} y1={y0} x2={540} y2={y1 - 22} stroke="url(#ag)" strokeWidth={7} strokeDasharray="18 14" strokeLinecap="round" />
      </g>
      {p > 0.85 && <path d={`M ${518} ${y1 - 34} L 540 ${y1 - 6} L ${562} ${y1 - 34}`} fill="none" stroke="#FFD54A" strokeWidth={8} strokeLinecap="round" strokeLinejoin="round"
        opacity={Math.min(1, (p - 0.85) / 0.15)} />}
    </svg>
  );
};

export const Flow: React.FC<FlowP & { font: string }> = ({ title, nodes, from, until, bg, font }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < from - 0.3 || t > until + 0.4) return null;
  const out = ramp(t, until, 0.35, inOut);
  const H = 160, GAP = 150, top = title ? 290 : 240;   // node height, the arrow's run between nodes
  const yOf = (i: number) => top + i * (H + GAP);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {bg && <Backdrop file={bg} from={from} until={until} t={t} />}
      <AbsoluteFill style={{ opacity: 1 - out, direction: "rtl", fontFamily: font }}>
        {title && <div style={{ position: "absolute", top: top - 150, left: 0, right: 0, textAlign: "center", fontSize: 66, fontWeight: 900, color: "#FFD54A",
          opacity: ramp(t, from - 0.2, 0.3, inOut), textShadow: "0 3px 12px rgba(0,0,0,0.55)" }}>{title}</div>}
        {nodes.map((n, i) => {
          // the arrow from the node before starts as this node's word nears and finishes as the node lands
          const p = ramp(t, n.at - 0.1, 0.34);
          const a = i > 0 ? ramp(t, n.at - 0.55, 0.45) : 0;
          return (
            <React.Fragment key={i}>
              {i > 0 && a > 0 && <Arrow y0={yOf(i - 1) + H + 14} y1={yOf(i) - 8} p={a} />}
              {p > 0 && (
                <div style={{ ...glass, position: "absolute", top: yOf(i), left: 130, right: 130, height: H, borderRadius: 36, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", gap: 6, opacity: Math.min(1, p * 1.6), transform: `scale(${0.75 + 0.25 * back(Math.min(1, p))})` }}>
                  {n.label && <div style={{ fontSize: 40, fontWeight: 800, color: "#FFD54A", letterSpacing: "0.02em" }}>{n.label}</div>}
                  <div style={{ fontSize: 60, fontWeight: 900, color: "#fff", whiteSpace: "nowrap" }}>{n.text}</div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
