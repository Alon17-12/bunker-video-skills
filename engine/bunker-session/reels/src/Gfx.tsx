import React from "react";
import { AbsoluteFill } from "remotion";
import { Counter, Outro, Pill } from "./Reel";

// One brand graphic alone, from frame 0, for the CapCut build: a pill / the counter on transparent (→ HEVC with alpha),
// or the end card (opaque). The same components as the reels, so the look is identical.
export type GfxProps = { kind: "pill" | "counter" | "outro"; text?: string; to?: number; suffix?: string; dur: number };
export const Gfx: React.FC<GfxProps> = ({ kind, text = "", to = 0, suffix, dur }) => (
  <AbsoluteFill style={{ background: "transparent" }}>
    {kind === "pill" && <Pill at={0.05} until={dur - 0.3} text={text} />}
    {kind === "counter" && <Counter at={0} until={dur - 0.3} to={to} suffix={suffix} />}
    {kind === "outro" && <Outro at={0} />}
  </AbsoluteFill>
);
