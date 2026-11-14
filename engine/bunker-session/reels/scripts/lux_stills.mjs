// lux_stills.mjs <outDir> '<props json>' "t1,t2" — stills of one 3D insert alone (no session needed), WebGL through ANGLE
import { bundle } from "@remotion/bundler";
import { renderStill, renderMedia, selectComposition } from "@remotion/renderer";
import fs from "node:fs"; import path from "node:path"; import os from "node:os";
const [, , out, props, times, video] = process.argv;
const pub = fs.mkdtempSync(path.join(os.tmpdir(), "luxpub-"));
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: pub });
const inputProps = JSON.parse(props);
const chromiumOptions = { gl: "angle" };
try {
  const c = await selectComposition({ serveUrl, id: "Lux", inputProps, chromiumOptions });
  fs.mkdirSync(out, { recursive: true });
  if (video) await renderMedia({ serveUrl, composition: c, inputProps, codec: "h264", outputLocation: path.join(out, `${inputProps.kind}.mp4`), chromiumOptions, concurrency: 4 });
  else for (const t of times.split(",").map(Number)) {
    await renderStill({ serveUrl, composition: c, inputProps, frame: Math.min(c.durationInFrames - 1, Math.round(t * 30)), output: path.join(out, `${inputProps.kind}-${t}.jpg`), imageFormat: "jpeg", scale: 0.5, chromiumOptions });
    console.log("still", t);
  }
} finally { fs.rmSync(serveUrl, { recursive: true, force: true }); fs.rmSync(pub, { recursive: true, force: true }); }
