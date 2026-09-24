import { cx } from "../lib/cx.js";
import "./charts.css";

// A figure: a label, the number, then either the change against a named
// period or one quiet line of context. A rise is plain ink; only a fall in
// something that should grow turns red.
export default function StatTile({ label, value, delta, period = "previous period", goodWhenUp = true, note }) {
  const hasDelta = delta !== null && delta !== undefined && Number.isFinite(delta);
  const up = hasDelta && delta > 0;
  const flat = hasDelta && Math.abs(delta) < 0.005;
  const good = flat ? null : up === goodWhenUp;
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {hasDelta ? (
        <span className={cx("stat-delta", good === true && "good", good === false && "bad")}>
          <span className="tnum">{flat ? "±0%" : `${up ? "+" : "−"}${Math.abs(delta * 100).toFixed(Math.abs(delta) < 0.1 ? 1 : 0)}%`}</span>
          <span className="stat-period">vs {period}</span>
        </span>
      ) : (
        note && <span className="stat-note">{note}</span>
      )}
    </div>
  );
}
