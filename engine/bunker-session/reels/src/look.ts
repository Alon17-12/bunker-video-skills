import { loadFont } from "@remotion/google-fonts/Heebo";
import { Easing, interpolate } from "remotion";

// The client's own look, from the spec (אפיון.json → landing_page.brand): the Bunker site sets every word in Heebo
// (47 uses in its live CSS), dark #09090B panels, the red→ember gradient for the one thing that matters, gold highlight.
// Alon, 17.10.2026: "שים ברילס את הפונט מהאתר" — the engine's render had fallen back to a narrow face; this loads Heebo.
const heebo = loadFont("normal", { weights: ["500", "700", "800", "900"], subsets: ["hebrew", "latin"] });
export const FONT = heebo.fontFamily;
export const fontReady = () => heebo.waitUntilDone();

export const B = {
  bg: "#09090B", panel: "#121216", text: "#F2EEEC", white: "#FFFFFF",
  red: "#D32020", accent: "#FF3B2E", ember: "#FF6A3D", gold: "#F6C453",
};
export const GRAD = `linear-gradient(100deg, ${B.red} 0%, ${B.ember} 100%)`;

// house caption colours (tsomet-20 rule 5): the host — camera 1 — gold, the guest white; one keyword per card in the accent
export const WHO_COLOR = { host: B.gold, guest: B.white } as const;

export const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
export const ease = Easing.bezier(0.22, 1, 0.36, 1);
export const inOut = Easing.bezier(0.45, 0, 0.25, 1); // CapCut FreeCurveInOut, the curve of Alon's settling zoom
export const ramp = (t: number, a: number, d: number, e: (x: number) => number = ease) =>
  interpolate(t, [a, a + d], [0, 1], { ...clamp, easing: e });

/** a real black outline as a ring of shadows — house rule since Guest J round 6 (the soft halo was unreadable on white shirts) */
export const ink = (r = 4) => Array.from({ length: 16 }, (_, i) => {
  const a = (i / 16) * Math.PI * 2;
  return `${(Math.cos(a) * r).toFixed(1)}px ${(Math.sin(a) * r).toFixed(1)}px 0 #000`;
}).join(", ");
export const outline = `${ink(4.5)}, 0 6px 16px rgba(0,0,0,0.55)`;
