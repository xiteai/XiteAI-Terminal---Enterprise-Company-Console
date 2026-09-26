import { cx } from "../lib/cx.js";
import "./Avatar.css";

// A photo when there's one, initials on a warm tile when there isn't. The
// founder's ring is ember; everyone else's is quiet.
export default function Avatar({ src, initials, level, size = 36, className }) {
  return (
    <span
      className={cx("avatar", level === "founder" && "avatar-founder", className)}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}
      aria-hidden
    >
      {src ? <img className="avatar-img" src={src} alt="" /> : (initials || "?")}
    </span>
  );
}
