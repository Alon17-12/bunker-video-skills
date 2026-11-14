// render_fx.mjs <jobs.json> <out dir>: every job {name, ...FxProps} → <out>/<name>.mov (HEVC with alpha, what CapCut reads as a
// transparent clip — Remotion ProRes 4444 → avconvert, like render_gfx.mjs). publicDir = assets/fx_public (logo_round.png).
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [jobsFile, out] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsFile, "utf8"));
fs.mkdirSync(out, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(here, "..", "src", "index.ts"), publicDir: path.join(here, "..", "..", "assets", "fx_public") });
try {
  for (const j of jobs) {
    const dst = path.join(out, `${j.name}.mov`);
    if (fs.existsSync(dst) && !process.env.FORCE) { console.log("skip", j.name); continue; }
    const composition = await selectComposition({ serveUrl, id: "Fx", inputProps: j });
    const pr = path.join(out, `${j.name}.prores.mov`);
    await renderMedia({ serveUrl, composition, inputProps: j, outputLocation: pr, concurrency: 6, muted: true, timeoutInMilliseconds: 120000,
      codec: "prores", proResProfile: "4444", imageFormat: "png", pixelFormat: "yuva444p10le" });
    execFileSync("/usr/bin/avconvert", ["-s", pr, "-o", dst, "-p", "PresetHEVCHighestQualityWithAlpha", "--replace"]); fs.unlinkSync(pr);
    console.log("ok", j.name);
  }
  console.log("FX_DONE");
} finally { fs.rmSync(serveUrl, { recursive: true, force: true }); }
