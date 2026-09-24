// How numbers, dates and times read everywhere in the console.

const nf = new Intl.NumberFormat("en-IN");

export const num = (n) => (n === null || n === undefined ? "–" : nf.format(n));

export function compact(n) {
  if (n === null || n === undefined) return "–";
  const a = Math.abs(n);
  if (a >= 1e7) return `${(n / 1e7).toFixed(a >= 1e8 ? 0 : 1)}Cr`;
  if (a >= 1e5) return `${(n / 1e5).toFixed(a >= 1e6 ? 0 : 1)}L`;
  if (a >= 1e3) return `${(n / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K`;
  return nf.format(n);
}

export const pct = (x, digits = 0) =>
  x === null || x === undefined ? "–" : `${(x * 100).toFixed(digits)}%`;

export function delta(now, prev) {
  if (!prev) return null;
  return (now - prev) / prev;
}

const toDate = (v) => (v instanceof Date ? v : new Date(v));

export function ago(value) {
  if (!value) return "never";
  const s = Math.max(0, (Date.now() - toDate(value).getTime()) / 1000);
  if (s < 45) return "just now";
  if (s < 90) return "a minute ago";
  const m = s / 60;
  if (m < 60) return `${Math.round(m)} min ago`;
  const h = m / 60;
  if (h < 24) return `${Math.round(h)} h ago`;
  const d = h / 24;
  if (d < 2) return "yesterday";
  if (d < 30) return `${Math.round(d)} days ago`;
  const mo = d / 30.4;
  if (mo < 12) return `${Math.round(mo)} mo ago`;
  return `${(d / 365).toFixed(1)} yr ago`;
}

export const date = (v, opts = { day: "numeric", month: "short", year: "numeric" }) =>
  v ? toDate(v).toLocaleDateString("en-IN", opts) : "–";

export const dateTime = (v) =>
  v ? toDate(v).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "–";

export const shortDay = (iso) => toDate(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export function ageFrom(dob) {
  if (!dob) return null;
  const d = new Date(`${dob}T00:00:00`);
  const t = new Date();
  let a = t.getFullYear() - d.getFullYear();
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a -= 1;
  return a;
}

export function greeting(now = new Date()) {
  const h = now.getHours();
  if (h < 5) return "Working late";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export const plural = (n, one, many = `${one}s`) => `${num(n)} ${n === 1 ? one : many}`;

export const titleCase = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
