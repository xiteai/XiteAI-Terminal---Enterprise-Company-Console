import { useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import { KIND } from "./labels.js";

const EMPTY = { kind: "news", title: "", body: "", event_date: "" };

export default function PostModal({ open, onClose, onDone }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/feed", form);
      setForm(EMPTY);
      onDone();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Post to Home" subtitle="Everyone active sees this."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant="primary" busy={busy} onClick={submit} disabled={form.title.trim().length < 3}>Post</Button></>}>
      <Seg value={form.kind} onChange={set("kind")}
        options={Object.entries(KIND).map(([value, k]) => ({ value, label: k.label }))} />
      <div className="hm-fields">
        <Field label="Headline" className="hm-wide" value={form.title}
          onChange={(e) => set("title")(e.target.value)} placeholder="We closed our Series A" />
        {form.kind === "event" && (
          <Field label="When" type="date" value={form.event_date}
            onChange={(e) => set("event_date")(e.target.value)} required />
        )}
        <Field label="Details" textarea rows={3} className="hm-wide" value={form.body}
          onChange={(e) => set("body")(e.target.value)} placeholder="Optional" />
      </div>
      <ErrorNote error={error} />
    </Modal>
  );
}
