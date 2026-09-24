import { forwardRef } from "react";
import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import Spinner from "./Spinner.jsx";
import "./Button.css";

// Icons are not decoration: a button keeps its icon only when the icon says
// something the label doesn't (a direction, a download, a search).
const MEANINGFUL = new Set(["arrowLeft", "arrowRight", "download", "search", "external", "plus", "trash", "logout", "refresh", "check"]);

// variant: primary (ink) | ghost | quiet | danger ; size: sm | md | lg
const Button = forwardRef(function Button(
  { variant = "ghost", size = "md", icon: rawIcon, iconRight: rawRight, busy = false, block = false, className, children, ...rest },
  ref,
) {
  const icon = rawIcon && (!children || MEANINGFUL.has(rawIcon)) ? rawIcon : null;
  const iconRight = rawRight && MEANINGFUL.has(rawRight) ? rawRight : null;
  return (
    <button
      ref={ref}
      type="button"
      className={cx("btn", `btn-${variant}`, `btn-${size}`, block && "btn-block", !children && "btn-icon", className)}
      disabled={busy || rest.disabled}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Spinner size={size === "sm" ? 12 : 14} /> : icon && <Icon name={icon} size={size === "sm" ? 15 : 16} />}
      {children && <span className="btn-label">{children}</span>}
      {iconRight && !busy && <Icon name={iconRight} size={size === "sm" ? 15 : 16} />}
    </button>
  );
});

export default Button;
