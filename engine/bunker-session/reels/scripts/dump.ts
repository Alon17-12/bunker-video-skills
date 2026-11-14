// dump.ts — QA every reel before a render (tsomet-20 caption_dump + shots_dump, in one):
//  · every spoken word is on screen exactly once (caption or graphic)   · never two cards at once
//  · every word's speaker is on camera (main shots; reactions and splits are the exceptions on purpose)
//  · card list + shot list for reading
import fs from "node:fs";
import { loadPlans, readCut, sessionArg } from "./session";
import { cardsOf } from "../src/cards";
import { Cut, Word, findWord, resolve, shotsOf } from "../src/timeline";
const S = sessionArg();
const PLANS = loadPlans(S);
let bad = 0;
for (const [id, plan] of Object.entries(PLANS)) {
  const cut: Cut = readCut(S, plan.file);
  const skip = new Set<Word>();
  for (const p of plan.pills ?? []) { const w = findWord(cut, p.word)!; const i = cut.words.indexOf(w); cut.words.slice(i, i + p.n).forEach((x) => skip.add(x)); }
  if (plan.counter) for (const k of plan.counter.skip ?? [plan.counter.word]) skip.add(findWord(cut, k)!);
  const cards = cardsOf(cut, plan, skip);
  const shown = cards.flatMap((c) => c.rows.flat().map((w) => w.at));
  const drop = new Set((plan.drop ?? []).map((k) => findWord(cut, k)));
  const missing = cut.words.filter((w) => w.text && !skip.has(w) && !drop.has(w) && !shown.includes(w.at));
  const twice = shown.filter((t, i) => shown.indexOf(t) !== i);
  const overlap = cards.filter((c, i) => i && c.from < cards[i - 1].to - 1e-3);
  const shots = shotsOf(cut, plan);
  const wrong = cut.words.filter((w) => { const s = shots.find((x) => (w.at + w.end) / 2 >= x.at && (w.at + w.end) / 2 < x.end); return s && s.kind === "main" && s.cam !== (w.who === "host" ? 1 : w.who === "guest2" ? 3 : 2) && w.end - w.at > 0.12; });
  const longest = Math.max(...shots.map((s) => s.end - s.at));
  console.log(`\n## ${id} ${plan.title} — ${cut.duration.toFixed(1)}s · ${cards.length} cards · ${shots.length} shots (longest ${longest.toFixed(1)}s) · splits ${JSON.stringify(resolve(cut, plan.split).map(([a, b]) => [+a.toFixed(2), +b.toFixed(2)]))}`);
  for (const c of cards) console.log(`  ${c.from.toFixed(2)}–${c.to.toFixed(2)} ${c.who === "host" ? "H" : "G"} ${c.rows.map((r) => r.map((w) => (w.hot ? `*${w.text}*` : w.text)).join(" ")).join(" / ")}`);
  console.log("  shots: " + shots.map((s) => `${s.at.toFixed(1)} ${s.kind === "main" ? `c${s.cam}${s.z > 1.1 ? "T" : ""}` : s.kind}`).join(" | "));
  if (missing.length) { bad++; console.log("  ✗ missing:", missing.map((w) => `${w.text}@${w.at}`).join(", ")); }
  if (twice.length) { bad++; console.log("  ✗ twice:", twice); }
  if (overlap.length) { bad++; console.log("  ✗ overlap:", overlap.map((c) => c.from)); }
  if (wrong.length) { bad++; console.log("  ✗ off-face:", wrong.map((w) => `${w.text}@${w.at}(${w.who})`).join(", ")); }
}
console.log(bad ? `\n✗ ${bad} problems` : "\n✓ all reels clean");
