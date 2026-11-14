// render_gfx.mjs <session>: every pill / counter of <session>/רילס/remotion/work/capcut/plan.json → work/capcut/gfx/<reel>_<n>.mov (HEVC with alpha, the format CapCut reads
// as a transparent clip — Remotion ProRes 4444 → macOS avconvert); the end card → work/capcut/gfx/outro.mp4
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { ENTRY, sessionArg } from "./sessionArg.mjs";
const { PUB, WORK } = sessionArg();
const plan = JSON.parse(fs.readFileSync(path.join(WORK, "capcut/plan.json"), "utf8"));
const out = path.join(WORK, "capcut/gfx");
fs.mkdirSync(out, { recursive: true });
const serveUrl = await bundle({ entryPoint: ENTRY, publicDir: PUB });
try {
  const job = async (name, props, alpha) => {
    const composition = await selectComposition({ serveUrl, id: "Gfx", inputProps: props });
    const file = path.join(out, alpha ? `${name}.prores.mov` : `${name}.mp4`);
    await renderMedia({ serveUrl, composition, inputProps: props, outputLocation: file, concurrency: 6, timeoutInMilliseconds: 120000, muted: true,
      ...(alpha ? { codec: "prores", proResProfile: "4444", imageFormat: "png", pixelFormat: "yuva444p10le" } : { codec: "h264", crf: 16 }) });
    if (alpha) { execFileSync("/usr/bin/avconvert", ["-s", file, "-o", path.join(out, `${name}.mov`), "-p", "PresetHEVCHighestQualityWithAlpha", "--replace"]); fs.unlinkSync(file); }
    console.log("ok", name);
  };
  for (const r of plan.reels) {
    for (const [i, p] of r.pills.entries()) await job(`${r.id}_pill${i}`, { kind: "pill", text: p.text, dur: p.until - p.at + 0.3 }, true);
    if (r.counter) await job(`${r.id}_counter`, { kind: "counter", to: r.counter.to, suffix: r.counter.suffix, dur: r.counter.until - r.counter.at + 0.3 }, true);
  }
  await job("outro", { kind: "outro", dur: 1.6 }, false);
  console.log("GFX_DONE");
} finally {
  // every bundle copies public/ (~1.4 GB) into $TMPDIR — removed on success AND failure (ENOSPC on 17.10.2026)
  fs.rmSync(serveUrl, { recursive: true, force: true });
}
