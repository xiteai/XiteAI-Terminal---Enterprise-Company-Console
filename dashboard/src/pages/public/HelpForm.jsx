import { useState } from "react";
import { api } from "../../lib/api.js";
import Button from "../../components/Button.jsx";
import Field from "../../components/Field.jsx";
import Seg from "../../components/Seg.jsx";

const KINDS = [
  { value: "support", label: "Something's wrong" },
  { value: "feedback", label: "An idea" },
  { value: "data_access", label: "Show me my data" },
  { value: "data_delete", label: "Delete my data" },
];
const EMPTY = { name: "", email: "", install_code: "", subject: "", message: "", website: "" };

// No card: plain fields, one ink button, and the outcome in a single live
// line beside it, as on the site's contact form.
export default function HelpForm() {
  const [kind, setKind] = useState("support");
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api.post("/api/public/tickets", { ...form, kind });
      setSent(r.ref);
      setForm(EMPTY);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="pub-form">
      <Seg size="sm" value={kind} onChange={setKind} options={KINDS} label="What is this about?" />
      <Field label="Your name" value={form.name} onChange={set("name")} autoComplete="name" />
      <Field label="Email" type="email" required value={form.email} onChange={set("email")} autoComplete="email" placeholder="you@company.com" />
      <Field label={<>Install code <span className="opt">(optional)</span></>} placeholder="ABCD-2345"
        hint="In XOS1, Settings → About. It finds your install without us needing your name."
        value={form.install_code} onChange={set("install_code")} />
      <Field label="Message" textarea required
        placeholder={kind === "support" ? "What happened, and what did you expect?" : kind === "feedback" ? "What would make XOS1 better for you?" : "Anything we should know?"}
        value={form.message} onChange={set("message")} />
      <input className="pub-hp" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} aria-hidden />
      <div className="pub-send">
        <Button type="submit" variant="primary" busy={busy}>Send</Button>
        <p aria-live="polite" className={error ? "form-error" : "t-note"}>
          {error || (sent && <>Got it. Your reference is <b className="mono">{sent}</b>; keep it with your email to check progress.</>)}
        </p>
      </div>
    </form>
  );
}
