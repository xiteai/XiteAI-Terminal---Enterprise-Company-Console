import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import { useToast } from "../../../components/Toast.jsx";

const slugOf = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32);
const EMPTY = { name: "", slug: "", kind: "desktop", description: "", website: "" };

// Founder only: add something XiteAI ships. You become its owner.
export default function NewProductModal({ open, onClose, onDone }) {
  const toast = useToast();
  const navigate = useNavigate();
  const { refresh } = useSession();
  const [form, setForm] = useState(EMPTY);
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setForm(EMPTY); setSlugTouched(false); setError(""); } }, [open]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value, ...(k === "name" && !slugTouched ? { slug: slugOf(e.target.value) } : {}) }));

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const p = await api.post("/api/products", { ...form, status: "building" });
      await refresh();
      onDone?.();
      onClose();
      toast(`${p.name} added. You're its owner.`);
      navigate(`/console/p/${p.slug}`);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="New product" width={500}
      subtitle="It gets its own overview, customers, releases, support and team. Installs and users arrive once it checks in."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="primary" busy={busy} disabled={form.name.trim().length < 2} onClick={save}>Create product</Button></>}>
      <Field label="Name" placeholder="e.g. XiteAI Chat" value={form.name} onChange={set("name")} data-autofocus />
      <Field label="Short name" hint={`Used in links: /console/p/${form.slug || "short-name"}`} value={form.slug}
        onChange={(e) => { setSlugTouched(true); setForm((f) => ({ ...f, slug: slugOf(e.target.value) })); }} />
      <div className="field">
        <span className="field-label">What kind of product</span>
        <Seg value={form.kind} onChange={(kind) => setForm((f) => ({ ...f, kind }))} label="Kind"
          options={[{ value: "desktop", label: "Desktop app" }, { value: "web", label: "Web app" }]} />
      </div>
      <Field label={<>Description <span className="opt">(optional)</span></>} placeholder="One line about what it does" value={form.description} onChange={set("description")} />
      <Field label={<>Website <span className="opt">(optional)</span></>} placeholder="https://" value={form.website} onChange={set("website")} />
      {error && <p className="form-error" role="alert">{error}</p>}
    </Modal>
  );
}
