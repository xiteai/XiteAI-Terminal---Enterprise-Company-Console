import { useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Erasing is permanent, so you type the install's code to confirm it.
export default function EraseInstall({ open, install, onClose, onDone }) {
  const toast = useToast();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const ok = typed.trim().toUpperCase() === install?.code;
  const go = async () => {
    setBusy(true);
    try {
      await api.del(`/api/installs/${install.id}`);
      toast(`${install.code} erased.`);
      onClose();
      onDone();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} tone="danger" title="Erase this install?"
      subtitle="Every record for it is deleted for good. If the app checks in again, it arrives as a new install."
      footer={<>
        <Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant="danger" className="btn-danger-solid" icon="trash" disabled={!ok} busy={busy} onClick={go}>Erase for good</Button>
      </>}>
      <Field label={`Type ${install?.code} to confirm`} value={typed} onChange={(e) => setTyped(e.target.value)} data-autofocus autoComplete="off" />
    </Modal>
  );
}
