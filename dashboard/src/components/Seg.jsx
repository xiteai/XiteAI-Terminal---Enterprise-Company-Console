import { useId } from "react";
import { motion } from "../lib/motion.js";
import { cx } from "../lib/cx.js";
import "./Seg.css";

// A segmented control. The chosen pill glides between options, and only then:
// it re-measures when the choice changes, not when a count arrives or the
// page reflows, so it never wobbles while a page is loading.
// options: [{value, label, count?}]
export default function Seg({ value, onChange, options, size = "md", label, className }) {
  const group = useId();
  return (
    <div className={cx("seg", `seg-${size}`, className)} role="tablist" aria-label={label}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="tab"
            aria-selected={on}
            className={cx("seg-opt", on && "on")}
            onClick={() => onChange(o.value)}
          >
            {on && (
              <motion.span
                layoutId={`seg-${group}`}
                layoutDependency={value}
                className="seg-pill"
                transition={{ type: "spring", stiffness: 520, damping: 42, mass: 0.7 }}
              />
            )}
            <span className="seg-text">
              {o.label}
              {o.count !== undefined && o.count !== null && <span className="seg-count tnum">{o.count}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}
