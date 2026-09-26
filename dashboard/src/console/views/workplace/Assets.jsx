import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import FileCard from "./FileCard.jsx";
import RequestList from "./RequestList.jsx";

const ITEMS = [
  { value: "laptop", label: "Laptop" },
  { value: "monitor", label: "Monitor" },
  { value: "phone", label: "Phone" },
  { value: "desk", label: "Desk and chair" },
  { value: "peripherals", label: "Keyboard, mouse, headset" },
  { value: "other", label: "Other" },
];
const ACTIONS = [{ value: "new", label: "New — I don't have one" }, { value: "replacement", label: "Replacement — lost or damaged" }];

const EMPTY = { category: "laptop", quantity: 1, asset_action: "new", note: "" };

// Hardware you need to do the job — new kit, or a replacement for something
// lost or broken. A replacement can carry a fine, set when it's decided.
export default function Assets() {
  const mine = useData(() => api.get("/api/workplace/requests?kind=asset"), []);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const isReplacement = form.asset_action === "replacement";

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workplace/requests/asset", { ...form, quantity: Number(form.quantity) });
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
      <PageHeader title="Assets" subtitle="Ask for the kit you need." />

      <FileCard
        title="Request kit"
        subtitle={isReplacement ? "Replacements can carry a fine for loss or damage — that's set when it's decided."
          : "More than ten of anything needs a conversation first."}
        error={error}
        busy={busy}
        onSubmit={submit}
        submitLabel="Send for approval"
      >
        <div className="wp-wide"><Seg value={form.asset_action} onChange={set("asset_action")} options={ACTIONS} /></div>
        <Select label="What" value={form.category} onChange={set("category")} options={ITEMS} />
        <Field label="How many" type="number" min="1" max="10" value={form.quantity}
          onChange={(e) => set("quantity")(e.target.value)} required />
        <Field label={isReplacement ? "What happened to it" : "Why you need it"} className="wp-wide"
          value={form.note} onChange={(e) => set("note")(e.target.value)}
          placeholder={isReplacement ? "Dropped it, screen's cracked" : "Second screen for review work"} required />
      </FileCard>

      <Card title="Your requests" flush>
        <ErrorNote error={mine.error} onRetry={mine.reload} />
        <RequestList items={mine.data?.items || []} onWithdraw={withdraw}
          empty="You haven't asked for anything yet." />
      </Card>
    </div>
  );
}
