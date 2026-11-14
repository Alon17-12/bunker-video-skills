// «עריכה ברמה אחת מעל» (צומת 20 × אורח B, 28.10.2026: «מוזיקה טרנדית, בירולים, אנימציות 3D וזכוכית יוקרתית — נקי,
// בקלאס, motion graphic ברמה גבוהה»): full-frame 3D inserts the voice runs on under, in one dark-glass look —
// black-green stage, gold light, a reflective glass floor. plans.json: "lux": [{ "kind": "containers", "at": "word#n",
// "until": "word#n" | seconds, … }] (anchors resolve like the other graphics).
import React, { useEffect, useMemo } from "react";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { inOut, ramp } from "./look";

export type LuxP = { kind: "containers" | "money" | "card" | "pyramid"; from: number; to: number; count?: number; label?: string; sub?: string;
  amount?: number; prefix?: string; suffix?: string; img?: string; labelAt?: number;
  text?: string; strikeAt?: number; tiers?: string[]; steps?: number[] };

const GOLD = "#E9C46A", GREEN = "#0E3B2E";
const back = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);

/** the studio light every scene reflects (no HDR file — three's RoomEnvironment through PMREM) */
const Env: React.FC = () => {
  const { gl, scene } = useThree();
  useEffect(() => {
    const pm = new THREE.PMREMGenerator(gl);
    const tex = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = tex;
    return () => { tex.dispose(); pm.dispose(); };
  }, [gl, scene]);
  return null;
};

/** corrugated container side: vertical ridges + a thin top/bottom rail, drawn once into a canvas */
const ridges = (base: string) => {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 128;
  const g = c.getContext("2d")!;
  g.fillStyle = base; g.fillRect(0, 0, 512, 128);
  for (let x = 0; x < 512; x += 16) {
    const grd = g.createLinearGradient(x, 0, x + 16, 0);
    grd.addColorStop(0, "rgba(0,0,0,0.28)"); grd.addColorStop(0.5, "rgba(255,255,255,0.16)"); grd.addColorStop(1, "rgba(0,0,0,0.28)");
    g.fillStyle = grd; g.fillRect(x, 6, 16, 116);
  }
  g.fillStyle = "rgba(0,0,0,0.45)"; g.fillRect(0, 0, 512, 6); g.fillRect(0, 122, 512, 6);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
};

const Container: React.FC<{ u: number; i: number; color: string }> = ({ u, i, color }) => {
  const tex = useMemo(() => ridges(color), [color]);
  const d = 0.42 * i, k = ramp(u, 0.1 + d, 0.55, (x) => x * x);                         // the fall
  const land = Math.max(0, u - 0.65 - d), bounce = Math.exp(-7 * land) * Math.abs(Math.sin(land * 13)) * 0.22 * (land > 0 ? 1 : 0);
  const y = 0.62 + i * 1.26 + (1 - k) * 7 + bounce;
  const rot = (i ? -0.12 : 0.08) + (1 - k) * (i ? 0.5 : -0.4);
  return (
    <mesh position={[i ? 0.35 : 0.1, y, 0]} rotation={[0, rot, 0]} castShadow receiveShadow>
      <boxGeometry args={[4.4, 1.2, 1.2]} />
      <meshPhysicalMaterial map={tex} metalness={0.55} roughness={0.38} clearcoat={0.6} clearcoatRoughness={0.25} envMapIntensity={1.1} />
    </mesh>
  );
};

/** the money on a thick glass slab: gold digits counting up inside the glass (or a fixed `text`), the slab turning in from
 *  the side; `strikeAt` (s into the insert) draws a red line through it — «לא נשאר לי 100 מיליון בכיס» */
const MoneySlab: React.FC<{ u: number; amount: number; prefix: string; suffix: string; dur: number; text?: string; strikeAt?: number }> = ({ u, amount, prefix, suffix, dur, text, strikeAt }) => {
  const canvas = useMemo(() => { const c = document.createElement("canvas"); c.width = 1024; c.height = 384; return c; }, []);
  const tex = useMemo(() => { const t = new THREE.CanvasTexture(canvas); t.colorSpace = THREE.SRGBColorSpace; return t; }, [canvas]);
  const v = Math.round(amount * ramp(u, 0.25, Math.min(1.3, dur * 0.55), inOut));
  const str = text ?? `${prefix}${v.toLocaleString("en-US")}${suffix}`;
  const g = canvas.getContext("2d")!;
  g.clearRect(0, 0, 1024, 384);
  const grd = g.createLinearGradient(0, 60, 0, 320);
  grd.addColorStop(0, "#FFF3C4"); grd.addColorStop(0.45, GOLD); grd.addColorStop(1, "#A8761C");
  let size = 220;
  g.font = `900 ${size}px ReelLook, Heebo, sans-serif`;
  const w = g.measureText(str).width;
  if (w > 940) { size = Math.floor(size * 940 / w); g.font = `900 ${size}px ReelLook, Heebo, sans-serif`; }
  g.fillStyle = grd; g.textAlign = "center"; g.textBaseline = "middle"; g.direction = /[\u0590-\u05FF]/.test(str) ? "rtl" : "ltr";
  g.shadowColor = "rgba(233,196,106,0.55)"; g.shadowBlur = 28;
  g.fillText(str, 512, 200);
  if (strikeAt !== undefined && u > strikeAt) {
    const k = ramp(u, strikeAt, 0.35, inOut);
    g.shadowColor = "rgba(255,60,40,0.7)"; g.shadowBlur = 24; g.strokeStyle = "#FF4A3A"; g.lineWidth = 22; g.lineCap = "round";
    g.beginPath(); g.moveTo(60, 290); g.lineTo(60 + 904 * k, 290 - 200 * k); g.stroke();
  }
  tex.needsUpdate = true;
  const turn = ramp(u, 0, 0.7, back);
  return (
    <group rotation={[0.08 * (1 - turn), (1 - turn) * 1.25 + Math.sin(u * 0.9) * 0.06, 0]} position={[0, 1.6, 0]} scale={0.84}>
      <mesh castShadow>
        <boxGeometry args={[5.2, 2.0, 0.42]} />
        <meshPhysicalMaterial transparent opacity={0.22} roughness={0.04} metalness={0.1} color="#cfe8de" clearcoat={1} clearcoatRoughness={0.02} envMapIntensity={2.2} depthWrite={false} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(5.2, 2.0, 0.42)]} />
        <lineBasicMaterial color={GOLD} transparent opacity={0.85} />
      </lineSegments>
      <mesh position={[0, 0, 0.23]}>
        <planeGeometry args={[5.0, 1.875]} />
        <meshBasicMaterial map={tex} transparent toneMapped={false} />
      </mesh>
    </group>
  );
};

/** a label drawn once into a canvas texture (Hebrew, gold or white) */
const labelTex = (text: string, color: string, w = 1024, h = 256) => {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d")!;
  let size = 150; g.font = `900 ${size}px ReelLook, Heebo, sans-serif`;
  const tw = g.measureText(text).width; if (tw > w * 0.86) { size = Math.floor(size * w * 0.86 / tw); g.font = `900 ${size}px ReelLook, Heebo, sans-serif`; }
  g.fillStyle = color; g.textAlign = "center"; g.textBaseline = "middle"; g.direction = "rtl";
  g.shadowColor = "rgba(0,0,0,0.5)"; g.shadowBlur = 12; g.fillText(text, w / 2, h / 2 + 6);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
};

/** the supply chain as a glass pyramid: tiers from the bottom up (the shop › the wholesaler › China), each one lands on its
 *  word (`steps`, s into the insert); the top tier glows gold */
const Pyramid: React.FC<{ u: number; tiers: string[]; steps: number[] }> = ({ u, tiers, steps }) => {
  const texs = useMemo(() => tiers.map((t, i) => labelTex(t, i === tiers.length - 1 ? "#1a1206" : "#FFFFFF")), [tiers]);
  return (
    <group position={[0, 0, 0]} rotation={[0, Math.sin(u * 0.6) * 0.12, 0]}>
      {tiers.map((_, i) => {
        const k = ramp(u, steps[i] ?? i * 1.2, 0.5, back), top = i === tiers.length - 1;
        const w = 4.8 - i * 1.4, h = 1.15, y = 0.6 + i * 1.22 + (1 - Math.min(1, k)) * 4;
        return (
          <group key={i} position={[0, y, 0]} scale={[Math.max(0.001, k), Math.max(0.001, k), Math.max(0.001, k)]}>
            <mesh castShadow>
              <boxGeometry args={[w, h, 1.9 - i * 0.45]} />
              {top ? <meshPhysicalMaterial color={GOLD} metalness={0.9} roughness={0.25} clearcoat={1} envMapIntensity={1.6} />
                : <meshPhysicalMaterial transparent opacity={0.3} color="#cfe8de" roughness={0.05} clearcoat={1} envMapIntensity={2} depthWrite={false} />}
            </mesh>
            <lineSegments>
              <edgesGeometry args={[new THREE.BoxGeometry(w, h, 1.9 - i * 0.45)]} />
              <lineBasicMaterial color={GOLD} transparent opacity={0.9} />
            </lineSegments>
            <mesh position={[0, 0, (1.9 - i * 0.45) / 2 + 0.01]}>
              <planeGeometry args={[Math.min(w * 0.95, 4.4), Math.min(w * 0.95, 4.4) / 4]} />
              <meshBasicMaterial map={texs[i]} transparent toneMapped={false} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
};

/** a trading card turning in 3D: the real card from the footage, a gold sheen across it, a slow spin that lands facing us */
const Card: React.FC<{ u: number; img: string }> = ({ u, img }) => {
  const tex = useMemo(() => { const t = new THREE.TextureLoader().load(staticFile(img)); t.colorSpace = THREE.SRGBColorSpace; return t; }, [img]);
  const spin = (1 - ramp(u, 0, 1.4, back)) * Math.PI * 2;
  return (
    <group position={[0, 2.1, 0]} rotation={[0.05, spin + Math.sin(u * 1.1) * 0.15, 0.03]}>
      <mesh castShadow>
        <boxGeometry args={[2.5, 3.5, 0.05]} />
        <meshPhysicalMaterial attach="material-4" map={tex} roughness={0.25} clearcoat={1} clearcoatRoughness={0.05} envMapIntensity={1.4} />
        <meshPhysicalMaterial attach="material-5" color="#1f3fb0" roughness={0.3} clearcoat={1} />
        <meshStandardMaterial attach="material-0" color={GOLD} metalness={1} roughness={0.2} />
        <meshStandardMaterial attach="material-1" color={GOLD} metalness={1} roughness={0.2} />
        <meshStandardMaterial attach="material-2" color={GOLD} metalness={1} roughness={0.2} />
        <meshStandardMaterial attach="material-3" color={GOLD} metalness={1} roughness={0.2} />
      </mesh>
    </group>
  );
};

const Stage: React.FC<{ u: number; children: React.ReactNode; orbit?: number }> = ({ u, children, orbit = 0.35 }) => {
  const { camera } = useThree();
  const a = -orbit + 2 * orbit * ramp(u, 0, 3.2, inOut), r = 15.5 - 1.4 * ramp(u, 0, 3.2, inOut);
  camera.position.set(Math.sin(a) * r, 3.2, Math.cos(a) * r);
  camera.lookAt(0, 0.1, 0);
  return (
    <>
      <Env />
      <ambientLight intensity={0.25} />
      <directionalLight position={[4, 9, 5]} intensity={2.2} color="#fff4dc" castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} />
      <pointLight position={[-5, 3, -3]} intensity={30} color={GOLD} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <shadowMaterial opacity={0.6} />
      </mesh>
      {children}
    </>
  );
};

/** a glass caption under the 3D object: gold headline + white sub, a light sweep across the glass */
const GlassLabel: React.FC<{ u: number; label?: string; sub?: string; y?: number; at?: number }> = ({ u, label, sub, y = 1500, at = 0.55 }) => {
  if (!label) return null;
  const p = ramp(u, at, 0.45, back), sweep = ramp(u, at + 0.2, 1.1, inOut);
  return (
    <div style={{ position: "absolute", left: 90, right: 90, top: y, display: "flex", justifyContent: "center", opacity: Math.min(1, p * 1.6),
      transform: `translateY(${(1 - p) * 50}px) scale(${0.9 + 0.1 * p})`, direction: "rtl" }}>
      <div style={{ position: "relative", overflow: "hidden", padding: "26px 54px 30px", borderRadius: 34, textAlign: "center",
        background: "linear-gradient(150deg, rgba(255,255,255,0.16), rgba(14,59,46,0.35))", border: "1.5px solid rgba(233,196,106,0.75)",
        boxShadow: "0 24px 60px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.55), 0 0 40px rgba(233,196,106,0.18)",
        backdropFilter: "blur(20px) saturate(1.3)", WebkitBackdropFilter: "blur(20px) saturate(1.3)" }}>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(110deg, transparent 35%, rgba(255,255,255,0.28) 50%, transparent 65%)",
          transform: `translateX(${(sweep * 2 - 1) * 120}%)` }} />
        <div style={{ position: "relative", fontFamily: "ReelLook, Heebo", fontWeight: 900, fontSize: 76, lineHeight: 1.05, color: GOLD,
          textShadow: "0 2px 18px rgba(233,196,106,0.45), 0 3px 8px rgba(0,0,0,0.6)", whiteSpace: "nowrap" }}>{label}</div>
        {sub && <div style={{ position: "relative", marginTop: 10, fontFamily: "ReelLook, Heebo", fontWeight: 700, fontSize: 44, color: "#fff",
          opacity: ramp(u, at + 0.3, 0.3), textShadow: "0 2px 10px rgba(0,0,0,0.6)", whiteSpace: "nowrap" }}>{sub}</div>}
      </div>
    </div>
  );
};

/** one 3D insert over the picture — a dip of 0.14 s in and out, film grain + vignette so it sits with the footage */
export const Lux: React.FC<LuxP> = (p) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < p.from - 0.01 || t > p.to + 0.01) return null;
  const u = t - p.from, dur = p.to - p.from;
  const k = Math.min(ramp(t, p.from, 0.14), 1 - ramp(t, p.to - 0.14, 0.14));
  return (
    <AbsoluteFill style={{ opacity: k, background: `radial-gradient(ellipse at 50% 38%, #123d31 0%, #06140f 55%, #020604 100%)` }}>
      <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 38, position: [0, 4.2, 15.5] }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}>
        <Stage u={u} orbit={p.kind === "containers" ? 0.35 : 0.12}>
          {p.kind === "containers" && Array.from({ length: p.count ?? 2 }, (_, i) => <Container key={i} u={u} i={i} color={i % 2 ? "#8C2F23" : "#1F5F4E"} />)}
          {p.kind === "money" && <MoneySlab u={u} dur={dur} amount={p.amount ?? 0} prefix={p.prefix ?? ""} suffix={p.suffix ?? ""} text={p.text} strikeAt={p.strikeAt} />}
          {p.kind === "pyramid" && <Pyramid u={u} tiers={p.tiers ?? []} steps={p.steps ?? []} />}
          {p.kind === "card" && p.img && <Card u={u} img={p.img} />}
        </Stage>
      </ThreeCanvas>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
      <GlassLabel u={u} label={p.label} sub={p.sub} at={p.labelAt} />
    </AbsoluteFill>
  );
};
