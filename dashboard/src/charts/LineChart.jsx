import { useMemo, useState } from "react";
import { motion } from "../lib/motion.js";
import { shortDay } from "../lib/format.js";
import ChartTooltip from "./ChartTooltip.jsx";
import { linear, niceTicks, tickLabel } from "./scale.js";
import { useWidth } from "./useSize.js";
import "./charts.css";

// One series over time: a thin line, a faint wash below it, a dot at the
// latest point with its value, and a crosshair that snaps to the nearest day.
// points: [{date: "YYYY-MM-DD", value}]
export default function LineChart({ points, height = 220, label = "Value", format = tickLabel }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);
  const pad = { top: 16, right: 44, bottom: 28, left: 36 };
  const w = Math.max(120, width - pad.left - pad.right);
  const h = height - pad.top - pad.bottom;

  const geo = useMemo(() => {
    const max = Math.max(1, ...points.map((p) => p.value));
    const ticks = niceTicks(max, 4);
    const x = linear(0, Math.max(1, points.length - 1), 0, w);
    const y = linear(0, ticks[ticks.length - 1], h, 0);
    const pts = points.map((p, i) => [x(i), y(p.value)]);
    const line = pts.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join("");
    const area = pts.length ? `${line}L${pts[pts.length - 1][0].toFixed(1)},${h}L0,${h}Z` : "";
    // Date labels: evenly spaced, the latest day always shown, never crowding it.
    const every = Math.max(1, Math.ceil(points.length / Math.max(2, Math.floor(w / 90))));
    const labels = [];
    for (let i = 0; i < points.length; i += every) labels.push(i);
    const lastIdx = points.length - 1;
    if (lastIdx > 0 && labels[labels.length - 1] !== lastIdx) {
      if (lastIdx - labels[labels.length - 1] < every * 0.6) labels.pop();
      labels.push(lastIdx);
    }
    return { ticks, x, y, pts, line, area, labels };
  }, [points, w, h]);

  const onMove = (e) => {
    const box = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - box.left - pad.left;
    const i = Math.round((px / w) * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, i)));
  };
  const onKey = (e) => {
    if (e.key === "ArrowRight") setHover((i) => Math.min(points.length - 1, (i ?? -1) + 1));
    if (e.key === "ArrowLeft") setHover((i) => Math.max(0, (i ?? points.length) - 1));
  };

  const last = geo.pts[geo.pts.length - 1];
  const hp = hover !== null ? geo.pts[hover] : null;

  return (
    <div className="viz" ref={ref} style={{ height }}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label}, daily`}
        tabIndex={0}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        onKeyDown={onKey}
        onBlur={() => setHover(null)}
      >
        <g transform={`translate(${pad.left},${pad.top})`}>
          {geo.ticks.map((t) => (
            <g key={t} transform={`translate(0,${geo.y(t)})`}>
              <line x1={0} x2={w} className={t === 0 ? "viz-base" : "viz-grid"} />
              <text x={-10} dy="0.32em" textAnchor="end" className="viz-tick tnum">{tickLabel(t)}</text>
            </g>
          ))}
          {geo.labels.map((i) => (
            <text key={points[i].date} x={geo.x(i)} y={h + 18} textAnchor="middle" className="viz-tick">
              {shortDay(points[i].date)}
            </text>
          ))}
          <motion.path
            d={geo.area}
            className="viz-area"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.25 }}
          />
          <motion.path
            d={geo.line}
            className="viz-line"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          />
          {last && (
            <g>
              <circle cx={last[0]} cy={last[1]} r={6} className="viz-ring" />
              <circle cx={last[0]} cy={last[1]} r={3.5} className="viz-dot" />
              <text x={last[0] + 10} y={last[1]} dy="0.32em" className="viz-endlabel tnum">
                {format(points[points.length - 1].value)}
              </text>
            </g>
          )}
          {hp && (
            <g pointerEvents="none">
              <line x1={hp[0]} x2={hp[0]} y1={0} y2={h} className="viz-cross" />
              <circle cx={hp[0]} cy={hp[1]} r={6} className="viz-ring" />
              <circle cx={hp[0]} cy={hp[1]} r={3.5} className="viz-dot" />
            </g>
          )}
        </g>
      </svg>
      {hp && (
        <ChartTooltip
          x={hp[0] + pad.left}
          y={hp[1] + pad.top}
          width={width}
          value={format(points[hover].value)}
          label={label}
          sub={shortDay(points[hover].date)}
        />
      )}
    </div>
  );
}
