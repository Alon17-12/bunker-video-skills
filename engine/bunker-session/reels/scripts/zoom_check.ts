// zoom_check.ts <session> [rN] — every edit where the picture's size jumps without the camera changing (עומר 12.11.2026:
// «קפיצות זומים שבורות»): a jump cut that flips wide↔tight, a push cut off before it settles, a reaction push that snaps back.
// The zoom math mirrors zoomFn in src/Reel.tsx (push / close / react; punch is not used here).
import fs from "node:fs";
import path from "node:path";
import { Cut, Plan, findWord, shotsOf, pushes } from "../src/timeline";
const S = process.argv[2], PUB = path.join(S, "רילס", "remotion", "public");
const plans = JSON.parse(fs.readFileSync(path.join(PUB, "plans.json"), "utf8"));
const ids = process.argv[3] ? [process.argv[3]] : Object.keys(plans).filter((k) => !k.startsWith("_"));
const ramp = (t: number, a: number, d: number) => { const x = Math.min(1, Math.max(0, (t - a) / d)); return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; };
let bad = 0;
for (const id of ids) {
  const plan = plans[id] as Plan & { pushSoft?: boolean; close?: string[] };
  const cut = JSON.parse(fs.readFileSync(path.join(PUB, plan.file), "utf8")) as Cut;
  const shots = shotsOf(cut, plan), push = pushes(cut, plan), soft = !!plan.pushSoft;
  const close = (plan.close ?? []).map((k) => findWord(cut, k)?.at ?? -1).filter((t) => t > 0);
  const z = (s: (typeof shots)[0], u: number) => {
    const t = s.at + u; let v = s.z;
    if (s.kind === "react") return v * (1 + 0.06 * Math.min(1, u / Math.max(0.6, s.end - s.at)));
    if (s.kind === "split") return 1;
    for (const p of push) { const k = (s.z > 1.1 ? 0.07 : 0.14) * (soft ? 0.6 : 1), up = soft ? 1.3 : 0.7;
      if (t > p - up && p - up >= s.at - 0.05) v += k * ramp(t, p - up, up) * (1 - ramp(t, p + 1.1, soft ? 1.6 : 0.9)); }
    for (const p of close) if (t > p - 0.6) v += 0.32 * ramp(t, p - 0.6, 0.8);
    return v * (1 + 0.006 * (t - ((s as { run0?: number }).run0 ?? s.at)));
  };
  const mix = (t: number) => (plan.mix ?? []).some((x) => Math.abs(x - t) < 0.06);
  for (let i = 1; i < shots.length; i++) {
    const a = shots[i - 1], b = shots[i];
    if (a.cam !== b.cam || a.kind !== b.kind || a.kind === "split") continue;   // a camera/layout change hides a size change
    const za = z(a, a.end - a.at - 1 / 30), zb = z(b, 0), d = Math.abs(zb / za - 1);
    if (d > 0.012) { bad++; console.log(`  ✗ ${id} ${b.at.toFixed(2)}s cam ${b.cam}: ${za.toFixed(3)} → ${zb.toFixed(3)} (${(d * 100).toFixed(1)}%)${mix(b.at) ? " [mix]" : ""}`); }
  }
  console.log(`${id}: ${shots.length} shots checked`);
}
console.log(bad ? `✗ ${bad} zoom jumps` : "✓ no zoom jumps");
