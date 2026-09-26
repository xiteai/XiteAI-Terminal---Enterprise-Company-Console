import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Seg from "../../../components/Seg.jsx";
import { KIND_NOUN, amount, detail } from "./labels.js";
import RequestList from "./RequestList.jsx";

// What's waiting on you. The server only sends what this level can actually
// decide — the permission for that kind, and a level above whoever filed it —
// so anything visible here is something you're allowed to act on.
export default function Approvals() {
  const [kind, setKind] = useState("all");
  const pending = useData(() => api.get("/api/workplace/requests?scope=approvals"), []);
  const [asking, setAsking] = useState(null);   // { request, approve }
  const [note, setNote] = useState("");
  const [fine, setFine] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const items = pending.data?.items || [];
  const shown = kind === "all" ? items : items.filter((r) => r.kind === kind);
  const count = (k) => items.filter((r) => r.kind === k).length;
  const isReplacement = asking?.request.kind === "asset" && asking.request.asset_action === "replacement";

  const open = (request, approve) => {
    setAsking({ request, approve });
    setNote("");
    setFine("");
    setError(null);
  };

  const decide = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/workplace/requests/${asking.request.id}/decide`,
        { approve: asking.approve, note, fine: isReplacement && fine ? Number(fine) : undefined });
      setAsking(null);
      pending.reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      <PageHeader title="Approvals" subtitle="Everything waiting on you." />

      <Seg
        value={kind}
        onChange={setKind}
        label="Kind"
        options={[
          { value: "all", label: "All", count: items.length },
          { value: "leave", label: "Leave", count: count("leave") },
          { value: "expense", label: "Expenses", count: count("expense") },
          { value: "asset", label: "Assets", count: count("asset") },
        ]}
      />

      <Card flush>
        <ErrorNote error={pending.error} onRetry={pending.reload} />
        <RequestList items={shown} showWho onDecide={open}
          empty={items.length ? "Nothing of that kind is waiting." : "Nothing is waiting on you."} />
      </Card>

      <Modal
        open={Boolean(asking)}
        onClose={() => setAsking(null)}
        title={asking?.approve ? "Approve this?" : "Decline this?"}
        subtitle={asking && `${asking.request.staff?.name}'s ${KIND_NOUN[asking.request.kind]}`}
        footer={
          <>
            <Button variant="quiet" onClick={() => setAsking(null)}>Cancel</Button>
            <Button variant={asking?.approve ? "primary" : "danger"} busy={busy} onClick={decide}>
              {asking?.approve ? "Approve" : "Decline"}
            </Button>
          </>
        }
      >
        {asking && (
          <div className="wp-decide">
            <p className="wp-decide-what">{asking.request.title}</p>
            <p className="t-note">{detail(asking.request)} · {amount(asking.request)}</p>
            {asking.request.note && <p className="wp-decide-note">“{asking.request.note}”</p>}
            {isReplacement && asking.approve && (
              <Field label="Fine" hint="Optional — charged for loss or damage" prefix="₹" type="number" min="0" step="0.01"
                value={fine} onChange={(e) => setFine(e.target.value)} />
            )}
            <Field
              label="Note"
              hint={asking.approve ? "Optional. They'll see it." : "Say why. They'll see it."}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              textarea
              rows={3}
            />
            <ErrorNote error={error} />
          </div>
        )}
      </Modal>
    </div>
  );
}
