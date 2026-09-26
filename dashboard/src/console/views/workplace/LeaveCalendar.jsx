import { useMemo } from "react";
import { motion } from "../../../lib/motion.js";
import { cx } from "../../../lib/cx.js";
import Icon from "../../../components/Icon.jsx";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const iso = (d) => d.toISOString().slice(0, 10);
const todayIso = iso(new Date());

function monthGrid(month) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const startOffset = (first.getDay() + 6) % 7;                    // Monday-first
  const start = new Date(first);
  start.setDate(first.getDate() - startOffset);
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

// A month of days, each carrying whatever's true about it: a holiday, a
// weekend, an existing leave request, or a day picked for a new one. Every
// click toggles that one day — alternate-day, split-week, whatever the leave
// actually looks like, not just a dragged range.
export default function LeaveCalendar({ month, onMonth, requests, holidayMap, selected, onToggle, minIso }) {
  const days = useMemo(() => monthGrid(month), [month]);
  const inMonth = month.getMonth();

  const cover = (day) => requests.find((r) => (r.dates || []).includes(day)
    && (r.status === "approved" || r.status === "pending"));

  return (
    <div className="lc">
      <div className="lc-head">
        <span className="lc-month">{month.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</span>
        <div className="lc-nav">
          <button type="button" onClick={() => onMonth(-1)} aria-label="Previous month"><Icon name="chevronLeft" size={16} /></button>
          <button type="button" className="lc-today" onClick={() => onMonth(0, true)}>Today</button>
          <button type="button" onClick={() => onMonth(1)} aria-label="Next month"><Icon name="chevronRight" size={16} /></button>
        </div>
      </div>

      <div className="lc-weekdays">{WEEKDAYS.map((w) => <span key={w}>{w}</span>)}</div>

      <motion.div className="lc-grid" key={month.toISOString()} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.22 }}>
        {days.map((d) => {
          const day = iso(d);
          const weekend = d.getDay() === 0 || d.getDay() === 6;
          const holiday = holidayMap[day];
          const booked = cover(day);
          const picked = selected.has(day);
          const disabled = (minIso && day < minIso) || weekend || Boolean(holiday) || Boolean(booked);
          const outside = d.getMonth() !== inMonth;
          return (
            <button
              key={day}
              type="button"
              disabled={disabled && !picked}
              onClick={() => onToggle(day)}
              className={cx("lc-day",
                outside && "lc-outside",
                day === todayIso && "lc-today-cell",
                weekend && "lc-weekend",
                holiday && "lc-holiday",
                booked && `lc-${booked.status}`,
                picked && "lc-picked",
                disabled && !picked && "lc-disabled")}
              title={holiday || (booked && `${booked.leave_label || "Leave"} · ${booked.status}`) || undefined}
            >
              <span className="lc-num">{d.getDate()}</span>
              {holiday && !outside && <span className="lc-dot" />}
            </button>
          );
        })}
      </motion.div>

      <div className="lc-legend">
        <span><i className="lc-sw lc-sw-picked" />Picked</span>
        <span><i className="lc-sw lc-sw-approved" />Approved</span>
        <span><i className="lc-sw lc-sw-pending" />Pending</span>
        <span><i className="lc-sw lc-sw-holiday" />Holiday</span>
        <span><i className="lc-sw lc-sw-weekend" />Weekend</span>
      </div>
    </div>
  );
}
