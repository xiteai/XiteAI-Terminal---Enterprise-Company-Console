import "./charts.css";

// A small trend for a stat tile: quiet line, the latest point in ember.
export default function Sparkline({ values, width = 96, height = 28 }) {
  if (!values?.length) return null;
  const max = Math.max(1, ...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const x = (i) => (i / Math.max(1, values.length - 1)) * (width - 6) + 3;
  const y = (v) => height - 4 - ((v - min) / span) * (height - 8);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const lx = x(values.length - 1);
  const ly = y(values[values.length - 1]);
  return (
    <svg className="spark" width={width} height={height} aria-hidden>
      <path d={d} className="spark-line" />
      <circle cx={lx} cy={ly} r={3.2} className="viz-dot" />
    </svg>
  );
}
