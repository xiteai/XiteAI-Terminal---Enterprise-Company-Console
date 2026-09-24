import { useEffect, useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Field from "../../../../components/Field.jsx";
import Modal from "../../../../components/Modal.jsx";
import Select from "../../../../components/Select.jsx";
import { useToast } from "../../../../components/Toast.jsx";
import { useTeamOptions } from "./useTeamOptions.js";

// Approve a join request, adjusting level, title, team or manager if needed.
export default function ApproveModal({ open, person, onClose, onDone }) {
  const toast = useToast();
  const { opts, levels, bossesFor, me } = useTeamOptions(open);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open && person) setForm({ level: person.level, title: person.title, department: person.department, reports_to: String(me.user.id), note: "" });
  }, [open, person, me.user.id]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const bosses = bossesFor(form.level || person?.level);

  const go = async () => {
    setBusy(true);
    try {
      await api.post(`/api/requests/${person.id}/approve`, {
        level: form.level, title: form.title, department: form.department,
        reports_to: form.reports_to ? Number(form.reports_to) : undefined, note: form.note,
      });
      toast(`${person.display_name} is in. Everyone who could approve has been told.`);
      onDone();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Approve ${person?.preferred_name || ""}`} width={520}
      subtitle="They'll get into the console straight away. You can adjust the details first."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="ember" icon="check" busy={busy} onClick={go}>Approve</Button></>}>
      <div className="md-grid">
        <Select label="Level" value={form.level} onChange={set("level")} options={levels.map((l) => ({ value: l.key, label: l.label }))} />
        <Select label="Team" value={form.department} onChange={set("department")} options={opts?.departments || [form.department].filter(Boolean)} />
      </div>
      <Field label="Title" value={form.title || ""} onChange={(e) => set("title")(e.target.value)} />
      <Select label="Reports to" value={form.reports_to} onChange={set("reports_to")}
        options={bosses.map((b) => ({ value: String(b.id), label: `${b.display_name} · ${b.level_label}` }))} />
      <Field label="Note (optional)" placeholder="Anything worth recording" value={form.note || ""} onChange={(e) => set("note")(e.target.value)} />
    </Modal>
  );
}
