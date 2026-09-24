import { useEffect, useState } from "react";
import { api } from "../../../../lib/api.js";
import Button from "../../../../components/Button.jsx";
import Modal from "../../../../components/Modal.jsx";
import { useToast } from "../../../../components/Toast.jsx";

// A temporary password, shown once. They must choose their own at next sign-in.
export default function ResetPasswordModal({ open, person, onClose }) {
  const toast = useToast();
  const [temp, setTemp] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (!open) setTemp(null); }, [open]);
  const go = async () => {
    setBusy(true);
    try { setTemp((await api.post(`/api/people/${person.id}/reset-password`)).temp_password); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(temp); toast("Copied."); } catch { toast.info("Select it and copy by hand."); }
  };
  return (
    <Modal open={open} onClose={onClose} title={temp ? "Temporary password" : `Reset ${person?.preferred_name || ""}'s password?`}
      subtitle={temp
        ? "Give this to them privately. It's shown once. They'll set their own when they sign in."
        : "Their current password stops working and they're signed out everywhere."}
      footer={temp
        ? <Button variant="primary" onClick={onClose}>Done</Button>
        : <><Button variant="quiet" onClick={onClose}>Cancel</Button><Button variant="primary" icon="key" busy={busy} onClick={go}>Reset</Button></>}>
      {temp && (
        <div className="md-secret">
          <code className="mono">{temp}</code>
          <button onClick={copy}>Copy</button>
        </div>
      )}
    </Modal>
  );
}
