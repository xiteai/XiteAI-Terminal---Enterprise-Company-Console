import { useEffect, useState } from "react";
import { api, qs } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useDebounced } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import "./Audit.css";

// The few actions worth catching the eye: failures and removals read red.
const BAD = new Set(["auth.failed", "install.erased", "person.deactivated", "join.declined"]);
const pretty = (action) => action.replace(/[._]/g, " ").replace(/^\w/, (c) => c.toUpperCase());

// What happened, who did it, and to what. Nothing here can be edited.
export default function Audit() {
  const [q, setQ] = useState("");
  const query = useDebounced(q, 300);
  const [items, setItems] = useState([]);
  const [more, setMore] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async (before) => {
    setBusy(true);
    try {
      const r = await api.get(`/api/audit${qs({ q: query, before, limit: 60 })}`);
      setItems((xs) => (before ? [...xs, ...r.items] : r.items));
      setMore(r.more);
      setError(null);
    } catch (e) { setError(e); } finally { setBusy(false); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [query]);

  return (
    <div>
      <PageHeader title="Audit log" subtitle="Every sign-in, decision, change and deletion, newest first. Read-only." />
      <div className="toolbar">
        <Field icon="search" placeholder="Search actions, people, targets" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <ErrorNote error={error} onRetry={() => load()} />
      {!busy && items.length === 0 && !error && <Empty title="Nothing recorded yet." />}
      {items.length > 0 && (
        <ol className="au-list">
          {items.map((r) => (
            <li key={r.id} className={`au-row${BAD.has(r.action) ? " au-bad" : ""}`}>
              <span className="au-when tnum" title={dateTime(r.at)}>{ago(r.at)}</span>
              <span className="au-main">
                <span className="au-line">
                  <b>{r.actor_name}</b>
                  <span className="au-action">{pretty(r.action).toLowerCase()}</span>
                  {r.target && <span className="au-target">{r.target}</span>}
                </span>
                {r.detail && <span className="au-detail">{r.detail}</span>}
              </span>
            </li>
          ))}
        </ol>
      )}
      {more && (
        <div className="au-more">
          <Button variant="ghost" busy={busy} onClick={() => load(items[items.length - 1]?.id)}>Load older</Button>
        </div>
      )}
    </div>
  );
}
