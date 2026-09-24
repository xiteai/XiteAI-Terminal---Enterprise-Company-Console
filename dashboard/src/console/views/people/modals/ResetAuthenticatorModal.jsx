import { useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Modal from "../../../../components/Modal.jsx";
import { useToast } from "../../../../components/Toast.jsx";

// For someone who lost their phone: their authenticator is cleared and they're
// signed out everywhere. They set a new one up from Account after signing in.
export default function ResetAuthenticatorModal({ open, person, onClose }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    try {
      await api.post(`/api/people/${person.id}/reset-authenticator`);
      toast(`${person.preferred_name}'s authenticator was reset. They were told.`);
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title={`Reset ${person?.preferred_name || ""}'s authenticator?`}
      subtitle="Only if they lost their phone or changed it. They're signed out everywhere, and company code stays closed to them until they set up a new one."
      footer={<><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="primary" busy={busy} onClick={go}>Reset</Button></>} />
  );
}
