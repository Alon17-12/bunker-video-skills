// Every script works on ONE session: <session>/רילס/remotion/{public,work} holds its plans, cuts, media and work files.
import fs from "node:fs";
import path from "node:path";
import type { Plan } from "../src/timeline";
export const sessionArg = () => {
  const s = process.argv[2];
  if (!s || !fs.existsSync(path.join(s, "יומן.md"))) { console.error("צריך נתיב לתיקיית הסשן (עם יומן.md) כארגומנט הראשון"); process.exit(2); }
  return s;
};
export const rmDir = (s: string) => path.join(s, "רילס", "remotion");
export const pub = (s: string, f = "") => path.join(rmDir(s), "public", f);
export const work = (s: string, f = "") => path.join(rmDir(s), "work", f);
export const loadPlans = (s: string): Record<string, Plan> =>   // "_look" etc. are session settings, not reels
  Object.fromEntries(Object.entries(JSON.parse(fs.readFileSync(pub(s, "plans.json"), "utf8"))).filter(([k]) => !k.startsWith("_"))) as Record<string, Plan>;
export const readCut = (s: string, file: string) => JSON.parse(fs.readFileSync(pub(s, file), "utf8"));
