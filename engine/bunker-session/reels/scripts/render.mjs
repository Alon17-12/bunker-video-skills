// render.mjs <session> v<N> [r1,r2,…] [scale] → <session>/רילס/remotion/out/<id>-v<N>.mp4 (4K at scale 2) → loudnorm −14 LUFS
// → a copy in the reel's own folder <session>/רילס/<NN - title>/remotion-v<N>.mp4 (titles from רילס/רילס.json)
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { ENTRY, sessionArg } from "./sessionArg.mjs";
import { reelDir } from "./reelDir.mjs";
const { S, PUB, OUT } = sessionArg();
const [, , , ver, only, scale = "2"] = process.argv;
const plans = JSON.parse(fs.readFileSync(path.join(PUB, "plans.json"), "utf8"));
const picks = JSON.parse(fs.readFileSync(path.join(S, "רילס", "רילס.json"), "utf8"));
const dirOf = (id) => reelDir(picks, id);
const ids = only ? only.split(",") : Object.keys(plans);
fs.mkdirSync(OUT, { recursive: true });
// WebGL for the 3D inserts (lux.tsx) — ANGLE, not the default SwiftShader
const chromiumOptions = { gl: "angle" };
const serveUrl = await bundle({ entryPoint: ENTRY, publicDir: PUB });
try {
  for (const id of ids) {
    const t0 = Date.now();
    // the reel's sound is a file built from its cut (mk_audio.py) — older than the cut means the picture drifts off the voice from
    // the moved edge on (יירום v5, 29.10.2026). Stop rather than render it.
    const wav = path.join(PUB, "a", `${id}.wav`), cutF = path.join(PUB, plans[id].file ?? `${id}.json`);
    if (fs.existsSync(wav) && fs.statSync(wav).mtimeMs < fs.statSync(cutF).mtimeMs)
      throw new Error(`${id}: a/${id}.wav is older than ${path.basename(cutF)} — run mk_audio.py <session> ${id} first`);
    // FINAL=1: the approved render — no review stamp (reel number + clock) whatever the session's _look says
    const inputProps = process.env.FINAL ? { id, music: true, review: false } : { id, music: true };
    const composition = await selectComposition({ serveUrl, id, inputProps, chromiumOptions });
    const raw = path.join(OUT, `${id}-${ver}.raw.mp4`), out = path.join(OUT, `${id}-${ver}.mp4`);
    // yuv420p · tv range · bt709 — the default came out yuvj420p / pc / bt470bg, against Alon's 18.10 delivery rule (מייקי found it
    // on every engine final 29.10.2026 and re-encoded the scheduled ones by hand)
    const base = { serveUrl, composition, inputProps, scale: Number(scale), crf: 18, concurrency: 6, timeoutInMilliseconds: 120000, chromiumOptions, pixelFormat: "yuv420p", colorSpace: "bt709" };
    // CHUNK=<frames>: picture in chunks, each retried on its own, then the sound once — Chrome drops localhost fetches on
    // net::ERR_NETWORK_CHANGED when the network flaps, and a 60 s reel then never got through in one piece (28.10.2026)
    const CH = Number(process.env.CHUNK || 0);
    const retry = async (fn, what) => { for (let k = 0; ; k++) { try { return await fn(); } catch (e) { if (k >= 6) throw e; console.error(`retry ${what} (${k + 1})`); } } };
    if (!CH) await renderMedia({ ...base, codec: "h264", outputLocation: raw });
    else {
      const parts = [], N = composition.durationInFrames;
      for (let a = 0; a < N; a += CH) {
        const part = raw.replace(/\.raw\.mp4$/, `.p${a}.mp4`);
        if (!fs.existsSync(part)) await retry(async () => { await renderMedia({ ...base, codec: "h264", muted: true, frameRange: [a, Math.min(N - 1, a + CH - 1)], outputLocation: part + ".tmp.mp4" }); fs.renameSync(part + ".tmp.mp4", part); }, `${id} ${a}`);   // a finished chunk is kept for the next run
        parts.push(part);
      }
      const wav = raw.replace(/\.raw\.mp4$/, ".wav"), list = raw.replace(/\.raw\.mp4$/, ".txt");
      const { crf: _c, scale: _s, pixelFormat: _p, colorSpace: _cs, ...aud } = base;   // the sound pass takes no picture options
      await retry(() => renderMedia({ ...aud, codec: "wav", outputLocation: wav }), `${id} audio`);
      fs.writeFileSync(list, parts.map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join("\n"));
      const cat = spawnSync(path.join((process.env.HOME || process.env.USERPROFILE), "ffmpeg-bin/ffmpeg"), ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-i", wav,
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le", raw.replace(/\.mp4$/, ".mov")]);
      if (cat.status !== 0) throw new Error(cat.stderr.toString());
      fs.renameSync(raw.replace(/\.mp4$/, ".mov"), raw);
      [...parts, wav, list].forEach((f) => fs.rmSync(f, { force: true }));
    }
    const ff = spawnSync(path.join((process.env.HOME || process.env.USERPROFILE), "ffmpeg-bin/ffmpeg"), ["-v", "error", "-y", "-i", raw, "-c:v", "copy", "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "256k", out]);
    if (ff.status !== 0) throw new Error(ff.stderr.toString());
    fs.unlinkSync(raw);
    const probe = spawnSync(path.join((process.env.HOME || process.env.USERPROFILE), "ffmpeg-bin/ffprobe"), ["-v", "error", "-select_streams", "v", "-show_entries", "stream=pix_fmt,color_range,color_space,color_primaries,color_transfer", "-of", "csv=p=0", out]).stdout.toString().trim().replace(/,+$/, "");
    if (probe !== "yuv420p,tv,bt709,bt709,bt709") throw new Error(`${id}: ${out} is ${probe}, not yuv420p · tv · bt709 — not delivered`);
    const dir = path.join(S, "רילס", dirOf(id));
    fs.mkdirSync(dir, { recursive: true });
    fs.copyFileSync(out, path.join(dir, `remotion-${ver}.mp4`));
    console.log(`${id} ${ver} → ${dir}/remotion-${ver}.mp4 · ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
} finally {
  // every bundle copies public/ (~1.4 GB) into $TMPDIR — removed on success AND failure (ENOSPC on 17.10.2026)
  fs.rmSync(serveUrl, { recursive: true, force: true });
}
