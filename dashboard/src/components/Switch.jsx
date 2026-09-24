import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import "./Switch.css";

export default function Switch({ checked, onChange, disabled, label, size = "md" }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={cx("switch", `switch-${size}`, checked && "on")}
      onClick={() => !disabled && onChange(!checked)}
    >
      <span className="switch-knob" />
    </button>
  );
}

// The same yes/no as a checkbox, for grids where many switches would crowd.
export function Checkbox({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={cx("check", checked && "on")}
      onClick={() => !disabled && onChange(!checked)}
    >
      <Icon name="check" size={13} stroke={2.4} />
    </button>
  );
}
