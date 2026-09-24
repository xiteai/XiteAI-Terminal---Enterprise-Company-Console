import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";

// An edit goes into a change request: one you're still writing, or a new one.
// Several edits (even in different files) can share one change.
export default function SaveToChange({ payload, onClose, onSaved }) {
  const { rid } = useRepo();
  const { me } = useSession();
  const toast = useToast();
  const [mine, setMine] = useState(null);
  const [choice, setChoice] = useState("new");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!payload) return;
    setErr(null); setTitle("");
    api.get(`/api/code/${rid}/changes`).then((d) => {
      const open = d.items.filter((c) => c.author_id === me.user.id && ["draft", "changes", "conflict"].includes(c.status));
      setMine(open);
      setChoice(open[0] ? String(open[0].id) : "new");
    }).catch((e) => setErr(e.message));
  }, [payload, rid, me.user.id]);

  const save = async () => {
    setBusy(true); setErr(null);
    try {
      let cid = Number(choice);
      if (choice === "new") cid = (await api.post(`/api/code/${rid}/changes`, { title })).id;
      await api.put(`/api/code/${rid}/changes/${cid}/files`, payload);
      toast(<span>Saved in change #{cid}. <Link className="text-link" to={`/console/code/changes/${cid}`}>Open it</Link> to send it for review.</span>);
      onSaved(cid);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <Modal open={Boolean(payload)} onClose={onClose} title="Add to a change" width={480}
      subtitle="Nothing reaches GitHub until someone who answers for this code approves it."
      footer={<Button variant="primary" onClick={save} busy={busy} disabled={choice === "new" && title.trim().length < 3}>Save</Button>}>
      <div className="code-form">
        {mine?.length > 0 && (
          <div className="code-choices" role="radiogroup" aria-label="Which change">
            {mine.map((c) => (
              <label key={c.id} className="code-choice">
                <input type="radio" name="change" checked={choice === String(c.id)} onChange={() => setChoice(String(c.id))} />
                <span><b>#{c.id} {c.title}</b><small>{c.files} file{c.files === 1 ? "" : "s"} so far</small></span>
              </label>
            ))}
            <label className="code-choice">
              <input type="radio" name="change" checked={choice === "new"} onChange={() => setChoice("new")} />
              <span><b>A new change</b></span>
            </label>
          </div>
        )}
        {choice === "new" && (
          <Field label="What does this change do?" value={title} onChange={(e) => setTitle(e.target.value)}
            placeholder="Fix the memory recall for birthdays" maxLength={120} autoFocus />
        )}
        {err && <p className="form-error" role="alert">{err}</p>}
      </div>
    </Modal>
  );
}
