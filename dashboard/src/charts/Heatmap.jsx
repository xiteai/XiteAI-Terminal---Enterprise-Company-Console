import { useState } from "react";
import { cx } from "../lib/cx.js";
import "./charts.css";

// When XOS1 is used: weekday by hour. One hue, light to dark with count, in
// five steps (a sequential ramp: the lightest step may recede to the surface).
const STEPS = [0.08, 0.22, 0.4, 0.62, 0.9];

export default function Heatmap({ rows, values, tzLabel = "IST" }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...values.flat());
  const step = (v) => (v === 0 ? -1 : Math.min(STEPS.length - 1, Math.floor((v / max) * STEPS.length)));
  const hourLabel = (h) => (h === 0 ? "12a" : h < 12 ? `${h}a` : h === 12 ? "12p" : `${h - 12}p`);
  return (
    <div className="heat">
      <div className="heat-grid" role="grid" aria-label={`Check-ins by weekday and hour (${tzLabel})`}>
        {rows.map((r, ri) => (
          <div className="heat-row" role="row" key={r}>
            <span className="heat-rowlabel">{r}</span>
            {values[ri].map((v, h) => {
              const s = step(v);
              return (
                <span
                  key={h}
                  role="gridcell"
                  tabIndex={-1}
                  aria-label={`${r} ${hourLabel(h)}: ${v} check-ins`}
                  className={cx("heat-cell", hover && hover.r === ri && hover.h === h && "hover")}
                  style={{ opacity: s < 0 ? 1 : undefined, "--a": s < 0 ? 0 : STEPS[s] }}
                  data-zero={s < 0 || undefined}
                  onMouseEnter={() => setHover({ r: ri, h, v })}
                  onMouseLeave={() => setHover(null)}
                />
              );
            })}
          </div>
        ))}
        <div className="heat-row heat-hours" aria-hidden>
          <span className="heat-rowlabel" />
          {Array.from({ length: 24 }, (_, h) => (
            <span key={h} className="heat-hour">{h % 3 === 0 ? hourLabel(h) : ""}</span>
          ))}
        </div>
      </div>
      <div className="heat-foot">
        <span className="heat-read">
          {hover ? (
            <><strong className="tnum">{hover.v}</strong> check-ins · {rows[hover.r]} {hourLabel(hover.h)} {tzLabel}</>
          ) : (
            <>Hover a cell · times in {tzLabel}</>
          )}
        </span>
        <span className="heat-scale" aria-label="Fewer to more">
          Fewer
          {STEPS.map((a) => <i key={a} style={{ "--a": a }} />)}
          More
        </span>
      </div>
    </div>
  );
}
