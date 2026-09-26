import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "../../lib/motion.js";
import { api, ApiError } from "../../lib/api.js";
import { date } from "../../lib/format.js";
import { useData } from "../../lib/useData.js";
import Button from "../../components/Button.jsx";
import { ErrorNote } from "../../components/Empty.jsx";
import Field from "../../components/Field.jsx";
import Spinner from "../../components/Spinner.jsx";
import EntryNav from "../shared/EntryNav.jsx";
import "../shared/Entry.css";
import "./Careers.css";

const rise = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } };

// Blank-line paragraphs; a run of "- " lines becomes a list. No markdown
// library for four punctuation marks.
function Description({ text }) {
  const blocks = (text || "").split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  return (
    <div className="cr-desc">
      {blocks.map((block, i) => {
        const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
        if (lines.every((l) => l.startsWith("- "))) {
          return <ul key={i}>{lines.map((l) => <li key={l}>{l.slice(2)}</li>)}</ul>;
        }
        return <p key={i}>{block}</p>;
      })}
    </div>
  );
}

function ApplyForm({ roleId, onDone }) {
  const [form, setForm] = useState({ name: "", email: "", phone: "", portfolio: "", note: "", website: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/careers/roles/${roleId}/apply`, form);
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="cr-apply" onSubmit={submit}>
      <h3 className="t-h3">Apply</h3>
      <input className="pub-hp" tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => set("website")(e.target.value)} aria-hidden="true" />
      <Field label="Full name" value={form.name} onChange={(e) => set("name")(e.target.value)} required />
      <Field label="Email" type="email" value={form.email} onChange={(e) => set("email")(e.target.value)} required />
      <Field label="Phone" hint="Optional" value={form.phone} onChange={(e) => set("phone")(e.target.value)} />
      <Field label="Portfolio or LinkedIn" hint="Optional" placeholder="https://" value={form.portfolio} onChange={(e) => set("portfolio")(e.target.value)} />
      <Field label="Anything you'd like us to know" hint="Optional" textarea rows={4} value={form.note} onChange={(e) => set("note")(e.target.value)} />
      <ErrorNote error={error} />
      <Button type="submit" variant="primary" size="lg" busy={busy} block>Send application</Button>
    </form>
  );
}

export default function RoleDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const role = useData(() => api.get(`/api/careers/roles/${id}`), [id]);
  const [sent, setSent] = useState(false);
  useEffect(() => { if (role.data) document.title = `${role.data.title} · Careers · XiteAI`; }, [role.data]);

  const notFound = role.error instanceof ApiError && role.error.status === 404;

  return (
    <div className="entry pub">
      <EntryNav sub="Careers" links={[{ to: "/careers", label: "All roles" }]} />

      {role.loading && <div className="cr-wait"><Spinner delay={300} /></div>}

      {notFound && (
        <main className="cr-main cr-notfound">
          <h1 className="t-h1">This role isn't open anymore.</h1>
          <p className="t-lede">It may have been filled, or the link's out of date.</p>
          <Link to="/careers" className="pub-secondary">See open roles</Link>
        </main>
      )}

      {role.data && (
        <main className="cr-role">
          <motion.div {...rise} className="cr-role-head">
            <span className="eyebrow">{role.data.department}</span>
            <h1 className="t-display">{role.data.title}</h1>
            <p className="cr-role-meta">{role.data.employment_type} · {role.data.location} · Posted {date(role.data.posted_at)}</p>
          </motion.div>

          <div className="cr-role-body">
            <div>
              <p className="t-lede">{role.data.summary}</p>
              <Description text={role.data.description} />
            </div>
            <div className="cr-apply-panel">
              {sent ? (
                <div className="cr-sent">
                  <h3 className="t-h3">Application sent.</h3>
                  <p className="t-note">We'll reach out if it's a fit. Thanks for your time.</p>
                  <Button variant="quiet" onClick={() => nav("/careers")}>Back to careers</Button>
                </div>
              ) : <ApplyForm roleId={role.data.id} onDone={() => setSent(true)} />}
            </div>
          </div>
        </main>
      )}
    </div>
  );
}
