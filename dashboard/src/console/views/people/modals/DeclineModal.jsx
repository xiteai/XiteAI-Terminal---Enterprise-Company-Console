import { useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Field from "../../../../components/Field.jsx";
import Modal from "../../../../components/Modal.jsx";
import { useToast } from "../../../../components/Toast.jsx";

export default function DeclineModal({ open, person, onClose, onDone }) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    try {
      await api.post(`/api/requests/${person.id}/decline`, { note });
      toast(`Declined. ${person.preferred_name} will see your note.`);
      setNote("");
      onDone();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title={`Decline ${person?.preferred_name || ""}'s request?`}
      subtitle="They'll see that it wasn't approved, and your note if you leave one."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="danger" icon="x" busy={busy} onClick={go}>Decline</Button></>}>
      <Field textarea label="Note to them (optional)" placeholder="e.g. We've filled this role for now." value={note} onChange={(e) => setNote(e.target.value)} data-autofocus />
    </Modal>
  );
}
