import { useEffect, useState } from "react";
import { api } from "../../../lib/api.js";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";

// Paste a new key, prove it's you, and the server does the rest: the provider
// must accept the key, then Cloudflare must take it. "Test only" checks a key
// without saving anything, which works before Cloudflare is connected too.
export default function ReplaceKey({ provider, needsCode, cloudflare, onClose, onDone }) {
  const [key, setKey] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(null);
  const [note, setNote] = useState(null);

  useEffect(() => {
    setKey(""); setPassword(""); setCode(""); setNote(null); setBusy(null);
  }, [provider]);

  const test = async () => {
    setBusy("test"); setNote(null);
    try {
      const r = await api.post(`/api/ai-keys/${provider.key}/test`, { key });
      setNote({ ok: r.ok, text: r.message });
    } catch (e) { setNote({ ok: false, text: e.message }); }
    finally { setBusy(null); }
  };

  const replace = async () => {
    setBusy("save"); setNote(null);
    try {
      const r = await api.post(`/api/ai-keys/${provider.key}`, { key, password, code });
      setKey(""); setPassword("");
      onDone(r);
    } catch (e) { setNote({ ok: false, text: e.message }); }
    finally { setBusy(null); }
  };

  const ready = key.trim().length >= 16;
  return (
    <Modal open={Boolean(provider)} onClose={onClose} width={500}
      title={provider ? `Replace the ${provider.label} key` : ""}
      subtitle="Every XOS1 install switches to the new key within seconds. No update needed."
      footer={
        <>
          <Button variant="quiet" onClick={test} busy={busy === "test"} disabled={!ready || Boolean(busy)}>Test only</Button>
          <Button variant="primary" onClick={replace} busy={busy === "save"}
            disabled={!ready || !password || (needsCode && code.length !== 6) || !cloudflare || Boolean(busy)}>
            Replace key
          </Button>
        </>
      }>
      {provider && (
        <div className="keys-form">
          <Field label="New key" type="password" autoComplete="off" spellCheck={false} value={key}
            onChange={(e) => setKey(e.target.value)} placeholder={`Paste the ${provider.label} key`}
            hint={`Tested with ${provider.label} first. If it's refused, nothing changes for users.`} />
          <Field label="Your password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} hint="Asked every time a key changes." />
          {needsCode && (
            <Field label="Authenticator code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="6 digits" />
          )}
          {note && <p className={note.ok ? "keys-note" : "form-error"} role="status">{note.text}</p>}
          <p className="t-note">
            After this, nobody can see the key again: not on this page, not in Cloudflare. You can only replace it.
            {!cloudflare && " Replacing is off until Cloudflare is connected; testing works now."}
          </p>
        </div>
      )}
    </Modal>
  );
}
