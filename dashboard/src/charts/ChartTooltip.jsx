import "./charts.css";

// The one tooltip every chart uses: the value leads, the label follows.
// Positioned inside the chart's own box and kept within it.
export default function ChartTooltip({ x, y, width, value, label, sub }) {
  if (x === null || x === undefined) return null;
  const flip = x > width - 160;
  return (
    <div
      className="viz-tip"
      style={{ left: flip ? undefined : x + 12, right: flip ? width - x + 12 : undefined, top: Math.max(0, y - 10) }}
      role="presentation"
    >
      <strong className="tnum">{value}</strong>
      <span>{label}</span>
      {sub && <em>{sub}</em>}
    </div>
  );
}
