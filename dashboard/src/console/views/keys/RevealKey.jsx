import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import Modal from "../../../components/Modal.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Reading a key in full: password again, and the founder is told. The key is
// held in React state only — never written to storage, and dropped the moment
// this closes.
export default function RevealKey({ provider, needsCode, onClose }) {
  const toast = useToast();
  const [form, setForm] = useState({ password: "", code: "" });
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => () => setKey(""), []);

  const go = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post(`/api/ai-keys/${provider.key}/reveal`, form);
      setKey(r.key);
      setForm({ password: "", code: "" });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(key);
      toast("Copied. It's on your clipboard now — paste it somewhere safe.");
    } catch {
      toast.error("Couldn't reach the clipboard.");
    }
  };

  return (
    <Modal open onClose={onClose} title={`${provider.label} key`}
      subtitle={key ? "On screen until you close this." : "Your password again, because this shows the whole key."}
      footer={key
        ? <><Button variant="quiet" onClick={onClose}>Done</Button>
          <Button variant="primary" icon="check" onClick={copy}>Copy</Button></>
        : <><Button variant="quiet" onClick={onClose}>Cancel</Button>
          <Button variant="primary" busy={busy} onClick={go} disabled={!form.password}>Show key</Button></>}>
      {key ? (
        <>
          <p className="keys-revealed mono">{key}</p>
          <p className="callout"><Icon name="lock" size={16} />
            <span>This read is in the audit log with your name on it, and the founder has been told.</span></p>
        </>
      ) : (
        <>
          <Field label="Your password" type="password" autoComplete="current-password" value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} />
          {needsCode && (
            <div style={{ marginTop: 12 }}>
              <Field label="Authenticator code" inputMode="numeric" value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} />
            </div>
          )}
          <ErrorNote error={error} />
        </>
      )}
    </Modal>
  );
}
