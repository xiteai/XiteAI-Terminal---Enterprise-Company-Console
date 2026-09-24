import { cx } from "../lib/cx.js";
import "./Card.css";

// A white card. `title` and `subtitle` head it, `action` sits on the right.
// `flush` drops the padding so a table or list can run edge to edge.
export default function Card({ title, subtitle, action, className, children, pad = true, flush = false, as: Tag = "section" }) {
  return (
    <Tag className={cx("card", flush ? "card-flush" : pad && "card-pad", className)}>
      {(title || action) && (
        <header className="card-head">
          <div className="card-titles">
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {action && <div className="card-action">{action}</div>}
        </header>
      )}
      {children}
    </Tag>
  );
}
