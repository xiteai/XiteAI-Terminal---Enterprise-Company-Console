import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Modal from "../../../components/Modal.jsx";
import Switch from "../../../components/Switch.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Sample data so every panel has something to show before real data arrives:
// XOS1 installs, a demo second product, a demo team and tickets. Showing it
// is a switch; removing it for good is a separate, confirmed step.
export default function DemoData() {
  const toast = useToast();
  const { me, refresh } = useSession();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const show = async (on) => {
    setBusy(true);
    try { await api.put("/api/settings/demo", { show: on }); await refresh(); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const run = async (load) => {
    setBusy(true);
    try {
      const r = load ? await api.post("/api/demo") : await api.del("/api/demo");
      toast(load ? `Loaded ${r.installs} demo installs and users, and ${r.people} demo people.` : `Removed ${r.installs} installs, ${r.tickets} tickets and ${r.people} people.`);
      setConfirm(false);
      await refresh();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Card title="Demo data" subtitle="Every demo row is tagged Demo. Demo people can never sign in.">
      {me.has_demo ? (
        <div className="acc-demo">
          <label className="acc-demo-row">
            <span>
              <b>Show demo data</b>
              <small>{me.show_demo ? "Demo data shows beside real data everywhere." : "Hidden. Only real data shows. Switch it on any time."}</small>
            </span>
            <Switch checked={me.show_demo} disabled={busy} onChange={show} label="Show demo data" />
          </label>
          <div className="acc-demo-row">
            <span>
              <b>Remove it for good</b>
              <small>Deletes every demo install, ticket, person and the demo product. It won't come back on restart.</small>
            </span>
            <Button variant="danger" onClick={() => setConfirm(true)}>Remove</Button>
          </div>
        </div>
      ) : (
        <div className="acc-demo-row">
          <span>
            <b>No demo data loaded</b>
            <small>Load it to see the console with a full team, a second product and a few hundred installs.</small>
          </span>
          <Button variant="ghost" busy={busy} onClick={() => run(true)}>Load demo data</Button>
        </div>
      )}
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Remove all demo data?"
        subtitle="Demo installs, check-ins, tickets, demo people and the demo product go. Real data is untouched. To only hide it, use the switch instead."
        footer={<><Button variant="quiet" onClick={() => setConfirm(false)}>Cancel</Button>
          <Button variant="danger" className="btn-danger-solid" busy={busy} onClick={() => run(false)}>Remove for good</Button></>} />
    </Card>
  );
}
