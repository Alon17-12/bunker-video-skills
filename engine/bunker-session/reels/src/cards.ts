// Caption cards in the house grammar (hakapitan + tsomet-20 rechunk_cards rules):
// a card is one phrase of 2–4 words, ≤ 2 rows; it never runs across a sentence end or a change of speaker; no orphan
// word unless it is a whole sentence ("וואו."); a card shorter than 0.5 s merges into its neighbour; never two cards
// at once; every spoken word is on screen exactly once (words shown by a graphic are skipped).
import { Cut, Plan, Word, findWord } from "./timeline";

export type CWord = { text: string; at: number; hot: boolean };
export type Card = { from: number; to: number; who: "host" | "guest"; rows: CWord[][] };

const MAX_WORDS = 4, MAX_CHARS = 22, ONE_ROW = 18;   // ≤ 18 characters = one row (≈ 70 % of the frame in Bamberger at his caption size; wrap is at 82 %)
const endsSentence = (s: string) => /[.?!]$/.test(s);
// a comma ends the card (לקוח A 20.10: «החלוקה של הטקסט לא נכונה») — except after a lone address/tag word that
// belongs with what follows ("תשמע, אחי," / "וואלה, אחי,"); a single orphan left behind merges back below
const TAG = /^(תשמע|שמע|אחי|וואלה|ואללה|בני|נשמה|אוקיי|כאילו|יפה|נכון|בסדר|כן),$/;
// pairs that must stay on one card (number + unit, "בדרך כלל", "כל כך"…)
const BOND = [/^\d+$/, /^(כל|בדרך|לבן|הכי|אח|על|בתור)$/];
// a card never ends on a word that leans on the next one ("אוהב את | המצלמה", "שאני מול | מצלמה")
const LEAN = /^(את|של|עם|מול|על|אל|כי|אבל|ו?אני|זה|לא|יש|אין|בין|לבין|או|גם|כל|הכי|מה|איך|שאני|כשאני|אחד|ה|ב|ל|מ|ש|ו)$/;

export const cardsOf = (cut: Cut, plan: Plan, skip: Set<Word>): Card[] => {
  const keyOf = (w: Word) => { const same = cut.words.filter((x) => x.text === w.text); return `${w.text}#${same.indexOf(w)}`; };
  const fix = (w: Word) => plan.fix?.[keyOf(w)] ?? plan.fix?.[w.text] ?? w.text;
  const hotSet = new Set((plan.hot ?? []).map((k) => findWord(cut, k)).filter(Boolean) as Word[]);
  const drop = new Set((plan.drop ?? []).map((k) => findWord(cut, k)).filter(Boolean) as Word[]);
  const s0 = plan.solo ? findWord(cut, plan.solo[0])?.at ?? 1e9 : 1e9, s1 = plan.solo?.[1] ? findWord(cut, plan.solo[1])?.at ?? 1e9 : 1e9;
  const solo = (w: Word) => w.at >= s0 - 1e-3 && w.at <= s1 + 1e-3;
  const brk = new Set((plan.breaks ?? []).map((k) => findWord(cut, k)).filter(Boolean) as Word[]);
  const groups: Word[][] = [];
  let g: Word[] = [];
  const flush = () => { if (g.length) groups.push(g); g = []; };
  if (plan.cards) {
    const ws = cut.words.filter((w) => fix(w) && !skip.has(w) && !drop.has(w));
    let i = 0;
    for (const n of plan.cards) { groups.push(ws.slice(i, i + n)); i += n; }
    if (i !== ws.length) throw new Error(`${plan.title}: hand cards cover ${i} of ${ws.length} words`);
  }
  for (const w of plan.cards ? [] : cut.words) {
    if (skip.has(w) || drop.has(w) || !fix(w)) { flush(); continue; }
    if (solo(w)) { flush(); g.push(w); flush(); continue; }
    if (brk.has(w)) flush();
    const prev = g[g.length - 1];
    const len = g.reduce((a, x) => a + fix(x).length + 1, 0) + fix(w).length;
    // the hook copy never shares a card with the reel that follows it (אלון+אייל+דולב v6: «…600 לידים קודם כל»)
    const hk = (plan as { hook?: number }).hook;
    if (prev && hk != null && prev.at < hk - 0.05 && w.at >= hk - 0.05) flush();
    const prev2 = g[g.length - 1];
    if (prev2 && (prev2.who !== w.who || prev2.clip !== w.clip && w.at - prev2.end > 0.6 || endsSentence(fix(prev2))
      || ((g.length >= MAX_WORDS || len > MAX_CHARS) && !(LEAN.test(fix(prev2)) && g.length < 6 && len <= 30)) || (/,$/.test(fix(prev2)) && !(g.length === 1 && TAG.test(fix(prev2))) && !BOND.some((r) => r.test(fix(prev2).replace(/,$/, "")))))) flush();
    g.push(w);
  }
  flush();
  const closes = (ws: Word[]) => /,$/.test(fix(ws[ws.length - 1])) && !TAG.test(fix(ws[ws.length - 1]));
  // orphans: a lone word that is not a sentence of its own joins the next card of the same speaker (or the previous)
  for (let i = 0; i < (plan.cards ? 0 : groups.length); i++) {
    const c = groups[i];
    if (solo(c[0])) continue;
    const n0 = groups[i + 1], p0 = groups[i - 1];
    const n = n0 && !brk.has(n0[0]) ? n0 : undefined, p = p0 && !brk.has(c[0]) ? p0 : undefined;
    // a one-word card stands only as a sentence of its own ("וואו.") — "…הוא עולם | בודד." is an orphan
    const alone = endsSentence(fix(c[0])) && (!p || p[p.length - 1].who !== c[0].who || endsSentence(fix(p[p.length - 1])));
    if (c.length !== 1 || alone) continue;
    // a word that closes a phrase with a comma goes back to the phrase it closes ("על היומן | שלך," → "על היומן שלך,")
    if (closes(c) && p && p[p.length - 1].who === c[0].who && !endsSentence(fix(p[p.length - 1])) && p.length < MAX_WORDS + 1) { p.push(c[0]); groups.splice(i, 1); i--; continue; }
    if (!endsSentence(fix(c[0])) && n && n[0].who === c[0].who && n.length < MAX_WORDS + 1 && n[0].at - c[0].end < 0.6) { groups[i + 1] = [...c, ...n]; groups.splice(i, 1); i--; }
    else if (p && p[p.length - 1].who === c[0].who && !endsSentence(fix(p[p.length - 1])) && p.length < MAX_WORDS + 1) { p.push(c[0]); groups.splice(i, 1); i--; }
  }
  // a card under 0.5 s on screen merges into its neighbour of the same speaker (≤ 6 words, two rows)
  const span = (ws: Word[]) => ws[ws.length - 1].end - ws[0].at + 0.3;
  for (let i = 0; i < (plan.cards ? 0 : groups.length); i++) {
    const c = groups[i];
    if (span(c) >= 0.5 || solo(c[0])) continue;
    const n0 = groups[i + 1], p0 = groups[i - 1];
    const n = n0 && !brk.has(n0[0]) ? n0 : undefined, p = p0 && !brk.has(c[0]) ? p0 : undefined;
    if (closes(c) && p && p[p.length - 1].who === c[0].who && !endsSentence(fix(p[p.length - 1])) && p.length + c.length <= 6) { p.push(...c); groups.splice(i, 1); i--; continue; }
    if (n && n[0].who === c[0].who && !endsSentence(fix(c[c.length - 1])) && c.length + n.length <= 6) { groups[i + 1] = [...c, ...n]; groups.splice(i, 1); i--; }
    else if (p && p[p.length - 1].who === c[0].who && !endsSentence(fix(p[p.length - 1])) && p.length + c.length <= 6) { p.push(...c); groups.splice(i, 1); i--; }
  }
  const cards: Card[] = groups.map((ws) => {
    const cw = ws.map((w) => ({ text: fix(w), at: w.at, hot: hotSet.has(w) }));
    const text = cw.map((x) => x.text).join(" ");
    let rows: CWord[][] = [cw];
    // one row whenever it fits; two rows only when it does not, split by WORD count first (2|2, never 3|1), characters as
    // the tie-break (לקוח A 20.10: «פיצלת בלי סיבה ל-2 שורות… 2 מילים בכל שורה במקום 3 בשורה הראשונה ו-1 בשנייה»)
    if (text.length > ONE_ROW && cw.length > 1) {
      let best = 1, bd = [1e9, 1e9];
      for (let k = 1; k < cw.length; k++) {
        const a = cw.slice(0, k).map((x) => x.text).join(" ").length, b = cw.slice(k).map((x) => x.text).join(" ").length;
        const d = [Math.abs(k - (cw.length - k)), Math.abs(a - b)];
        if (d[0] < bd[0] || (d[0] === bd[0] && d[1] < bd[1])) { bd = d; best = k; }
      }
      rows = [cw.slice(0, best), cw.slice(best)];
    }
    return { from: ws[0].at - 0.05, to: ws[ws.length - 1].end + 0.35, who: ws[0].who, rows };
  });
  for (let i = 0; i + 1 < cards.length; i++) cards[i].to = Math.min(cards[i].to, cards[i + 1].from - 0.02);
  return cards;
};
