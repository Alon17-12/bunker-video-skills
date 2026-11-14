// the session folder every render script works on (first argument) — data in <session>/רילס/remotion/{public,work}
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
export const sessionArg = () => {
  const s = process.argv[2];
  if (!s || !fs.existsSync(path.join(s, "יומן.md"))) { console.error("צריך נתיב לתיקיית הסשן (עם יומן.md) כארגומנט הראשון"); process.exit(2); }
  const RM = path.join(s, "רילס", "remotion");
  return { S: s, RM, PUB: path.join(RM, "public"), WORK: path.join(RM, "work"), OUT: path.join(RM, "out") };
};
// the Remotion entry, resolved from this file — the scripts run from the repo root (SKILL.md), not from reels/
export const ENTRY = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "index.ts");
