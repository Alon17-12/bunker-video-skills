// stills.mjs <session> <comp> "t1,t2,…" [scale] → <session>/רילס/remotion/out/stills/<comp>-<t>.jpg (one bundle, many frames)
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { ENTRY, sessionArg } from "./sessionArg.mjs";
const { PUB, OUT } = sessionArg();
const [, , , comp, times, scale = "0.5"] = process.argv;
// WebGL for the 3D inserts (lux.tsx) — ANGLE, not the default SwiftShader
const chromiumOptions = { gl: "angle" };
const serveUrl = await bundle({ entryPoint: ENTRY, publicDir: PUB });
try {
  const c = await selectComposition({ serveUrl, id: comp, chromiumOptions });
  fs.mkdirSync(path.join(OUT, "stills"), { recursive: true });
  for (const t of times.split(",").map(Number)) {
    const f = Math.min(c.durationInFrames - 1, Math.round(t * 30));
    await renderStill({ serveUrl, composition: c, frame: f, output: path.join(OUT, "stills", `${comp}-${t.toFixed(2)}.jpg`), imageFormat: "jpeg", scale: Number(scale), timeoutInMilliseconds: 120000, chromiumOptions });
    console.log("still", comp, t);
  }
} finally {
  // every bundle copies public/ (~1.4 GB) into $TMPDIR — removed on success AND failure (ENOSPC on 17.10.2026)
  fs.rmSync(serveUrl, { recursive: true, force: true });
}
