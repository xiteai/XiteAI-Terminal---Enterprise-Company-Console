import Icon from "../../../components/Icon.jsx";
import { KIND } from "./labels.js";

// A slow-scrolling strip of what's coming and what just landed — the one
// place on Home that moves on its own, so it earns that by carrying only
// the headlines. The list is duplicated once so the loop has no seam.
export default function Marquee({ items }) {
  if (!items.length) return null;
  const loop = [...items, ...items];
  return (
    <div className="hm-marquee" role="list" aria-label="Upcoming and recent">
      <div className="hm-marquee-track">
        {loop.map((p, i) => (
          <span key={`${p.id}-${i}`} role="listitem" className="hm-marquee-item">
            <Icon name={KIND[p.kind]?.icon || "sparkle"} size={14} />
            <b>{p.title}</b>
            {p.event_date && <span>{new Date(`${p.event_date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>}
          </span>
        ))}
      </div>
    </div>
  );
}
