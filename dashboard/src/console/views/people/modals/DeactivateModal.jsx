import { useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Field from "../../../../components/Field.jsx";
import Modal from "../../../../components/Modal.jsx";
import { useToast } from "../../../../components/Toast.jsx";

// Deactivating signs them out everywhere and hands their reports to their manager.
export default function DeactivateModal({ open, rehire, person, onClose, onDone }) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    try {
      if (rehire) await api.post(`/api/people/${person.id}/reactivate`);
      else await api.post(`/api/people/${person.id}/deactivate`, { note });
      toast(rehire ? `${person.preferred_name} can sign in again.` : `${person.preferred_name} has been deactivated.`);
      setNote("");
      onDone();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} tone={rehire ? undefined : "danger"}
      title={rehire ? `Bring back ${person?.preferred_name || ""}?` : `Deactivate ${person?.preferred_name || ""}?`}
      subtitle={rehire
        ? "They'll be able to sign in again with their existing password."
        : "They're signed out everywhere and can't sign in. Anyone who reported to them moves to their manager. The Founder is told."}
      footer={<>
        <Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant={rehire ? "primary" : "danger"} className={rehire ? "" : "btn-danger-solid"} busy={busy} onClick={go}>
          {rehire ? "Reactivate" : "Deactivate"}
        </Button>
      </>}>
      {!rehire && <Field textarea label="Reason (kept on record)" value={note} onChange={(e) => setNote(e.target.value)} data-autofocus />}
    </Modal>
  );
}
