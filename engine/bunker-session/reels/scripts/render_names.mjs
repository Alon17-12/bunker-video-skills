// render_names.mjs <jobs.json> <out dir> [--stills]: every job {name (file), text, sub?, side?, dur} → <out>/<file>.mov,
// the NameGlass plate on transparent 1920×1080 (ProRes 4444 → avconvert HEVC with alpha, what CapCut reads as transparent).
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [jobsFile, out, flag] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsFile, "utf8"));
fs.mkdirSync(out, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(here, "..", "src", "index.ts"), publicDir: path.join(here, "..", "..", "assets", "fx_public") });
try {
  for (const j of jobs) {
    const props = { name: j.text, sub: j.sub, side: j.side, dur: j.dur };
    const composition = await selectComposition({ serveUrl, id: "NameGlass", inputProps: props });
    if (flag === "--stills") {
      for (const s of [0.4, 1.0, 2.5]) await renderStill({ serveUrl, composition, inputProps: props, frame: Math.round(s * 30), imageFormat: "png", output: path.join(out, `${j.name}-${s}.png`) });
      continue;
    }
    const dst = path.join(out, `${j.name}.mov`), pr = path.join(out, `${j.name}.prores.mov`);
    await renderMedia({ serveUrl, composition, inputProps: props, outputLocation: pr, concurrency: 6, muted: true, timeoutInMilliseconds: 120000,
      codec: "prores", proResProfile: "4444", imageFormat: "png", pixelFormat: "yuva444p10le" });
    // CapCut reads HEVC alpha as PREMULTIPLIED: straight colours on a half-transparent glass were added over the picture and
    // blew it out to white (נאווה בויום 11.11.2026, the exported name plate). Premultiply before the HEVC encode.
    const pm = path.join(out, `${j.name}.pm.mov`);
    execFileSync(path.join(process.env.HOME, "ffmpeg-bin/ffmpeg"), ["-v", "error", "-y", "-i", pr, "-vf", "format=gbrap10le,premultiply=inplace=1",
      "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", pm]);
    execFileSync("/usr/bin/avconvert", ["-s", pm, "-o", dst, "-p", "PresetHEVCHighestQualityWithAlpha", "--replace"]); fs.unlinkSync(pr); fs.unlinkSync(pm);
    console.log("ok", j.name);
  }
  console.log("NAMES_DONE");
} finally { fs.rmSync(serveUrl, { recursive: true, force: true }); }
