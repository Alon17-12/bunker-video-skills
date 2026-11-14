// The northern border on a real map (לקוח I r3 4.11.2026: «תכניס אנימציות של הגבול של ישראל עם מדינות האויב»).
// Natural Earth borders (borderGeo.ts). Two modes, full frame like the world map:
//   missiles — wide over the region, two missiles arc from Tehran into the Galilee; at `shatter` the camera dives onto the
//              Lebanese border, which burns red while short rockets land on Kiryat Shmona
//   drone    — close on the border: a drone crosses from Lebanon over Kiryat Shmona (`steps[0]`) and turns south (`steps[1]`)
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { ramp, inOut } from "./look";
import { GEO } from "./borderGeo";
import type { AeBeat } from "./ae";

const sec = () => { const { fps } = useVideoConfig(); return useCurrentFrame() / fps; };
const GOLD = "linear-gradient(180deg, #FFF1C4 0%, #F6C453 45%, #B7811B 100%)";
const ENEMY = ["LB", "SY", "IR"];
const P = GEO.pts as Record<string, readonly [number, number]>;
const CY = 760;
const LEB_NEAR = [P.kiryat[0] - 10, P.kiryat[1] - 30] as const;   // a spot just across the border, where the label sits once the camera is close   // the map's centre line — above the caption line (1170)

const arc = (a: readonly [number, number], b: readonly [number, number], lift: number) => {
  const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2 - lift;
  return `M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}`;
};
const onQuad = (a: readonly [number, number], b: readonly [number, number], lift: number, u: number) => {
  const c = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - lift];
  const x = (1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0], y = (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1];
  return [x, y] as const;
};

const Label: React.FC<{ x: number; y: number; text: string; font: string; k: number; red?: boolean; size?: number }> = ({ x, y, text, font, k, red, size = 54 }) =>
  k <= 0 ? null : (
    <div style={{ position: "absolute", left: x - 300, top: y - size, width: 600, display: "flex", justifyContent: "center", opacity: Math.min(1, k * 1.6),
      transform: `translateY(${(1 - k) * 24}px) scale(${0.7 + 0.3 * k})` }}>
      <div style={{ fontFamily: font, fontWeight: 900, fontSize: size, direction: "rtl", whiteSpace: "nowrap", padding: "6px 24px 10px", borderRadius: 999,
        color: red ? "#fff" : "#1a1206", background: red ? "linear-gradient(180deg, #ff5a5f 0%, #c81e28 100%)" : GOLD, boxShadow: "0 10px 30px rgba(0,0,0,0.55)" }}>{text}</div>
    </div>
  );

export const AeBorder: React.FC<{ b: AeBeat; font: string }> = ({ b, font }) => {
  const t = sec();
  if (t < b.from - 0.02 || t > b.to + 0.02) return null;
  const k = ramp(t, b.from, 0.35, inOut) * (1 - ramp(t, b.to - 0.35, 0.35, inOut));
  const drone = b.text === "drone";
  const dive = drone ? 1 : ramp(t, (b.shatter ?? b.to) - 0.2, 0.9, inOut);
  // camera: wide over Israel → Iran, then onto the Galilee
  const wide = { x: 1620, y: 1060, z: 0.5 }, near = { x: P.kiryat[0] - 4, y: P.kiryat[1] + 14, z: drone ? 5.2 : 6.2 };
  const drift = 1 + 0.03 * ramp(t, b.from, b.to - b.from);
  const cx = wide.x + (near.x - wide.x) * dive, cy = wide.y + (near.y - wide.y) * dive;
  const z = Math.exp(Math.log(wide.z) + (Math.log(near.z) - Math.log(wide.z)) * dive) * drift;
  const sx = (x: number) => 540 + (x - cx) * z, sy = (y: number) => CY + (y - cy) * z;
  const burn = drone ? 0.6 + 0.4 * Math.sin(t * 5) : ramp(t, (b.shatter ?? b.to) + 0.3, 0.6) * (0.75 + 0.25 * Math.sin(t * 6));

  // missiles from Tehran (wide part only)
  const missiles = drone ? [] : [0, 0.45].map((d) => ({ p: ramp(t, b.from + 0.35 + d, 1.5, inOut), off: d ? 10 : -6 }));
  // rockets from southern Lebanon onto Kiryat Shmona after the dive
  const t1 = (b.shatter ?? b.to) + 0.7;
  const rockets = drone ? [] : [0, 0.55, 1.1].map((d, i) => ({ p: ramp(t, t1 + d, 0.6, (x) => x), i }));
  // the drone: north of the border → Kiryat Shmona → south
  const s0 = b.steps?.[0]?.at ?? b.from + 1.2, s1 = b.steps?.[1]?.at ?? s0 + 1.5;
  const north = [P.kiryat[0] - 3, P.kiryat[1] - 26] as const, south = [P.kiryat[0] - 10, P.kiryat[1] + 34] as const;
  const leg1 = ramp(t, b.from + 0.3, Math.max(0.6, s0 - b.from - 0.3), inOut), leg2 = ramp(t, s1 - 0.1, 1.4, inOut);
  const dpos = leg2 > 0 ? [P.kiryat[0] + (south[0] - P.kiryat[0]) * leg2, P.kiryat[1] + (south[1] - P.kiryat[1]) * leg2]
    : [north[0] + (P.kiryat[0] - north[0]) * leg1, north[1] + (P.kiryat[1] - north[1]) * leg1];
  const alarm = drone ? ramp(t, s0 - 0.3, 0.3) : ramp(t, t1 + 0.5, 0.3);

  return (
    <AbsoluteFill style={{ opacity: k, background: "#08111b", overflow: "hidden" }}>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="bglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
        </defs>
        <g transform={`translate(${540 - cx * z} ${CY - cy * z}) scale(${z})`}>
          {Object.entries(GEO.paths).map(([iso, d]) => {
            const il = iso === "IL" || iso === "PS", en = ENEMY.includes(iso);
            const enK = iso === "IR" ? 1 - dive * 0.6 : iso === "LB" ? 0.55 - 0.3 * dive : 0.6;
            return <path key={iso} d={d} vectorEffect="non-scaling-stroke" strokeWidth={il ? 3 : 2}
              fill={il ? "rgba(246,196,83,0.30)" : en ? `rgba(200,30,40,${0.18 + 0.2 * enK})` : "#18212b"}
              stroke={il ? "#F6C453" : en ? "rgba(255,90,95,0.85)" : "#33404e"} />;
          })}
          {/* the border with Lebanon and Syria — burns red after the dive */}
          {["IL_LB", "IL_SY"].map((id) => (
            <g key={id} opacity={burn}>
              <path d={GEO.lines[id as "IL_LB"]} fill="none" stroke="#ff2a35" strokeWidth={22} vectorEffect="non-scaling-stroke" filter="url(#bglow)" />
              <path d={GEO.lines[id as "IL_LB"]} fill="none" stroke="#ff5a61" strokeWidth={8} vectorEffect="non-scaling-stroke" />
              <path d={GEO.lines[id as "IL_LB"]} fill="none" stroke="#ffe3e4" strokeWidth={3} vectorEffect="non-scaling-stroke" />
            </g>
          ))}
          {missiles.map((m, i) => {
            if (m.p <= 0) return null;
            const d = arc(P.tehran, P.kiryat, 420 + m.off * 10);
            const ev = evolvePath(m.p, d);
            return <path key={i} d={d} fill="none" stroke="#ffb347" strokeWidth={4} vectorEffect="non-scaling-stroke" strokeLinecap="round"
              strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} opacity={1 - ramp(t, b.from + 2.2 + i * 0.45, 0.5)} />;
          })}
          {rockets.map((r) => {
            if (r.p <= 0 || r.p >= 1) return null;
            const from = [P.launch[0] + (r.i - 1) * 4, P.launch[1] - r.i * 2] as const;
            const d = arc(from, P.kiryat, 9);
            const ev = evolvePath(r.p, d);
            return <path key={r.i} d={d} fill="none" stroke="#ffb347" strokeWidth={4} vectorEffect="non-scaling-stroke" strokeLinecap="round"
              strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />;
          })}
          {/* the drone's trail: from the north up to where it is now */}
          {drone && leg1 > 0 && (
            <path d={leg2 > 0 ? `M${north[0]},${north[1]} L${P.kiryat[0]},${P.kiryat[1]} L${dpos[0]},${dpos[1]}` : `M${north[0]},${north[1]} L${dpos[0]},${dpos[1]}`}
              fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth={3} strokeDasharray="12 10" vectorEffect="non-scaling-stroke" />
          )}
        </g>
      </svg>
      {/* missile heads + impacts, in screen space so they keep their size through the zoom */}
      {missiles.map((m, i) => {
        if (m.p <= 0 || m.p >= 1) return null;
        const [x, y] = onQuad(P.tehran, P.kiryat, 420 + m.off * 10, m.p);
        return <div key={i} style={{ position: "absolute", left: sx(x) - 14, top: sy(y) - 14, width: 28, height: 28, borderRadius: 14,
          background: "radial-gradient(circle, #fff 0%, #ffcf6b 40%, rgba(255,120,40,0) 75%)", boxShadow: "0 0 30px 10px rgba(255,140,40,0.6)" }} />;
      })}
      {rockets.map((r) => {
        const hit = ramp(t, t1 + [0, 0.55, 1.1][r.i] + 0.6, 0.7);
        if (hit <= 0 || hit >= 1) return null;
        return <div key={r.i} style={{ position: "absolute", left: sx(P.kiryat[0]) - 30 - 120 * hit, top: sy(P.kiryat[1]) - 30 - 120 * hit, width: 60 + 240 * hit, height: 60 + 240 * hit,
          borderRadius: "50%", border: "6px solid #ff8a3d", opacity: 1 - hit }} />;
      })}
      {drone && leg2 < 1 && (
        <div style={{ position: "absolute", left: sx(dpos[0]) - 50, top: sy(dpos[1]) - 50, width: 100, height: 100,
          transform: "rotate(180deg)" }}>
          <svg width={100} height={100} viewBox="-34 -34 68 68">
            <path d="M0,-26 L8,4 L26,14 L4,10 L0,26 L-4,10 L-26,14 L-8,4 Z" fill="#e8ecf0" stroke="#0b0f14" strokeWidth={2} />
          </svg>
        </div>
      )}
      {alarm > 0 && (
        <div style={{ position: "absolute", left: sx(P.kiryat[0]) - 90, top: sy(P.kiryat[1]) - 90, width: 180, height: 180, borderRadius: "50%",
          border: "5px solid rgba(255,59,68,0.9)", transform: `scale(${0.6 + 0.6 * ((t * 1.4) % 1)})`, opacity: alarm * (1 - ((t * 1.4) % 1)) }} />
      )}
      <div style={{ position: "absolute", left: sx(P.kiryat[0]) - 13, top: sy(P.kiryat[1]) - 13, width: 26, height: 26, borderRadius: 13, background: "#F6C453",
        boxShadow: "0 0 24px rgba(246,196,83,0.9)", opacity: drone ? 1 : ramp(t, b.from + 1.6, 0.3) }} />
      {/* labels */}
      {!drone && <Label x={sx(P.iran[0])} y={sy(P.iran[1])} text="איראן" font={font} red k={ramp(t, b.from + 0.25, 0.4) * (1 - dive)} size={64} />}
      <Label x={sx(P.lebanon[0] + (LEB_NEAR[0] - P.lebanon[0]) * dive)} y={sy(P.lebanon[1] + (LEB_NEAR[1] - P.lebanon[1]) * dive)} text="חיזבאללה · לבנון" font={font} red
        k={drone ? ramp(t, b.from + 0.1, 0.4) : ramp(t, (b.shatter ?? b.to) + 0.2, 0.4)} size={drone ? 52 : 50 + 6 * dive} />
      {!drone && <Label x={sx(P.israel[0])} y={sy(P.israel[1])} text="ישראל" font={font} k={ramp(t, b.from + 0.15, 0.4) * (1 - dive)} />}
      <Label x={sx(P.kiryat[0]) + (drone ? 210 : 220)} y={sy(P.kiryat[1]) + 70} text="קריית שמונה" font={font}
        k={drone ? ramp(t, b.from + 0.2, 0.4) : ramp(t, (b.shatter ?? b.to) + 0.45, 0.4)} size={50} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.65) 100%)" }} />
    </AbsoluteFill>
  );
};
