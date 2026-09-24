import { cx } from "../lib/cx.js";
import "./Avatar.css";

// Initials on a warm tile. The founder's ring is ember; everyone else's is quiet.
export default function Avatar({ initials, level, size = 36, className }) {
  return (
    <span
      className={cx("avatar", level === "founder" && "avatar-founder", className)}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}
      aria-hidden
    >
      {initials || "?"}
    </span>
  );
}
