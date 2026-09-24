import { useEffect } from "react";
import { motion } from "../../lib/motion.js";
import { cx } from "../../lib/cx.js";

// Answer by clicking, or by pressing the number beside an option.
export default function ChoiceList({ options, value, onPick, dense = false }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.metaKey || e.ctrlKey) return;
      const n = Number(e.key);
      if (n >= 1 && n <= options.length) onPick(options[n - 1].value);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [options, onPick]);

  return (
    <div className={cx("choices", dense && "choices-dense")} role="radiogroup">
      {options.map((o, i) => {
        const on = o.value === value;
        return (
          <motion.button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            className={cx("choice", on && "on")}
            onClick={() => onPick(o.value)}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 + i * 0.02, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className="choice-radio" aria-hidden />
            <span className="choice-text">
              <span className="choice-label">{o.label}</span>
              {o.note && <span className="choice-note">{o.note}</span>}
            </span>
            {i < 9 && <kbd className="choice-key">{i + 1}</kbd>}
          </motion.button>
        );
      })}
    </div>
  );
}
