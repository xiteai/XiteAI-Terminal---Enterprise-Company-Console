import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Field from "../../../components/Field.jsx";
import { useToast } from "../../../components/Toast.jsx";

export default function PasswordCard() {
  const toast = useToast();
  const { me } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (me.user.source === "env") {
    return (
      <Card title="Password">
        <p className="acc-note">Your password lives in the server's <code className="code">.env</code> file. Change <code className="code">FOUNDER_PASSWORD</code> there and restart; every other session signs out.</p>
        {me.founder_totp
          ? <p className="acc-note">An authenticator code is required at sign-in.</p>
          : <p className="acc-note">Add <code className="code">FOUNDER_TOTP_SECRET</code> to <code className="code">.env</code> to require an authenticator code before going online.</p>}
      </Card>
    );
  }
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/account/password", { current, new: next });
      setCurrent("");
      setNext("");
      toast("Password changed. Your other sessions were signed out.");
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return (
    <Card title="Password">
      <form className="acc-form" onSubmit={save}>
        <Field label="Current password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
        <Field label="New password" type="password" hint="12+ characters, upper and lower case, and a number." value={next}
          onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
        {error && <p className="form-error">{error}</p>}
        <Button type="submit" variant="primary" busy={busy} disabled={!current || !next}>Change password</Button>
      </form>
    </Card>
  );
}
