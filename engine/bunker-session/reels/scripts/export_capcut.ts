// The exact timelines Remotion renders → work/capcut/plan.json for capcut_reels.py (Alon 18.10.2026: "בוא ננסה לקחת את
// אותן 4 גרסאות ולבנות אותן בקאפקאט עם אותם אפקטים והכל" — so he can fix the small things himself).
// Same shots, framing, pushes, splits, reactions, caption cards, graphics, clicks — numbers from the same modules.
import fs from "node:fs";
import { loadPlans, pub, readCut, sessionArg, work } from "./session";
import { cardsOf } from "../src/cards";
import { graphicsOf } from "../src/graphics";
import { Cut, pushes, resolve, shotsOf } from "../src/timeline";

const OUTRO = 2.5; // v7: the end card is the episode poster (Alon 25.10 «המסך סיום שיהיה התמונה שלנו») — 2.5 s to read it
const S = sessionArg();
const PLANS = loadPlans(S);
const FACE = JSON.parse(fs.readFileSync(pub(S, "face.json"), "utf8"));
const reels = Object.entries(PLANS).map(([id, plan]) => {
  const cut: Cut = readCut(S, plan.file);
  const shots = shotsOf(cut, plan);
  const { skip, pills, counter } = graphicsOf(cut, plan);
  const cards = cardsOf(cut, plan, skip);
  const splits = resolve(cut, plan.split);
  const clicks: number[] = [];
  shots.forEach((s, i) => {
    const p = shots[i - 1];
    if (!p || s.end - s.at < 1.0 || s.kind === "react" || p.kind === "react") return;
    const change = p.cam !== s.cam || p.kind !== s.kind || (s.jump && Math.abs(p.z - s.z) > 0.01);
    if (change && (!clicks.length || s.at - clicks[clicks.length - 1] >= 2.0)) clicks.push(s.at);
  });
  return {
    id, title: plan.title, duration: cut.duration, outro: OUTRO,
    clips: cut.clips.map((c) => ({ at: c.at, end: c.end, src: c.src })),
    shots: shots.map((s) => ({ at: s.at, end: s.end, cam: s.cam, kind: s.kind, src: s.src, z: s.z })),
    pushes: pushes(cut, plan), splits,
    cards: cards.map((c) => ({ from: c.from, to: c.to, who: c.who, rows: c.rows.map((r) => r.map((w) => ({ text: w.text, hot: w.hot }))) })),
    pills, counter, clicks,
    logoHide: [...splits, ...(counter ? [[counter.at, counter.until]] : [])],
  };
});
fs.mkdirSync(work(S, "capcut"), { recursive: true });
fs.writeFileSync(work(S, "capcut/plan.json"), JSON.stringify({ face: FACE, reels }, null, 1));
for (const r of reels) console.log(`${r.id}: ${r.shots.length} shots · ${r.cards.length} cards · ${r.pills.length} pills${r.counter ? " · counter" : ""} · ${r.splits.length} splits · ${r.clicks.length} clicks · ${r.duration.toFixed(1)}s`);
