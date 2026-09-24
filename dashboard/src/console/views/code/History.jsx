import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";

const VERB = { A: "added", M: "changed", D: "deleted", R: "renamed", C: "copied" };

// Everything that ever changed, in plain words: from change requests here and
// from people pushing to GitHub directly. Checkpoints mark the safe points.
export default function History() {
  const { rid, repo } = useRepo();
  const navigate = useNavigate();
  const toast = useToast();
  const [pages, setPages] = useState([0]);
  const cps = useData(() => api.get(`/api/code/${rid}/checkpoints`), [rid, repo.head_sha]);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const d = await api.post(`/api/code/${rid}/checkpoints`, { name, note });
      cps.mutate(() => d);
      setSaving(false); setName(""); setNote("");
      toast(d.items[0].on_github ? "Checkpoint saved, here and on GitHub." : "Checkpoint saved here. GitHub didn't take it.");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="hs">
      <section className="hs-cps">
        <div className="hs-cps-head">
          <h3 className="t-h3">Checkpoints</h3>
          <span className="t-note">Named safe points. Compare anything with one, or put a file back to how it was there.</span>
          {cps.data?.can_create && <Button size="sm" onClick={() => setSaving(true)}>Save a checkpoint</Button>}
        </div>
        {cps.data && cps.data.items.length === 0 && <p className="t-note">None yet.</p>}
        {cps.data?.items.length > 0 && (
          <ul className="hs-cp-list">
            {cps.data.items.map((c) => (
              <li key={c.name}>
                <b className="mono">{c.name}</b>
                <span className="t-note">{c.note && `${c.note} · `}{c.by}, <span title={dateTime(c.at)}>{ago(c.at)}</span>{c.on_github ? "" : " · not on GitHub"}</span>
                <button className="text-link" onClick={() => navigate(`/console/code/history/compare/${encodeURIComponent(c.name)}`)}>Compare with now</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        {pages.map((skip) => <Page key={skip} skip={skip} last={skip === pages[pages.length - 1]}
          onMore={(next) => setPages((p) => [...p, next])} />)}
      </section>

      <Modal open={saving} onClose={() => setSaving(false)} title="Save a checkpoint" width={460}
        subtitle="A name for the code exactly as it is now. It's kept here and on GitHub, and never moves."
        footer={<Button variant="primary" busy={busy} disabled={name.trim().length < 2} onClick={save}>Save</Button>}>
        <div className="code-form">
          <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="before-memory-rewrite" maxLength={49}
            hint="Letters, numbers, dots, dashes. Spaces become dashes." />
          <Field label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Last version before we changed how memory works" maxLength={300} />
          {err && <p className="form-error">{err}</p>}
        </div>
      </Modal>
    </div>
  );
}

function Page({ skip, last, onMore }) {
  const { rid, repo } = useRepo();
  const { data, error, reload } = useData(() => api.get(`/api/code/${rid}/history${qs({ skip })}`), [rid, repo.head_sha, skip]);
  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (!data) return <div className="drawer-wait"><Spinner delay={300} /></div>;
  if (skip === 0 && data.commits.length === 0) return <Empty title="Nothing in the history is shared with you yet." />;
  return (
    <>
      <ol className="hs-list">
        {data.commits.map((c) => (
          <li key={c.sha} className="hs-item">
            <Link className="hs-subject" to={`/console/code/history/${c.sha}`}>{c.subject}</Link>
            <p className="hs-meta">
              <b>{c.author}</b> · <span title={dateTime(c.at)}>{ago(c.at)}</span> · <span className="mono">{c.short}</span>
              {c.change && <> · <Link className="text-link" to={`/console/code/changes/${c.change.id}`}>change #{c.change.id}</Link></>}
              {c.checkpoint && <> · checkpoint <b className="mono">{c.checkpoint}</b></>}
            </p>
            <p className="hs-files">
              {c.files.slice(0, 4).map((f) => <span key={f.path}>{VERB[f.status] || "changed"} <span className="mono">{f.path}</span></span>)}
              {c.files.length > 4 && <span>and {c.files.length - 4} more</span>}
              {c.hidden_files > 0 && <span className="faint">{c.hidden_files} file{c.hidden_files === 1 ? "" : "s"} not shared with you</span>}
            </p>
          </li>
        ))}
      </ol>
      {last && data.more && <div className="hs-more"><Button onClick={() => onMore(data.next)}>Older</Button></div>}
    </>
  );
}
