import { useState } from "react";
import { shortDay } from "../../../lib/format.js";

// Thirty small columns, one per day: height is check-ins that day.
export default function ActivityStrip({ days }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...days.map((d) => d.value));
  const active = days.filter((d) => d.value > 0).length;
  return (
    <div className="in-strip">
      <div className="in-strip-bars" role="img" aria-label={`Active on ${active} of the last 30 days`}>
        {days.map((d, i) => (
          <span
            key={d.date}
            className={d.value ? "on" : ""}
            style={{ height: `${Math.max(8, (d.value / max) * 100)}%` }}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </div>
      <p className="in-strip-read">
        {hover !== null
          ? `${shortDay(days[hover].date)}: ${days[hover].value} check-in${days[hover].value === 1 ? "" : "s"}`
          : `Active on ${active} of the last 30 days`}
      </p>
    </div>
  );
}
