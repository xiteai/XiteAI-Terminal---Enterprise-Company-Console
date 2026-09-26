import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import "./Select.css";

// A custom listbox, not a dressed-up native <select>: the trigger and its
// open menu share one design language, the chosen row gets a checkmark, and
// the whole thing keys through like a real control (arrows, Home/End, type-
// ahead, Enter, Escape). options: [{value, label}] or strings.
export default function Select({ label, value, onChange, options, placeholder, size = "md", className, disabled, ...rest }) {
  const id = useId();
  const norm = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const rootRef = useRef(null);
  const listRef = useRef(null);
  const typeahead = useRef({ str: "", at: 0 });

  const chosen = norm.find((o) => o.value === value);

  useEffect(() => {
    if (!open) return undefined;
    setActive(Math.max(0, norm.findIndex((o) => o.value === value)));
    const onDown = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (open && active >= 0) listRef.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  const pick = (o) => {
    if (o.disabled) return;
    onChange(o.value);
    setOpen(false);
  };

  const onKeyDown = (e) => {
    if (disabled) return;
    if (!open && ["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
      e.preventDefault();
      setOpen(true);
      return;
    }
    if (!open) return;
    if (e.key === "Escape") { e.preventDefault(); setOpen(false); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => Math.min(norm.length - 1, i + 1)); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => Math.max(0, i - 1)); return; }
    if (e.key === "Home") { e.preventDefault(); setActive(0); return; }
    if (e.key === "End") { e.preventDefault(); setActive(norm.length - 1); return; }
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (norm[active]) pick(norm[active]); return; }
    if (e.key.length === 1) {
      const now = Date.now();
      typeahead.current.str = now - typeahead.current.at < 600 ? typeahead.current.str + e.key : e.key;
      typeahead.current.at = now;
      const hit = norm.findIndex((o) => o.label.toLowerCase().startsWith(typeahead.current.str.toLowerCase()));
      if (hit >= 0) setActive(hit);
    }
  };

  return (
    <div ref={rootRef} className={cx("select", `select-${size}`, open && "select-open", disabled && "select-disabled", className)}>
      {label && <span className="field-label" id={`${id}-label`}>{label}</span>}
      <button
        type="button"
        className="select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby={label ? `${id}-label` : undefined}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={onKeyDown}
        {...rest}
      >
        <span className={cx("select-value", !chosen && "select-placeholder")}>
          {chosen ? chosen.label : placeholder || "Select…"}
        </span>
        <Icon name="chevronDown" size={14} className="select-caret" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.ul
            ref={listRef}
            role="listbox"
            className="select-list"
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -3, scale: 0.985, transition: { duration: 0.12 } }}
            transition={{ type: "spring", stiffness: 560, damping: 38 }}
          >
            {norm.map((o, i) => (
              <li
                key={o.value}
                role="option"
                aria-selected={o.value === value}
                className={cx("select-opt", i === active && "on-active", o.value === value && "on-selected", o.disabled && "opt-disabled")}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(o)}
              >
                <span>{o.label}</span>
                {o.value === value && <Icon name="check" size={14} />}
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
