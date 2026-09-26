import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Select from "../../../components/Select.jsx";
import FileCard from "./FileCard.jsx";
import RequestList from "./RequestList.jsx";

const CATEGORIES = [
  { value: "travel", label: "Travel" },
  { value: "meals", label: "Meals" },
  { value: "software", label: "Software" },
  { value: "hardware", label: "Hardware" },
  { value: "training", label: "Training" },
  { value: "other", label: "Other" },
];

const EMPTY = { category: "travel", amount: "", spent_on: "", note: "" };
const today = () => new Date().toISOString().slice(0, 10);

// Money you've spent on the company's behalf, and where each claim got to.
export default function Expenses() {
  const mine = useData(() => api.get("/api/workplace/requests?kind=expense"), []);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workplace/requests/expense", { ...form, amount: Number(form.amount) });
      setForm(EMPTY);
      mine.reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (r) => {
    await api.post(`/api/workplace/requests/${r.id}/withdraw`);
    mine.reload();
  };

  return (
    <div className="stack">
      <PageHeader title="Expenses" subtitle="Claim back what you spent for work." />

      <FileCard
        title="New claim"
        subtitle="Claims close six months after the money was spent."
        error={error}
        busy={busy}
        onSubmit={submit}
        submitLabel="Send for approval"
      >
        <Select label="What for" value={form.category} onChange={set("category")} options={CATEGORIES} />
        <Field label="Amount" type="number" min="1" step="0.01" prefix="₹" inputMode="decimal"
          value={form.amount} onChange={(e) => set("amount")(e.target.value)} required />
        <Field label="Spent on" type="date" max={today()} value={form.spent_on}
          onChange={(e) => set("spent_on")(e.target.value)} required />
        <Field label="What it was" value={form.note} onChange={(e) => set("note")(e.target.value)}
          placeholder="Client dinner, Mumbai" required />
      </FileCard>

      <Card title="Your claims" flush>
        <ErrorNote error={mine.error} onRetry={mine.reload} />
        <RequestList items={mine.data?.items || []} onWithdraw={withdraw}
          empty="You haven't claimed anything yet." />
      </Card>
    </div>
  );
}
