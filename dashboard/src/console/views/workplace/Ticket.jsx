import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import { Status } from "../../../components/Badge.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { PRIORITY, TICKET_STATUS } from "./labels.js";

const STATUSES = Object.entries(TICKET_STATUS).map(([value, s]) => ({ value, label: s.label }));
const PRIORITIES = Object.entries(PRIORITY).map(([value, label]) => ({ value, label }));

// One ticket and its thread. What you can change depends on who you are: the
// person who raised it may close or reopen it, the queue may do the rest.
export default function Ticket() {
  const { id } = useParams();
  const nav = useNavigate();
  const view = useData(() => api.get(`/api/workplace/tickets/${id}`), [id]);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (view.loading) return <div className="wp-loading"><Spinner /></div>;
  if (view.error) return <ErrorNote error={view.error} onRetry={view.reload} />;

  const { ticket, notes, can } = view.data;

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/workplace/tickets/${id}/notes`, { body: reply });
      setReply("");
      view.reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const change = async (patch) => {
    setError(null);
    try {
      await api.patch(`/api/workplace/tickets/${id}`, patch);
      view.reload();
    } catch (e) {
      setError(e);
    }
  };

  return (
    <div className="stack">
      <PageHeader
        title={ticket.subject}
        subtitle={`${ticket.ref} · ${ticket.category_label} · raised by ${ticket.staff?.name || "someone"}`}
        badge={<Status tone={TICKET_STATUS[ticket.status].tone}>{TICKET_STATUS[ticket.status].label}</Status>}
      >
        <Button icon="arrowLeft" variant="quiet" onClick={() => nav("/console/workplace/helpdesk")}>
          All tickets
        </Button>
      </PageHeader>

      {can.work && (
        <Card title="Queue">
          <div className="wp-fields">
            <Select label="Status" value={ticket.status} options={STATUSES}
              onChange={(v) => change({ status: v })} />
            <Select label="Priority" value={ticket.priority} options={PRIORITIES}
              onChange={(v) => change({ priority: v })} />
          </div>
        </Card>
      )}

      <Card flush>
        <ul className="wp-thread">
          <li>
            <div className="wp-msg-who">
              <b>{ticket.staff?.name || "Someone"}</b>
              <span>{dateTime(ticket.created_at)}</span>
            </div>
            <p className="wp-msg-body">{ticket.body}</p>
          </li>
          {notes.map((n) => (
            <li key={n.id}>
              <div className="wp-msg-who">
                <b>{n.staff?.name || "Someone"}</b>
                <span>{dateTime(n.at)}</span>
              </div>
              <p className="wp-msg-body">{n.body}</p>
            </li>
          ))}
        </ul>
      </Card>

      {ticket.status !== "closed" && can.reply && (
        <Card title="Reply">
          <Field label="" textarea rows={3} value={reply} onChange={(e) => setReply(e.target.value)}
            placeholder="Add to the thread" />
          <ErrorNote error={error} />
          <div className="wp-submit">
            {!can.work && ticket.status !== "closed" && (
              <Button variant="quiet" onClick={() => change({ status: "closed" })}>Close it</Button>
            )}
            <Button variant="primary" busy={busy} disabled={!reply.trim()} onClick={send}>Send</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
