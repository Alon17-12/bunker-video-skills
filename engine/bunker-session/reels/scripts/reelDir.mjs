// r3 → «03 - <title>» by the pick's own number n — never by its position (a dropped pick shifts positions)
export const reelDir = (picks, id) => {
  const n = Number(String(id).replace(/^r/, ""));
  const p = picks.find((x) => Number(x.n) === n);
  if (!p) throw new Error(`אין בחירה מספר ${n} ב-רילס/רילס.json`);
  return `${String(n).padStart(2, "0")} - ${p.title}`;
};
