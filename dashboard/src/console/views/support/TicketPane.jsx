import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { KIND_LABEL, PRIORITY_LABEL, STATUS_LABEL } from "./labels.js";

const initials = (name = "") => name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "?";

export default function TicketPane({ id, onChanged }) {
  const toast = useToast();
  const { product, base } = useProduct();
  const { data, error, reload } = useData(() => api.get(`/api/tickets/${id}`), [id]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const patch = async (body, msg) => {
    try {
      await api.patch(`/api/tickets/${id}`, body);
      toast(msg);
      reload();
      onChanged();
    } catch (e) { toast.error(e.message); }
  };
  const addNote = async () => {
    if (!note.trim()) return;
    setBusy(true);
    try {
      await api.post(`/api/tickets/${id}/notes`, { body: note });
      setNote("");
      reload();
      onChanged();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  if (error) return <div className="tk"><ErrorNote error={error} onRetry={reload} /></div>;
  if (!data) return <div className="drawer-wait"><Spinner delay={300} /></div>;
  const t = data.ticket;
  const can = data.can;
  return (
    <article key={t.id} className="tk fade-in">
      <header className="tk-head">
        <div className="tk-tags">
          <span className="mono">{t.ref}</span>
          <span className={t.kind === "data_delete" || t.kind === "data_access" ? "sp-strong" : undefined}>{KIND_LABEL[t.kind]}</span>
          <span>{STATUS_LABEL[t.status]}</span>
          {(t.priority === "urgent" || t.priority === "high") && (
            <span className={t.priority === "urgent" ? "sp-bad" : "sp-strong"}>{PRIORITY_LABEL[t.priority]} priority</span>
          )}
          {t.is_demo && <span>Demo</span>}
        </div>
        <h2 className="t-h2">{t.subject}</h2>
        <div className="tk-from">
          <Avatar initials={initials(t.name || t.email)} size={32} />
          <span>
            <b>{t.name || "Someone"}</b>
            <a className="text-link" href={`mailto:${t.email}`}>{t.email}</a>
          </span>
          <span className="tk-when">{dateTime(t.created_at)}</span>
        </div>
      </header>

      <p className="tk-message">{t.message}</p>

      {data.install && (
        <div className="callout">
          <Icon name="info" size={16} />
          <span>
            Sent from {words(product).one} <Link className="text-link mono" to={`${base}/installs/${data.install.id}`}>{data.install.code}</Link>,
            version {data.install.app_version}, last seen {ago(data.install.last_seen)}.
            {t.kind === "data_delete" && can.erase && " To honour this, open it and erase it, then mark this resolved."}
          </span>
        </div>
      )}

      <div className="tk-controls">
        <Select size="sm" label="Status" value={t.status} disabled={!can.reply}
          onChange={(v) => patch({ status: v }, `Marked ${STATUS_LABEL[v].toLowerCase()}.`)}
          options={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))} />
        <Select size="sm" label="Priority" value={t.priority} disabled={!can.reply}
          onChange={(v) => patch({ priority: v }, `Priority set to ${PRIORITY_LABEL[v].toLowerCase()}.`)}
          options={Object.entries(PRIORITY_LABEL).map(([value, label]) => ({ value, label }))} />
        {can.assign ? (
          <Select size="sm" label="Assigned to" value={t.assignee_id || ""} placeholder="Nobody yet"
            onChange={(v) => patch(v ? { assignee_id: Number(v) } : { unassign: true }, v ? "Assigned." : "Unassigned.")}
            options={data.assignable.map((p) => ({ value: p.id, label: p.name }))} />
        ) : (
          <div className="tk-assignee"><span className="field-label">Assigned to</span><span>{t.assignee_name || "Nobody yet"}</span></div>
        )}
      </div>

      <section className="tk-notes">
        <h3 className="t-h3">Team notes</h3>
        {data.notes.length === 0 && <p className="t-note">No notes yet.</p>}
        {data.notes.map((n) => (
          <div className="tk-note" key={n.id}>
            <Avatar initials={initials(n.author)} size={28} />
            <div>
              <p className="tk-note-meta"><b>{n.author || "Someone"}</b> · {ago(n.at)}</p>
              <p className="tk-note-body">{n.body}</p>
            </div>
          </div>
        ))}
        {can.reply && (
          <div className="tk-compose">
            <Field textarea placeholder="Write a note for the team…" value={note} onChange={(e) => setNote(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) addNote(); }} />
            <div className="tk-compose-row">
              <span className="t-note"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> to add</span>
              <Button variant="primary" size="sm" busy={busy} disabled={!note.trim()} onClick={addNote}>Add note</Button>
            </div>
          </div>
        )}
      </section>
    </article>
  );
}
