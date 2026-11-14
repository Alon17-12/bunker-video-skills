import { Cut, Plan, Word, findWord, resolve } from "./timeline";

/** the reel's brand graphics and the spoken words they show (the caption skips them) — shared with the CapCut export */
export const graphicsOf = (cut: Cut, plan: Plan) => {
  const skip = new Set<Word>();
  const pills = (plan.pills ?? []).map((p) => {
    const w = findWord(cut, p.word);
    if (!w) return null;
    const i = cut.words.indexOf(w), ws = cut.words.slice(i, i + p.n);
    ws.forEach((x) => skip.add(x));
    const text = ws.map((x) => plan.fix?.[x.text] ?? x.text).join(" ").replace(/[.,?!]/g, "");
    let until = Math.max(ws[ws.length - 1].end + 0.6, w.at + (p.hold ?? 1.8));
    for (const [a] of resolve(cut, plan.split)) if (a > w.at && a < until) until = a - 0.05; // a pill never sits over the split's top face
    return { at: w.at - 0.05, until, text };
  }).filter(Boolean) as { at: number; until: number; text: string }[];
  let counter: { at: number; until: number; to: number; suffix?: string; label?: string } | null = null;
  if (plan.counter) {
    const w = findWord(cut, plan.counter.word);
    if (w) {
      counter = { at: w.at, until: w.at + (plan.counter.hold ?? 2.2), to: plan.counter.to, suffix: plan.counter.suffix, label: plan.counter.label };
      for (const k of plan.counter.skip ?? [plan.counter.word]) { const x = findWord(cut, k); if (x) skip.add(x); }
    }
  }
  return { skip, pills, counter };
};

