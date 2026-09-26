import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { ago } from "../../../lib/format.js";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import { Status } from "../../../components/Badge.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import FileCard from "./FileCard.jsx";
import { PRIORITY, TICKET_STATUS } from "./labels.js";

const CATEGORIES = [
  { value: "laptop", label: "Laptop or desktop" },
  { value: "access", label: "Access and accounts" },
  { value: "software", label: "Software" },
  { value: "network", label: "Network and VPN" },
  { value: "other", label: "Something else" },
];
const PRIORITIES = Object.entries(PRIORITY).map(([value, label]) => ({ value, label }));
const EMPTY = { category: "laptop", subject: "", body: "", priority: "normal" };

// Raise a ticket with IT, and follow it. People who work the queue get a
// second tab with everyone's.
export default function Helpdesk() {
  const { can } = useSession();
  const works = can("helpdesk.work");
  const [scope, setScope] = useState("mine");
  const list = useData(() => api.get(`/api/workplace/tickets?scope=${scope}`), [scope]);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workplace/tickets", form);
      setForm(EMPTY);
      list.reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const items = list.data?.items || [];

  return (
    <div className="stack">
      <PageHeader title="Helpdesk" subtitle="Something broken? Tell IT." />

      <FileCard
        title="Raise a ticket"
        subtitle="The more you say now, the fewer questions come back."
        error={error}
        busy={busy}
        onSubmit={submit}
        submitLabel="Raise ticket"
      >
        <Select label="About" value={form.category} onChange={set("category")} options={CATEGORIES} />
        <Select label="Priority" value={form.priority} onChange={set("priority")} options={PRIORITIES} />
        <Field label="Subject" value={form.subject} onChange={(e) => set("subject")(e.target.value)}
          placeholder="Laptop won't wake from sleep" required className="wp-wide" />
        <Field label="What's happening" textarea rows={3} value={form.body}
          onChange={(e) => set("body")(e.target.value)}
          placeholder="When it started, what you've tried" required className="wp-wide" />
      </FileCard>

      {works && (
        <Seg
          value={scope}
          onChange={setScope}
          label="Which tickets"
          options={[{ value: "mine", label: "Mine" }, { value: "queue", label: "The queue" }]}
        />
      )}

      <Card title={scope === "queue" ? "Every open ticket" : "Your tickets"} flush>
        <ErrorNote error={list.error} onRetry={list.reload} />
        {items.length === 0 ? (
          <Empty title={scope === "queue" ? "The queue is clear." : "You haven't raised a ticket."} />
        ) : (
          <ul className="wp-tickets">
            {items.map((t) => (
              <li key={t.id}>
                <Link to={`/console/workplace/helpdesk/${t.id}`} className="wp-ticket">
                  <span className="wp-ticket-ref tnum">{t.ref}</span>
                  <span className="wp-ticket-main">
                    <b>{t.subject}</b>
                    <span>
                      {t.category_label}
                      {scope === "queue" && t.staff ? ` · ${t.staff.name}` : ""}
                      {t.assignee ? ` · with ${t.assignee.name}` : ""}
                    </span>
                  </span>
                  <Status tone={TICKET_STATUS[t.status].tone}>{TICKET_STATUS[t.status].label}</Status>
                  <span className="wp-ticket-when">{ago(t.updated_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
