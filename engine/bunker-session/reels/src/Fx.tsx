import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { B, FONT, GRAD, clamp, ink, ramp } from "./look";

// Overlay animations for a project Alon cut himself (תוכן הבונקר לממומן, 25.10.2026: «במקומות מתאימים תכניס אנימציות של
// remotion שישדרגו את הסרטון — עם אפשרות לבטל / למחוק»). Each one renders ALONE on transparent at the canvas size
// (w×h from the props — 1920×1080 or 1080×1920) and goes on its own CapCut track, so deleting it is one click.
// x/y = the anchor as a fraction of the canvas; s = the base size in px.
export type FxProps = {
  kind: "bignum" | "logo" | "clock" | "count" | "checklist" | "headline" | "list";
  w: number; h: number; dur: number; x: number; y: number; s: number;
  text?: string; from?: number; to?: number; prefix?: string; suffix?: string; label?: string; items?: string[];
  big?: string; small?: string; color?: string;
};

const useLife = (dur: number) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const t = f / fps;
  const inn = spring({ frame: f, fps, config: { damping: 11, stiffness: 140, mass: 0.7 } });
  const out = interpolate(t, [dur - 0.28, dur], [0, 1], clamp);
  return { t, f, fps, inn, out };
};

const BigNum: React.FC<FxProps> = ({ text = "1", s, dur }) => {
  const { t, inn, out } = useLife(dur);
  return (
    <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: s, lineHeight: 0.8, color: B.gold, letterSpacing: "-0.04em",
      transform: `translateY(${(1 - inn) * s * 0.18 - t * s * 0.03}px) scale(${0.55 + 0.45 * inn})`, opacity: Math.min(1, inn * 1.4) * (1 - out),
      textShadow: `0 ${s * 0.04}px ${s * 0.12}px rgba(0,0,0,0.55)` }}>{text}</div>
  );
};

const Logo: React.FC<FxProps> = ({ s, dur }) => {
  const { inn, out } = useLife(dur);
  return <Img src={staticFile("logo_round.png")} style={{ width: s, height: s, transform: `scale(${inn * (1 - 0.85 * out)}) rotate(${(1 - inn) * -14}deg)`,
    opacity: 1 - out, filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.5))" }} />;
};

const Pill: React.FC<{ text: string; s: number; k: number }> = ({ text, s, k }) => (
  <div style={{ background: GRAD, color: "#fff", fontFamily: FONT, fontWeight: 900, fontSize: s * 0.34, lineHeight: 1, padding: `${s * 0.1}px ${s * 0.22}px ${s * 0.12}px`,
    borderRadius: 999, direction: "rtl", whiteSpace: "nowrap", transform: `scale(${k})`, boxShadow: "0 8px 22px rgba(0,0,0,0.45)" }}>{text}</div>
);

const Clock: React.FC<FxProps> = ({ s, dur, label = "24 שעות" }) => {
  const { t, inn, out } = useLife(dur);
  const turn = ramp(t, 0.15, 1.3) * 360;                                  // one full day in 1.3 s
  const r = s / 2;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: s * 0.12, opacity: 1 - out, transform: `scale(${0.6 + 0.4 * inn})` }}>
      <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
        <circle cx={r} cy={r} r={r - s * 0.05} fill={B.bg} stroke={B.gold} strokeWidth={s * 0.06} />
        <path d={`M ${r} ${r} L ${r} ${s * 0.12} A ${r - s * 0.12} ${r - s * 0.12} 0 ${turn > 180 ? 1 : 0} 1 ${r + (r - s * 0.12) * Math.sin((turn * Math.PI) / 180)} ${r - (r - s * 0.12) * Math.cos((turn * Math.PI) / 180)} Z`}
          fill={B.red} opacity={0.55} />
        <line x1={r} y1={r} x2={r + (r - s * 0.16) * Math.sin((turn * Math.PI) / 180)} y2={r - (r - s * 0.16) * Math.cos((turn * Math.PI) / 180)}
          stroke="#fff" strokeWidth={s * 0.05} strokeLinecap="round" />
        <circle cx={r} cy={r} r={s * 0.05} fill="#fff" />
      </svg>
      <Pill text={label} s={s} k={ramp(t, 0.25, 0.3)} />
    </div>
  );
};

const Count: React.FC<FxProps> = ({ s, dur, from = 0, to = 100, prefix = "", suffix = "", label }) => {
  const { t, inn, out } = useLife(dur);
  const v = Math.round(interpolate(ramp(t, 0.1, Math.min(1.2, dur * 0.5)), [0, 1], [from, to]));
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: s * 0.08, opacity: 1 - out, transform: `scale(${0.7 + 0.3 * inn})` }}>
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: s, lineHeight: 0.95, direction: "ltr", color: "#fff", textShadow: ink(Math.max(3, s * 0.035)) }}>
        {prefix}{v.toLocaleString("en-US")}<span style={{ color: B.gold }}>{suffix}</span>
      </div>
      {label && <Pill text={label} s={s * 0.8} k={ramp(t, 0.3, 0.3)} />}
    </div>
  );
};

const Checklist: React.FC<FxProps> = ({ s, dur, items = [] }) => {
  const { t, out } = useLife(dur);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: s * 0.18, direction: "rtl", opacity: 1 - out }}>
      {items.map((it, i) => {
        const k = ramp(t, 0.1 + i * 0.32, 0.28);
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: s * 0.25, background: "rgba(9,9,11,0.82)", borderRight: `${s * 0.08}px solid ${B.gold}`,
            padding: `${s * 0.16}px ${s * 0.3}px`, borderRadius: s * 0.16, transform: `translateX(${(1 - k) * -40}px)`, opacity: k }}>
            <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: s * 0.5, color: B.text, whiteSpace: "nowrap" }}>{it}</span>
            <span style={{ fontSize: s * 0.5, color: B.gold, fontWeight: 900, fontFamily: FONT }}>✓</span>
          </div>
        );
      })}
    </div>
  );
};

// the caption itself, designed (Alon 25.10: «שהכיתוב של 400 שקלים בלבד יכנס בעיצוב … עם אנימציית טקסט — blur אלגנטי»):
// stands in the caption's place for the words it replaces — a big gold figure + the small words, each sharpening out of a blur
const blurIn = (t: number, at: number, d = 0.45) => {
  const k = ramp(t, at, d);
  return { filter: `blur(${(1 - k) * 18}px)`, opacity: k, transform: `scale(${1.08 - 0.08 * k})`, letterSpacing: `${(1 - k) * 0.12}em` };
};
const Headline: React.FC<FxProps> = ({ s, dur, big = "", small = "", color = B.gold }) => {
  const { t, out } = useLife(dur);
  const fade = { opacity: 1 - out, filter: `blur(${out * 12}px)` };
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: s * 0.04, direction: "rtl", ...fade }}>
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: s, lineHeight: 0.95, color, whiteSpace: "nowrap", textShadow: ink(Math.max(4, s * 0.045)), ...blurIn(t, 0) }}>{big}</div>
      {small && <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: s * 0.42, lineHeight: 1, color: "#fff", whiteSpace: "nowrap", textShadow: ink(4), ...blurIn(t, 0.18) }}>{small}</div>}
    </div>
  );
};
const List: React.FC<FxProps> = ({ s, dur, items = [] }) => {
  const { t, out } = useLife(dur);
  const step = Math.min(0.9, (dur - 0.8) / Math.max(1, items.length));
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: s * 0.12, direction: "rtl", opacity: 1 - out }}>
      {items.map((it, i) => (
        <div key={i} style={{ fontFamily: FONT, fontWeight: 900, fontSize: s, lineHeight: 1, color: i % 2 ? B.gold : "#fff", whiteSpace: "nowrap", textShadow: ink(4), ...blurIn(t, i * step) }}>
          <span style={{ color: B.gold }}>✓ </span>{it}
        </div>
      ))}
    </div>
  );
};

export const Fx: React.FC<FxProps> = (p) => (
  <AbsoluteFill style={{ background: "transparent" }}>
    <div style={{ position: "absolute", left: p.x * p.w, top: p.y * p.h, transform: "translate(-50%, -50%)" }}>
      {p.kind === "bignum" && <BigNum {...p} />}
      {p.kind === "logo" && <Logo {...p} />}
      {p.kind === "clock" && <Clock {...p} />}
      {p.kind === "count" && <Count {...p} />}
      {p.kind === "checklist" && <Checklist {...p} />}
      {p.kind === "headline" && <Headline {...p} />}
      {p.kind === "list" && <List {...p} />}
    </div>
  </AbsoluteFill>
);
