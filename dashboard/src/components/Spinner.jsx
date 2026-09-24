import { useEffect, useState } from "react";
import "./Spinner.css";

// `delay` (ms) keeps it hidden that long first: a page that loads quickly
// shows nothing at all instead of a spinner that flashes and vanishes.
export default function Spinner({ size = 16, label = "Loading", delay = 0 }) {
  const [shown, setShown] = useState(!delay);
  useEffect(() => {
    if (!delay) return undefined;
    const t = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(t);
  }, [delay]);
  return (
    <span className="spinner" style={{ width: size, height: size }} role="status" aria-label={label}>
      {shown && (
        <svg viewBox="0 0 20 20" width={size} height={size}>
          <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeOpacity="0.18" strokeWidth="2.2" />
          <path d="M10 2a8 8 0 0 1 8 8" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        </svg>
      )}
    </span>
  );
}
