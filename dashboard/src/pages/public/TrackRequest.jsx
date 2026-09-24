import { useState } from "react";
import { api } from "../../lib/api.js";
import { ago } from "../../lib/format.js";
import Button from "../../components/Button.jsx";
import Field from "../../components/Field.jsx";

const STAGE = { open: "Received, not picked up yet", in_progress: "Someone is working on it", resolved: "Resolved", closed: "Closed" };

// Follow up on a request with its reference and the email you used.
export default function TrackRequest() {
  const [ref, setRef] = useState("");
  const [email, setEmail] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const look = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try { setResult(await api.post("/api/public/tickets/lookup", { ref, email })); }
    catch (err) { setResult(null); setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="pub-track">
      <span className="eyebrow">Already wrote to us?</span>
      <form className="pub-track-form" onSubmit={look}>
        <Field label="Reference" placeholder="XS-123456" value={ref} onChange={(e) => setRef(e.target.value.toUpperCase())} />
        <Field label="Email you used" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Button type="submit" variant="ghost" busy={busy}>Check</Button>
      </form>
      {error && <p className="form-error">{error}</p>}
      {result && (
        <dl className="rows pub-track-result">
          <div><dt>Request</dt><dd>{result.subject}</dd></div>
          <div><dt>Where it is</dt><dd>{STAGE[result.status]}</dd></div>
          <div><dt>Last update</dt><dd>{ago(result.updated_at)}</dd></div>
        </dl>
      )}
    </div>
  );
}
