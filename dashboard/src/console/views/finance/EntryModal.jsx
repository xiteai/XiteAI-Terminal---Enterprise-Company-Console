import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import { useProduct } from "../../../lib/product.jsx";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY = { kind: "revenue", category: "", amount: "", occurred_on: today(), note: "" };

export default function EntryModal({ open, options, onClose, onDone }) {
  const { slug } = useProduct();
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const categories = form.kind === "revenue" ? options?.revenue_categories : options?.cost_categories;
  useEffect(() => {
    if (open) setForm(EMPTY);
  }, [open]);
  useEffect(() => {
    const keys = Object.keys(categories || {});
    if (keys.length && !keys.includes(form.category)) set("category")(keys[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.kind, categories]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/finance?product=${slug}`, { ...form, amount: Number(form.amount) });
      onDone();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Log an entry" subtitle="Revenue and costs, entered by hand."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant="primary" busy={busy} onClick={submit} disabled={!form.category || !form.amount}>Save</Button></>}>
      <Seg value={form.kind} onChange={set("kind")}
        options={[{ value: "revenue", label: "Revenue" }, { value: "cost", label: "Cost" }]} />
      <div className="fin-fields">
        <Select label="Category" value={form.category} onChange={set("category")}
          options={Object.entries(categories || {}).map(([value, label]) => ({ value, label }))} />
        <Field label="Amount" type="number" min="0" step="0.01" prefix="₹" value={form.amount}
          onChange={(e) => set("amount")(e.target.value)} required />
        <Field label="Date" type="date" max={today()} value={form.occurred_on}
          onChange={(e) => set("occurred_on")(e.target.value)} required />
        <Field label="Note" hint="Optional" className="fin-wide" value={form.note}
          onChange={(e) => set("note")(e.target.value)} placeholder="What this was for" />
      </div>
      <ErrorNote error={error} />
    </Modal>
  );
}
