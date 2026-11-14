import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, clamp } from "./look";

// A luxury glass name plate for a 16:9 episode (נאווה בויום 11.11.2026: «זכוכית שם יוקרתית שעולה עם כל דובר»).
// Rendered alone on transparent at 1920×1080 and laid on its own CapCut track at scale 1, so the place is baked here:
// bottom corner (side), clear of the faces. It rises out of a blur, a gold bar draws down its leading edge, one light sweep
// crosses the glass, and it sinks back out.
export type NameGlassP = { name: string; sub?: string; side?: "right" | "left"; dur: number; size?: number };

const out = Easing.bezier(0.16, 1, 0.3, 1), io = Easing.bezier(0.45, 0, 0.25, 1);

export const NameGlass: React.FC<NameGlassP> = ({ name, sub, side = "right", dur, size = 70 }) => {
  const t = useCurrentFrame() / useVideoConfig().fps;
  const inn = interpolate(t, [0, 0.8], [0, 1], { ...clamp, easing: out });
  const gone = interpolate(t, [dur - 0.55, dur], [0, 1], { ...clamp, easing: io });
  const bar = interpolate(t, [0.3, 0.95], [0, 1], { ...clamp, easing: io });
  const txt = interpolate(t, [0.22, 0.9], [0, 1], { ...clamp, easing: out });
  const sweep = interpolate(t, [0.55, 1.5], [-0.5, 1.5], { ...clamp, easing: io });
  const blur = (1 - inn) * 14 + gone * 10;
  const edge = side === "right" ? { right: 92 } : { left: 92 };
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", bottom: 104, ...edge, direction: "rtl", opacity: inn * (1 - gone),
        transform: `translateY(${(1 - inn) * 70 + gone * 26}px) scale(${0.96 + 0.04 * inn})`, transformOrigin: side === "right" ? "100% 100%" : "0% 100%",
        filter: blur > 0.3 ? `blur(${blur}px)` : undefined }}>
        <div style={{ position: "relative", overflow: "hidden", borderRadius: 26, padding: `${size * 0.36}px ${size * 0.62}px ${size * 0.42}px ${size * 0.7}px`,
          background: "linear-gradient(135deg, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0.07) 38%, rgba(14,14,20,0.34) 100%)",
          border: "1.5px solid rgba(255,255,255,0.34)",
          boxShadow: "inset 0 1.5px 0 rgba(255,255,255,0.55), inset 0 -1px 0 rgba(255,255,255,0.10), inset 0 0 40px rgba(255,255,255,0.06), 0 22px 60px rgba(0,0,0,0.38)" }}>
          {/* the gold bar on the leading (right) edge, drawn top to bottom */}
          <div style={{ position: "absolute", right: 0, top: 0, width: 6, height: `${bar * 100}%`,
            background: "linear-gradient(180deg, #FCE7A8 0%, #F6C453 45%, #B8862B 100%)", boxShadow: "0 0 14px rgba(246,196,83,0.55)" }} />
          {/* one light sweep across the glass */}
          <div style={{ position: "absolute", top: -40, bottom: -40, width: "38%", left: `${sweep * 100}%`, transform: "skewX(-18deg)",
            background: "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.28) 50%, rgba(255,255,255,0) 100%)" }} />
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: size, lineHeight: 1.05, color: "#fff", whiteSpace: "nowrap",
            letterSpacing: `${(1 - txt) * 0.06}em`, opacity: txt, transform: `translateY(${(1 - txt) * 14}px)`,
            textShadow: "0 2px 10px rgba(0,0,0,0.45)" }}>{name}</div>
          {sub && <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: size * 0.45, color: "#F6C453", marginTop: size * 0.12, whiteSpace: "nowrap",
            opacity: interpolate(t, [0.5, 1.1], [0, 1], clamp) }}>{sub}</div>}
        </div>
      </div>
    </AbsoluteFill>
  );
};
