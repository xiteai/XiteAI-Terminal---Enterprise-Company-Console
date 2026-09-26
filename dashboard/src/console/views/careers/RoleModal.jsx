import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Select from "../../../components/Select.jsx";

const EMPTY = { title: "", department: "", employment_type: "", location: "Remote", summary: "", description: "" };

// Posting and editing are the same form. Editing is live the moment it
// saves — there's no draft state, the way there isn't one for the Handbook.
export default function RoleModal({ open, role, options, onClose, onDone }) {
  const editing = Boolean(role);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!open) return;
    setForm(role ? {
      title: role.title, department: role.department, employment_type: role.employment_type,
      location: role.location, summary: role.summary, description: role.description || "",
    } : EMPTY);
    setError(null);
  }, [open, role]);

  const titleOptions = options?.titles?.[form.department] || [];

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (editing) await api.put(`/api/careers/admin/roles/${role.id}`, form);
      else await api.post("/api/careers/admin/roles", form);
      onDone();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit role" : "Post a role"}
      subtitle={editing ? "Changes are live the moment you save." : "Goes live on the public Careers page immediately."}
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant="primary" busy={busy} onClick={submit}
          disabled={!form.title || !form.department || !form.employment_type || !form.summary}>
          {editing ? "Save changes" : "Post role"}
        </Button></>}>
      <div className="pr-fields">
        <Select label="Department" value={form.department} onChange={set("department")}
          options={options?.departments || []} placeholder="Choose…" />
        <Select label="Employment" value={form.employment_type} onChange={set("employment_type")}
          options={options?.employment_types || []} placeholder="Choose…" />
      </div>
      <div style={{ marginTop: 12 }}>
        {titleOptions.length > 0 ? (
          <Select label="Title" value={form.title} onChange={set("title")}
            options={titleOptions} placeholder="Choose, or a custom one below" />
        ) : null}
        <div style={{ marginTop: titleOptions.length ? 8 : 0 }}>
          <Field label={titleOptions.length ? "Or a custom title" : "Title"} value={form.title}
            onChange={(e) => set("title")(e.target.value)} placeholder="Senior Software Engineer" />
        </div>
      </div>
      <div className="pr-fields" style={{ marginTop: 12 }}>
        <Field label="Location" value={form.location} onChange={(e) => set("location")(e.target.value)} />
      </div>
      <div style={{ marginTop: 12 }}>
        <Field label="One-line summary" value={form.summary} onChange={(e) => set("summary")(e.target.value)}
          placeholder="What this role actually does, in one sentence" />
      </div>
      <div style={{ marginTop: 12 }}>
        <Field label="Full description" hint="Leave a blank line between paragraphs."
          textarea rows={8} value={form.description} onChange={(e) => set("description")(e.target.value)} />
      </div>
      <ErrorNote error={error} />
    </Modal>
  );
}
