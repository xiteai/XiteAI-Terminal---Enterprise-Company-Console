import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import Switch from "../../../components/Switch.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";
import ItemBuilder from "./ItemBuilder.jsx";

// Give someone code: from the Access page, or straight from a file or a search
// result, already filled in with that file or function. The server decides
// whether you may; this only makes it quick.
export default function GiveAccess({ open, onClose, initialItems = [], onDone }) {
  const { rid, repo } = useRepo();
  const toast = useToast();
  const [people, setPeople] = useState([]);
  const [features, setFeatures] = useState([]);
  const [files, setFiles] = useState([]);
  const [who, setWho] = useState("");
  const [mode, setMode] = useState("items");
  const [items, setItems] = useState([]);
  const [feature, setFeature] = useState("");
  const [edit, setEdit] = useState(false);
  const [until, setUntil] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!open) return;
    setWho(""); setMode("items"); setItems(initialItems); setFeature(""); setEdit(false); setUntil(""); setNote(""); setErr(null);
    api.get(`/api/code/${rid}/people`).then((d) => setPeople(d.items)).catch((e) => setErr(e.message));
    api.get(`/api/code/${rid}/access`).then((d) => setFeatures(d.features)).catch(() => setFeatures([]));
    api.get(`/api/code/${rid}/tree`).then((d) => setFiles(d.files)).catch(() => setFiles([]));
  }, [open, rid, repo.head_sha]); // eslint-disable-line react-hooks/exhaustive-deps

  const target = people.find((p) => String(p.id) === String(who));
  const ready = who && (mode === "items" ? items.length : feature);
  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const next = await api.post(`/api/code/${rid}/grants`, {
        staff_id: Number(who), can_edit: edit, expires_on: until || null, note,
        ...(mode === "feature" ? { feature_id: Number(feature) } : { items }),
      });
      toast(`Access given to ${target?.name || "them"}. They were told.`);
      onDone?.(next);
      onClose();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Give access" width={620}
      subtitle="You can give only what you have: owners give in what they own, reviewers give read access to their own team."
      footer={<Button variant="primary" busy={busy} disabled={!ready} onClick={save}>Give access</Button>}>
      <div className="code-form">
        <Select label="Person" value={who} onChange={setWho} placeholder="Choose someone"
          options={people.filter((p) => !p.me).map((p) => ({ value: p.id, label: `${p.name}, ${p.level_label}${p.title ? `, ${p.title}` : ""}` }))} />
        {features.length > 0 && (
          <Seg size="sm" value={mode} onChange={setMode} label="What to give"
            options={[{ value: "items", label: "Pick code" }, { value: "feature", label: "A feature" }]} />
        )}
        {mode === "feature" ? (
          <Select label="Feature" value={feature} onChange={setFeature} placeholder="Choose a feature"
            options={features.map((f) => ({ value: f.id, label: `${f.name} (${f.items.length} item${f.items.length === 1 ? "" : "s"})` }))} />
        ) : <ItemBuilder files={files} items={items} onChange={setItems} />}
        <div className="code-row">
          <span><b>Can edit</b><small>Off: they can read it. On: they can also send changes to it.</small></span>
          <Switch checked={edit} onChange={setEdit} label="Can edit" />
        </div>
        {target?.level === "intern" && edit && <p className="t-note">Interns' changes need two approvals.</p>}
        <div className="code-two">
          <Field label="Until (optional)" type="date" value={until} onChange={(e) => setUntil(e.target.value)} hint="Access ends after this day." />
          <Field label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For the memory bug, sprint 12" maxLength={300} />
        </div>
        {err && <p className="form-error" role="alert">{err}</p>}
      </div>
    </Modal>
  );
}
