import { ago } from "../../../lib/format.js";
import { cx } from "../../../lib/cx.js";
import Empty from "../../../components/Empty.jsx";
import { KIND_LABEL, PRIORITY_LABEL } from "./labels.js";

// Data requests and anything high priority are set in ink so they stand out
// down the list; urgent reads red.
const kindClass = (k) => (k === "data_delete" || k === "data_access" ? "sp-strong" : undefined);
const prioClass = (p) => (p === "urgent" ? "sp-bad" : "sp-strong");

export default function TicketList({ items, selected, onOpen }) {
  if (!items.length) return <Empty title="Nothing here.">All clear for now.</Empty>;
  return (
    <ul className="sp-items scroll-y">
      {items.map((t) => (
        <li key={t.id}>
          <button className={cx("sp-item", selected === t.id && "on", t.status === "open" && "unread")} onClick={() => onOpen(t)}>
            <span className="sp-item-top">
              <span className="sp-item-subject">{t.subject}</span>
              <span className="sp-item-time">{ago(t.updated_at)}</span>
            </span>
            <span className="sp-item-msg">{t.message}</span>
            <span className="sp-item-meta">
              <span className={kindClass(t.kind)}>{KIND_LABEL[t.kind]}</span>
              {(t.priority === "urgent" || t.priority === "high") && <span className={prioClass(t.priority)}>{PRIORITY_LABEL[t.priority]}</span>}
              <span>{t.name || t.email}</span>
              {t.is_demo && <span>Demo</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
