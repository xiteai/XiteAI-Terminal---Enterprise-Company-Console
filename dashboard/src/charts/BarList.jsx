import { useState } from "react";
import { motion } from "../lib/motion.js";
import { cx } from "../lib/cx.js";
import { tickLabel } from "./scale.js";
import "./charts.css";

// Horizontal bars for comparing a handful of categories. One series, one
// colour; `emphasis` picks out the one bar the story is about (in ink) and
// quiets the rest. Value sits at each bar's tip; hover shows share too.
// items: [{label, value}]
export default function BarList({ items, emphasis, format = tickLabel, total, empty = "Nothing yet.", max: maxOverride }) {
  const [hover, setHover] = useState(null);
  if (!items?.length) return <p className="viz-empty">{empty}</p>;
  const max = maxOverride || Math.max(1, ...items.map((i) => i.value));
  const sum = total ?? items.reduce((a, i) => a + i.value, 0);
  return (
    <ul className="bars" role="list">
      {items.map((it, i) => {
        const share = sum ? it.value / sum : 0;
        // Ink only where it means something: the one emphasised bar, with
        // the rest in grey. Without an emphasis every bar is the same graphite.
        const tone = emphasis ? (emphasis === it.label ? "bar-accent" : "bar-muted") : "bar-plain";
        return (
          <li
            key={it.label}
            className={cx("bar-row", hover === i && "hover")}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            title={`${it.label}: ${format(it.value)} (${(share * 100).toFixed(1)}%)`}
          >
            <span className="bar-label">{it.label}</span>
            <span className="bar-track">
              <motion.span
                className={cx("bar-fill", tone)}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: it.value / max }}
                transition={{ duration: 0.7, delay: i * 0.035, ease: [0.16, 1, 0.3, 1] }}
              />
            </span>
            <span className="bar-value tnum">
              {format(it.value)}
              <em>{hover === i ? `${(share * 100).toFixed(1)}%` : ""}</em>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
