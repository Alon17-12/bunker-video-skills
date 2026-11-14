import { staticFile } from "remotion";
import { Plan } from "./timeline";

// One session per bundle: the render scripts bundle with publicDir = <session>/רילס/remotion/public, so the plans, the
// graded-selects map and the face positions are DATA of that session — nothing session-specific lives in src/.
export type Sel = { from: number; to: number; at: number };
export type Face = Record<"1" | "2", { x: number; y: number }>;
export type SessionData = { plans: Record<string, Plan>; sel: Sel[]; face: Face };
let cache: Promise<SessionData> | null = null;
const j = (f: string) => fetch(staticFile(f)).then((r) => { if (!r.ok) throw new Error(`חסר ${f} בתיקיית הסשן`); return r.json(); });
export const loadSession = () =>
  (cache ??= Promise.all([j("plans.json"), j("selects.json"), j("face.json")]).then(([plans, sel, face]) => ({ plans, sel, face })));
export const selOf = (sel: Sel[]) => (t: number) => {
  const w = sel.find((x) => t >= x.from - 0.001 && t <= x.to + 0.001);
  if (!w) throw new Error(`source ${t.toFixed(2)} is not in the graded selects — re-run grade_windows.py`);
  return w.at + (t - w.from);
};
