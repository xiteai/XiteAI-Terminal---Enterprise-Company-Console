import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import "./Badge.css";

// tone: neutral | accent | warn | bad | demo. Rare, colourless, and always
// a word, never colour alone.
export default function Badge({ tone = "neutral", icon, children, className, title }) {
  return (
    <span className={cx("badge", `badge-${tone}`, className)} title={title}>
      {icon && <Icon name={icon} size={12} stroke={1.9} />}
      {children}
    </span>
  );
}

export function Dot({ tone = "neutral", label }) {
  return <span className={cx("dot", `dot-${tone}`)} role={label ? "img" : undefined} aria-label={label} />;
}

// How something is doing, as a plain word. tone: good | neutral (grey),
// warn (ink, heavier), bad (red).
export function Status({ tone = "neutral", children, className }) {
  return <span className={cx("status", `status-${tone}`, className)}>{children}</span>;
}
