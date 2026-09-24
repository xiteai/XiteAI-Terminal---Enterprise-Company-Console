import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import { useProduct } from "../../../lib/product.jsx";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Select from "../../../components/Select.jsx";
import { useToast } from "../../../components/Toast.jsx";

const STATUSES = [{ value: "live", label: "Live" }, { value: "building", label: "In development" }, { value: "paused", label: "Paused" }];

// Founder only: a product's name, description, status and latest version.
export default function EditProductModal({ open, onClose }) {
  const toast = useToast();
  const { refresh } = useSession();
  const { product } = useProduct();
  const [form, setForm] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fromEnv = product.slug === "xos1";
  useEffect(() => {
    if (open) {
      setForm({ name: product.name, full_name: product.full_name, description: product.description, website: product.website,
        status: product.status, latest_version: product.latest_version });
      setError("");
    }
  }, [open, product]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const { latest_version: v, ...rest } = form;
      await api.patch(`/api/products/${product.slug}`, fromEnv ? rest : form);
      await refresh();
      toast("Saved.");
      onClose();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Edit ${product.name}`} width={520}
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="primary" busy={busy} onClick={save}>Save changes</Button></>}>
      <div className="md-grid">
        <Field label="Name" value={form.name || ""} onChange={set("name")} />
        <Select label="Status" value={form.status} onChange={(v) => setForm((f) => ({ ...f, status: v }))} options={STATUSES} />
      </div>
      <Field label="Full name" value={form.full_name || ""} onChange={set("full_name")} />
      <Field label="Description" value={form.description || ""} onChange={set("description")} />
      <div className="md-grid">
        <Field label="Website" value={form.website || ""} onChange={set("website")} placeholder="https://" />
        <Field label="Latest version" value={form.latest_version || ""} onChange={set("latest_version")} disabled={fromEnv}
          hint={fromEnv ? "Set by LATEST_VERSION in .env" : undefined} />
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
    </Modal>
  );
}
