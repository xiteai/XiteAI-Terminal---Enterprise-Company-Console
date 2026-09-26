import { ago, date } from "../../../lib/format.js";
import Card from "../../../components/Card.jsx";
import Icon from "../../../components/Icon.jsx";
import { KIND } from "./labels.js";

function Post({ p, onDelete }) {
  const k = KIND[p.kind];
  return (
    <li className="hm-post">
      <span className="hm-post-icon"><Icon name={k.icon} size={16} /></span>
      <span className="hm-post-body">
        <b>{p.title}</b>
        {p.body && <p>{p.body}</p>}
        {p.result && <p className="hm-post-result">{p.result}</p>}
        <span className="hm-post-meta">
          {p.kind === "event" ? date(p.event_date) : ago(p.posted_at)}
          {p.posted_by && ` · ${p.posted_by.name}`}
        </span>
      </span>
      {onDelete && (
        <button type="button" className="hm-post-del" onClick={() => onDelete(p)} aria-label={`Delete ${p.title}`}>
          <Icon name="trash" size={14} />
        </button>
      )}
    </li>
  );
}

export default function Timeline({ title, subtitle, items, empty, onDelete }) {
  return (
    <Card title={title} subtitle={subtitle}>
      {items.length === 0 ? <p className="hm-quiet"><Icon name="sparkle" size={15} />{empty}</p>
        : <ul className="hm-posts">{items.map((p) => <Post key={p.id} p={p} onDelete={onDelete} />)}</ul>}
    </Card>
  );
}
