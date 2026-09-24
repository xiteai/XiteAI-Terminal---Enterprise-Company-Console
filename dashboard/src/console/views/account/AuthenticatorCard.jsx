import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Field from "../../../components/Field.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Your authenticator: a 6-digit code from your phone at every sign-in, on top
// of your password. Company code only opens in a session signed in with one.
// The QR code is drawn here in the browser; the secret never leaves this page
// except to the server that issued it.
export default function AuthenticatorCard() {
  const toast = useToast();
  const { me, refresh } = useSession();
  const state = me.authenticator || {};
  const [setup, setSetup] = useState(null);      // {secret, uri, qr}
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [removing, setRemoving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (window.location.hash === "#authenticator") {
      document.getElementById("authenticator")?.scrollIntoView({ block: "start" });
    }
  }, []);

  const start = async () => {
    setBusy(true); setError("");
    try {
      const s = await api.post("/api/account/authenticator/start");
      const qr = await QRCode.toDataURL(s.uri, { margin: 1, width: 200, color: { dark: "#111113", light: "#ffffff" } });
      setSetup({ ...s, qr });
      setCode("");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const confirm = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.post("/api/account/authenticator/confirm", { code });
      setSetup(null); setCode("");
      await refresh();
      toast("Authenticator on. From now on, sign-in asks for a code.");
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  const remove = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.post("/api/account/authenticator/remove", { code, password });
      setRemoving(false); setCode(""); setPassword("");
      await refresh();
      toast("Authenticator removed. Company code stays closed to you until you set one up again.");
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  return (
    <div id="authenticator">
      <Card title="Authenticator" subtitle="A 6-digit code from an app on your phone, asked for at every sign-in. Company code opens only with one.">
        {state.from_env && (
          <p className="acc-note">Yours is set in the server's <code className="code">.env</code> (<code className="code">FOUNDER_TOTP_SECRET</code>). It's on.</p>
        )}

        {!state.from_env && state.on && !removing && (
          <div className="acc-auth">
            <p className="acc-note"><b>On.</b> {state.this_session ? "This session was opened with a code." : "Sign out and back in with a code to open company code."}</p>
            <button className="text-link" onClick={() => { setRemoving(true); setError(""); }}>Remove it</button>
          </div>
        )}

        {!state.from_env && state.on && removing && (
          <form className="acc-form" onSubmit={remove}>
            <p className="acc-note">If you lost your phone, ask HR or someone above you to reset it instead.</p>
            <Field label="Your password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <Field label="A current code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="6 digits" />
            {error && <p className="form-error">{error}</p>}
            <div className="acc-row">
              <Button variant="quiet" onClick={() => setRemoving(false)}>Keep it</Button>
              <Button type="submit" variant="danger" busy={busy} disabled={!password || code.length !== 6}>Remove</Button>
            </div>
          </form>
        )}

        {!state.from_env && !state.on && !setup && (
          <div className="acc-auth">
            <p className="acc-note">Not set up. Takes a minute with Google Authenticator, Microsoft Authenticator or any authenticator app.</p>
            {error && <p className="form-error">{error}</p>}
            <Button variant="primary" busy={busy} onClick={start}>Set it up</Button>
          </div>
        )}

        {setup && (
          <form className="acc-setup" onSubmit={confirm}>
            <img className="acc-qr" src={setup.qr} alt="QR code for your authenticator app" width={200} height={200} />
            <div className="acc-form">
              <p className="acc-note">1. In your authenticator app, add an account and scan this code.</p>
              <p className="acc-note">Can't scan? Enter this key instead: <code className="code acc-key">{setup.secret.replace(/(.{4})/g, "$1 ").trim()}</code></p>
              <p className="acc-note">2. Type the 6 digits the app shows now.</p>
              <Field label="Code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} autoFocus
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="6 digits" />
              {error && <p className="form-error">{error}</p>}
              <div className="acc-row">
                <Button variant="quiet" onClick={() => setSetup(null)}>Cancel</Button>
                <Button type="submit" variant="primary" busy={busy} disabled={code.length !== 6}>Turn it on</Button>
              </div>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
