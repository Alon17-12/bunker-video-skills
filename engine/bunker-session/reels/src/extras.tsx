// אורח K (צומת 20) round 2, 28.10.2026 — the graphics Alon asked for on top of the clean reel:
// an «illusion» on «חומרים משני תודעה», a liquid-glass statistic («פעמיים מתוך מאות»), the round badge of a person she
// introduces (as in the teaser), and the teaser's own «הגיבו "פרק"» pill on the end card.
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { inOut, ramp } from "./look";

const sec = () => { const { fps } = useVideoConfig(); return useCurrentFrame() / fps; };
const grow = (x: number) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2);

/** «אפקט של אשליה»: the shot doubles into two colour-shifted ghosts that drift apart and back, the hue breathes, and the
 *  frame sways a little — in over 0.3 s before the words, out over 0.3 s after them. `t0` = the shot's reel start (the
 *  wrapper sits inside the shot's Sequence, so its own clock is shot time). */
export const Trip: React.FC<{ t0: number; rs: [number, number][]; children: React.ReactNode }> = ({ t0, rs, children }) => {
  const t = t0 + sec();
  const r = rs.find(([a, b]) => t >= a - 0.3 && t < b + 0.3);
  const k = r ? Math.min(ramp(t, r[0] - 0.3, 0.3, inOut), 1 - ramp(t, r[1], 0.3, inOut)) : 0;
  if (k <= 0.001) return <>{children}</>;
  const ph = t - r![0];
  const dx = 34 * k * Math.sin(ph * 4.4), dy = 12 * k * Math.cos(ph * 3.1);
  const base: React.CSSProperties = { filter: `hue-rotate(${28 * k * Math.sin(ph * 2.6)}deg) saturate(${1 + 0.55 * k})`,
    transform: `scale(${1 + 0.035 * k}) rotate(${1.1 * k * Math.sin(ph * 2.2)}deg)` };
  const ghost = (s: number, hue: number): React.CSSProperties => ({ mixBlendMode: "screen", opacity: 0.42 * k,
    filter: `hue-rotate(${hue}deg) saturate(1.9) blur(${1.5 * k}px)`, transform: `translate(${s * dx}px, ${s * dy}px) scale(${1 + 0.06 * k})` });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={base}>{children}</AbsoluteFill>
      <AbsoluteFill style={ghost(1, 110)}>{children}</AbsoluteFill>
      <AbsoluteFill style={ghost(-1, -110)}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(0,0,0,0) 45%, rgba(70,0,120,0.45) 100%)", opacity: k }} />
    </AbsoluteFill>
  );
};

/** the statistic as one liquid-glass card under the captions (round 3, 28.10: «שהזכוכית תפתח עם אנימציה ושיהיה כתוב בה
 *  משהו שמרמז על סיכויי ההצלחה» / «הסיום ש"מאות" לא ברור»). It opens from a line of light into a card titled with the
 *  question — «סיכויי הצלחה» — over a big gold «?» on the illness, and folds back into the line. It reopens on «ראיתי»,
 *  two gold dots land on «פעמיים» («2 הצליחו»), hundreds of grey dots pour in around them from «מתוך», and on «מאות.» the
 *  answer slams onto the grid: «פחות מ-1%». Logos are hidden and captions lifted while it is up (Reel.tsx). */
export type StatP = { title: string; sub: string; inAt: number; outAt: number; recall: number; gold: number; many: number; total: number; until: number;
  cols?: number; rows?: number; hits?: number[]; odds?: string; y?: number; x?: number };
export const Stat: React.FC<StatP> = ({ title, sub, inAt, outAt, recall, gold, many, total, until, cols = 24, rows = 7, hits = [57, 110],
  odds = "פחות מ-1%", y = 1250, x = 510 }) => {
  const t = sec();
  const first = t >= inAt - 0.05 && t < outAt + 0.5, second = t >= recall - 0.05 && t < until + 0.5;
  if (!first && !second) return null;
  const a = first ? inAt : recall, b = first ? outAt : until;
  // open: a line of light widens (0.22 s), then the card unfolds from it with a touch of overshoot; close = the reverse
  const sx = ramp(t, a, 0.22, inOut) * (1 - ramp(t, b + 0.24, 0.2, inOut)), sy = ramp(t, a + 0.16, 0.42, grow) * (1 - ramp(t, b, 0.26, inOut));
  const body = ramp(t, a + 0.36, 0.25) * (1 - ramp(t, b - 0.05, 0.15));
  const g = second ? ramp(t, gold, 0.35, grow) : 0, f = second ? ramp(t, many, 0.25) : 0, m = second ? ramp(t, total, 0.32, grow) : 0;
  const q = 1 - g;                                   // the «?» — the question, until the first answer lands
  const W = 880, gap = 32, gw = cols * gap, gh = rows * gap, n = cols * rows;
  const cx = (cols - 1) / 2, cy = (rows - 1) / 2, far = Math.hypot(cx, cy);
  const head = !second || g <= 0 ? null : m > 0.02 ? "2 מתוך מאות" : "2 הצליחו";
  const F = "ReelLook";
  return (
    <div style={{ position: "absolute", left: x - W / 2, top: y, width: W, direction: "rtl" }}>
      <div style={{ position: "relative", borderRadius: 34, padding: "18px 34px 22px", background: "linear-gradient(140deg, rgba(255,255,255,0.2), rgba(18,22,30,0.55))",
        border: "2px solid rgba(255,255,255,0.6)", boxShadow: `0 22px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.7), 0 0 ${40 * (1 - sy)}px rgba(255,255,255,${0.8 * (1 - sy)})`,
        backdropFilter: "blur(18px) saturate(1.3)", WebkitBackdropFilter: "blur(18px) saturate(1.3)", overflow: "hidden",
        transform: `scale(${0.35 + 0.65 * sx}, ${0.03 + 0.97 * sy})`, opacity: Math.min(1, sx * 3), transformOrigin: "50% 50%" }}>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(115deg, transparent 30%, rgba(255,255,255,0.25) 45%, transparent 60%)",
          transform: `translateX(${(ramp(t, a + 0.3, 1.0, inOut) * 2 - 1) * 900}px)` }} />
        <div style={{ opacity: body }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 84, fontFamily: F, fontWeight: 900 }}>
            <div style={{ fontSize: 66, color: "#fff", textShadow: "0 3px 12px rgba(0,0,0,0.5)" }}>{title}</div>
            {head && <div style={{ fontSize: 64, color: "#F6C453", textShadow: "0 0 22px rgba(246,196,83,0.55), 0 3px 10px rgba(0,0,0,0.5)", whiteSpace: "nowrap",
              transform: `scale(${0.7 + 0.3 * (m > 0.02 ? m : g)})` }}>{head}</div>}
          </div>
          <div style={{ position: "relative", width: gw, height: gh, margin: "14px auto 0", direction: "ltr" }}>
            {!second || q > 0 ? (
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 34, direction: "rtl", fontFamily: F, fontWeight: 900, opacity: second ? q : 1 }}>
                {!second && <div style={{ fontSize: 54, color: "#fff", background: "rgba(255,255,255,0.14)", border: "2px solid rgba(255,255,255,0.45)", borderRadius: 999, padding: "8px 30px" }}>{sub}</div>}
                <div style={{ fontSize: 200, lineHeight: 1, color: "#F6C453", transform: `translateY(${Math.sin(t * 4) * 6}px) rotate(${Math.sin(t * 2.6) * 6}deg)`,
                  textShadow: "0 0 34px rgba(246,196,83,0.6), 0 6px 14px rgba(0,0,0,0.5)" }}>?</div>
              </div>) : null}
            {second && Array.from({ length: n }, (_, i) => {
              const c = i % cols, r = Math.floor(i / cols);
              const hit = hits.includes(i);
              // hundreds pour in from the two survivors outward, in 0.7 s from «מתוך»
              const d = Math.hypot(c - cx, r - cy) / far;
              const on = hit ? g : ramp(t, many + 0.02 + d * 0.45, 0.14);
              if (on <= 0) return null;
              const sz = hit ? 18 + 10 * g : 17;
              return <div key={i} style={{ position: "absolute", left: c * gap + (gap - sz) / 2, top: r * gap + (gap - sz) / 2, width: sz, height: sz, borderRadius: "50%",
                transform: `scale(${hit ? 1 : 0.4 + 0.6 * on})`, background: hit ? "#F6C453" : `rgba(255,255,255,${0.88 * on})`,
                boxShadow: hit ? `0 0 ${16 + 10 * m}px rgba(246,196,83,0.95)` : "none" }} />;
            })}
            {second && m > 0 && (
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ fontFamily: F, fontWeight: 900, fontSize: 70, lineHeight: 1, color: "#1a1206", padding: "12px 34px 16px", borderRadius: 999, direction: "rtl", whiteSpace: "nowrap",
                  background: "linear-gradient(180deg, #FFE7A3 0%, #F6C453 45%, #C98F1E 100%)", boxShadow: "0 0 0 3px rgba(255,231,163,0.55), 0 16px 40px rgba(0,0,0,0.55)",
                  transform: `scale(${1.6 - 0.6 * m}) rotate(-3deg)`, opacity: Math.min(1, m * 2) }}>{odds}</div>
              </div>)}
          </div>
        </div>
      </div>
    </div>
  );
};

/** the teaser's round badge (v10: «שהתמונה של אורח T תהיה בתוך עיגול קטן שיקפוץ מהצד של המסך — שיראו את כל הפנים שלו») */
export const Badge: React.FC<{ at: number; until: number; img: string; cx?: number; cy?: number; r?: number }> = ({ at, until, img, cx = 868, cy = 430, r = 150 }) => {
  const t = sec();
  if (t < at || t > until) return null;
  const u = t - at;
  const inn = 1 - Math.exp(-7 * u) * Math.cos(12 * u);
  const out = ramp(t, until - 0.25, 0.25, (q) => q * q);
  const dx = (1 - inn) * 420 + out * 460, rot = (1 - inn) * 25 + Math.sin(u * 5) * 3 * (1 - out), sc = 0.9 + 0.1 * Math.min(1, inn);
  return (
    <div style={{ position: "absolute", left: cx - r, top: cy - r + Math.sin(u * 5) * 5, width: 2 * r, height: 2 * r, borderRadius: "50%",
      transform: `translateX(${dx}px) rotate(${rot}deg) scale(${sc})`, boxShadow: "0 0 0 8px #fff, 0 0 0 11px #ffd60a, 0 14px 30px rgba(0,0,0,0.55)", overflow: "hidden" }}>
      <Img src={staticFile(img)} style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

/** the teaser's end-card CTA (guest-k-teaser outro_cta.png: a full-frame overlay, the pill at y 0.639 of the frame), moved to
 *  `y` and scaled by `k` — the same pill and the same word as the teaser, under the cover's title, never over it */
export const CtaImg: React.FC<{ u: number; file: string; y?: number; k?: number }> = ({ u, file, y = 0.968, k = 0.82 }) => {
  const g = ramp(u, 0.45, 0.3, grow);
  return (
    <AbsoluteFill style={{ opacity: Math.min(1, ramp(u, 0.45, 0.12)), transform: `translateY(${(y - 0.639) * 1920}px) scale(${(0.6 + 0.4 * g) * k})`, transformOrigin: "50% 63.9%" }}>
      <Img src={staticFile(file)} style={{ width: "100%", height: "100%" }} />
    </AbsoluteFill>
  );
};
