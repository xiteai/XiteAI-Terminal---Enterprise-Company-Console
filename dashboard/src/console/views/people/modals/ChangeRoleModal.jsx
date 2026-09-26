import { useEffect, useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Field from "../../../../components/Field.jsx";
import Modal from "../../../../components/Modal.jsx";
import Select from "../../../../components/Select.jsx";
import { useToast } from "../../../../components/Toast.jsx";
import { useTeamOptions } from "./useTeamOptions.js";

// Promote, move or re-title someone below you.
export default function ChangeRoleModal({ open, person, onClose, onDone }) {
  const toast = useToast();
  const { opts, levels, bossesFor } = useTeamOptions(open);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open && person) {
      setForm({ level: person.level, title: person.title, department: person.department,
        employment_type: person.employment_type, reports_to: person.reports_to ? String(person.reports_to) : "",
        pf_number: person.pf_number || "", uan_number: person.uan_number || "" });
    }
  }, [open, person]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const go = async () => {
    const changes = {};
    ["level", "title", "department", "employment_type"].forEach((k) => { if (form[k] && form[k] !== person[k]) changes[k] = form[k]; });
    if (form.reports_to && Number(form.reports_to) !== person.reports_to) changes.reports_to = Number(form.reports_to);
    ["pf_number", "uan_number"].forEach((k) => { if (form[k] !== (person[k] || "")) changes[k] = form[k]; });
    if (!Object.keys(changes).length) { onClose(); return; }
    setBusy(true);
    try {
      await api.patch(`/api/people/${person.id}`, changes);
      toast("Saved.");
      onDone();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Change ${person?.preferred_name || ""}'s role`} width={520}
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="primary" busy={busy} onClick={go}>Save</Button></>}>
      <div className="md-grid">
        <Select label="Level" value={form.level} onChange={set("level")} options={levels.map((l) => ({ value: l.key, label: l.label }))} />
        <Select label="Employment" value={form.employment_type} onChange={set("employment_type")} options={opts?.employment_types || [form.employment_type].filter(Boolean)} />
      </div>
      <div className="md-grid">
        <Select label="Team" value={form.department} onChange={set("department")} options={opts?.departments || [form.department].filter(Boolean)} />
        <Select label="Reports to" value={form.reports_to} onChange={set("reports_to")} placeholder="Choose…"
          options={bossesFor(form.level || person?.level).map((b) => ({ value: String(b.id), label: `${b.display_name} · ${b.level_label}` }))} />
      </div>
      <Field label="Title" value={form.title || ""} onChange={(e) => set("title")(e.target.value)} />
      <div className="md-grid">
        <Field label="PF number" hint="Optional" placeholder="MH/12345/0000001/000/0000001"
          value={form.pf_number || ""} onChange={(e) => set("pf_number")(e.target.value)} />
        <Field label="UAN" hint="Optional, 12 digits" placeholder="100200300400"
          value={form.uan_number || ""} onChange={(e) => set("uan_number")(e.target.value)} />
      </div>
    </Modal>
  );
}
