// Scales and ticks: clean round numbers on the axis, never 0, 137, 274.

export function niceStep(range, count) {
  const raw = range / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const n = raw / mag;
  const step = n >= 5 ? 10 : n >= 2 ? 5 : n >= 1 ? 2 : 1;
  return step * mag;
}

export function niceTicks(max, count = 4) {
  if (!max || max <= 0) return [0, 1];
  const step = niceStep(max, count);
  const top = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = 0; v <= top + step / 2; v += step) ticks.push(Math.round(v * 1e6) / 1e6);
  return ticks;
}

export const linear = (d0, d1, r0, r1) => (v) => (d1 === d0 ? r0 : r0 + ((v - d0) / (d1 - d0)) * (r1 - r0));

export const tickLabel = (v) => new Intl.NumberFormat("en-IN").format(v);
