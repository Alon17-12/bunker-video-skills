// צומת 20 extra reels, round 4 (28.10.2026). Alon on the «התירוץ › הסיבה › התוצאה» board: «תחליף את הבירול לבירול השני
// המצורף (רקע שחור עם משבצות) ותתאים את האנימציה לתנועה של המשבצות ברקע, שיהיה הרמוני … שתהיה רק אנימציה אבל שתהיה חלקה
// נקייה ומודרנית עם תנועה מפורטת». So the chain is printed ON the grid: every node fills exactly three cells, the whole column
// rides with the grid's drift (measured, not guessed — `grid` in plans.json), the cells light up right-to-left before a node
// lands, a dashed arrow runs down the middle cell's centre line, and gold crosshairs mark the active node's grid corners.
// The backdrop is never pushed or scaled: any zoom would slide the lines off the cards.
//   plans.json flow: { "theme": "grid", "bg": "bg/grid.mp4", "grid": { "x": 40.5, "v": 33.8, "pitch": 250, "y": 205 }, "caps": false, … }
//   x = a vertical line's x at the backdrop's first frame, v = px/s to the right, y = a horizontal line's y (lines don't move vertically).
import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { inOut, ramp } from "./look";
import type { FlowP } from "./glassList";

export type GridP = { x: number; v: number; pitch: number; y: number; rate?: number };   // rate slows the backdrop for a long chain (v = 33.8 × rate), else the column rides off the frame
const GOLD = "255,213,74";
const LEAD = 0.35;   // the backdrop starts this long before the first node

const Cross: React.FC<{ x: number; y: number; k: number }> = ({ x, y, k }) => (
  <div style={{ position: "absolute", left: x - 16, top: y - 16, width: 32, height: 32, opacity: k, transform: `rotate(${(1 - k) * 90}deg) scale(${0.4 + 0.6 * k})` }}>
    <div style={{ position: "absolute", left: 14.5, top: 0, width: 3, height: 32, background: `rgb(${GOLD})`, borderRadius: 2 }} />
    <div style={{ position: "absolute", left: 0, top: 14.5, width: 32, height: 3, background: `rgb(${GOLD})`, borderRadius: 2 }} />
  </div>
);

export const GridFlow: React.FC<FlowP & { font: string; grid: GridP }> = ({ nodes, from, until, bg, grid: g, font }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < from - LEAD - 0.3 || t > until + 0.5) return null;
  const T0 = from - LEAD;
  const k = Math.min(ramp(t, T0 - 0.25, 0.25, inOut), 1 - ramp(t, until, 0.3, inOut));
  const out = ramp(t, until - 0.3, 0.3, inOut);   // gone by the next spoken line, whose caption comes back
  const P = g.pitch, left = g.x + g.v * (t - T0), W = 3 * P, H = P;
  const top = (i: number) => g.y + i * 2 * P;
  const active = nodes.reduce((a, n, i) => (t >= n.at - 0.12 ? i : a), 0);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ opacity: k, background: "#161616" }}>
        <Sequence from={Math.round(T0 * fps)} layout="none">
          <OffthreadVideo src={staticFile(bg!)} muted playbackRate={g.rate ?? 1} style={{ position: "absolute", inset: 0, width: 1080, height: 1920, filter: "brightness(1.15) contrast(1.35)" }} />
        </Sequence>
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.45) 100%)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - out, direction: "rtl", fontFamily: font }}>
        {nodes.map((n, i) => {
          const y = top(i);
          // the three cells light right-to-left, then settle to a faint gold wash under the card
          const cells = [2, 1, 0].map((c, j) => {
            const p = ramp(t, n.at - 0.34 + j * 0.06, 0.16);
            const flash = p * (1 - 0.65 * ramp(t, n.at + 0.1 + j * 0.06, 0.4));
            return p > 0 && <div key={c} style={{ position: "absolute", left: left + c * P, top: y, width: P, height: H,
              background: `rgba(${GOLD},${0.13 * flash})`, boxShadow: `inset 0 0 0 2px rgba(${GOLD},${0.7 * flash})` }} />;
          });
          const p = ramp(t, n.at - 0.14, 0.4);
          const q = ramp(t, n.at + 0.02, 0.42, inOut);           // text wipes in from the right (RTL)
          const on = i === active ? 1 - ramp(t, (nodes[i + 1]?.at ?? 1e9) - 0.12, 0.3) : i < active ? 0 : ramp(t, n.at - 0.12, 0.3);
          const dim = i < active ? 0.72 : 1;
          // the arrow from the node above: draws down the middle cell's centre line, the dashes keep flowing after it lands
          const a = i > 0 ? ramp(t, n.at - 0.66, 0.46, inOut) : 0;
          const ax = left + 1.5 * P, ay0 = top(i - 1) + H + 10, ay1 = y - 12, drawn = (ay1 - ay0) * a;
          const ripple = ramp(t, n.at - 0.2, 0.55);
          return (
            <React.Fragment key={i}>
              {cells}
              {i > 0 && a > 0 && (
                <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
                  <defs>
                    <linearGradient id={`gfa${i}`} x1="0" y1={ay0} x2="0" y2={ay1} gradientUnits="userSpaceOnUse">
                      <stop offset="0" stopColor={`rgb(${GOLD})`} stopOpacity="0.25" /><stop offset="1" stopColor={`rgb(${GOLD})`} />
                    </linearGradient>
                    <clipPath id={`gfc${i}`}><rect x={0} y={ay0 - 4} width={1080} height={drawn + 4} /></clipPath>
                  </defs>
                  <line x1={ax} y1={ay0} x2={ax} y2={ay1 - 16} stroke={`url(#gfa${i})`} strokeWidth={6} strokeDasharray="16 14" strokeDashoffset={-t * 42}
                    strokeLinecap="round" clipPath={`url(#gfc${i})`} />
                  {a < 1 && <circle cx={ax} cy={ay0 + drawn} r={9} fill={`rgb(${GOLD})`} style={{ filter: `drop-shadow(0 0 10px rgba(${GOLD},0.9))` }} />}
                  {a > 0.9 && <path d={`M ${ax - 20} ${ay1 - 28} L ${ax} ${ay1 - 6} L ${ax + 20} ${ay1 - 28}`} fill="none" stroke={`rgb(${GOLD})`} strokeWidth={7}
                    strokeLinecap="round" strokeLinejoin="round" opacity={(a - 0.9) / 0.1} />}
                </svg>
              )}
              {i > 0 && ripple > 0 && ripple < 1 && (
                <div style={{ position: "absolute", left: left + P, top: y, width: P, height: H, boxShadow: `inset 0 0 0 3px rgba(${GOLD},${0.8 * (1 - ripple)})`,
                  transform: `scale(${1 + 0.35 * ripple})` }} />
              )}
              {p > 0 && (
                <div style={{ position: "absolute", left: left + 14, top: y + 14, width: W - 28, height: H - 28, borderRadius: 22,
                  background: "linear-gradient(160deg, rgba(34,34,34,0.82), rgba(14,14,14,0.86))",
                  boxShadow: `inset 0 0 0 ${1.5 + 1.5 * on}px rgba(${on > 0.01 ? GOLD : "255,255,255"},${0.2 + 0.7 * on}), 0 18px 44px rgba(0,0,0,0.5), 0 0 ${38 * on}px rgba(${GOLD},${0.28 * on})`,
                  opacity: Math.min(1, p * 1.5) * dim, transform: `scale(${0.93 + 0.07 * p})`, filter: `blur(${(1 - Math.min(1, p * 1.3)) * 10}px)`,
                  display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4 }}>
                  {n.label && <div style={{ fontSize: 42, fontWeight: 800, color: `rgb(${GOLD})`, letterSpacing: `${0.02 + 0.12 * (1 - q)}em`, opacity: q }}>{n.label}</div>}
                  <div style={{ fontSize: 70, fontWeight: 900, color: "#fff", whiteSpace: "nowrap", clipPath: `inset(0 0 0 ${(1 - q) * 100}%)` }}>{n.text}</div>
                </div>
              )}
              {i === active && p > 0 && [[0, 0], [W, 0], [0, H], [W, H]].map(([cx, cy], c) =>
                <Cross key={c} x={left + cx} y={y + cy} k={ramp(t, n.at + c * 0.04, 0.3) * on} />)}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
