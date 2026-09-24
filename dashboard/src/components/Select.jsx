import { useId } from "react";
import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import "./Select.css";

// A native select, dressed to match. options: [{value, label}] or strings.
export default function Select({ label, value, onChange, options, placeholder, size = "md", className, ...rest }) {
  const id = useId();
  const norm = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <label className={cx("select", `select-${size}`, className)} htmlFor={id}>
      {label && <span className="field-label">{label}</span>}
      <span className="select-box">
        <select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} {...rest}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {norm.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>
          ))}
        </select>
        <Icon name="chevronDown" size={14} className="select-caret" />
      </span>
    </label>
  );
}
