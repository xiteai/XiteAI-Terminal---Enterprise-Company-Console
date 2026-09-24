import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import Modal from "../../../components/Modal.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";
import Diff from "./Diff.jsx";

const VERB = { A: "added", M: "changed", D: "deleted", R: "renamed", C: "copied" };

// One past change (or everything since a checkpoint): what it did, file by
// file, only for files you can read. And the way to take it back.
export default function CommitView({ compare = false }) {
  const { sha, base } = useParams();
  const { rid, repo } = useRepo();
  const navigate = useNavigate();
  const toast = useToast();
  const url = compare ? `/api/code/${rid}/compare${qs({ base })}` : `/api/code/${rid}/commits/${sha}`;
  const { data, error, reload } = useData(() => api.get(url), [url, repo.head_sha]);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  const undo = async () => {
    setBusy(true);
    try {
      const d = await api.post(`/api/code/${rid}/commits/${data.sha}/undo`);
      toast(`Change #${d.id} takes it back. It goes through review like any change.`);
      navigate(`/console/code/changes/${d.id}`);
    } catch (e) { toast.error(e.message); setAsking(false); } finally { setBusy(false); }
  };

  const files = data?.files || [];
  const hidden = files.find((f) => f.hidden_count)?.hidden_count || 0;
  return (
    <div className="cd">
      <Link to="/console/code/history" className="cd-back"><Icon name="arrowLeft" size={15} /> History</Link>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <>
          <header className="cd-head">
            {compare
              ? <h2 className="t-h2">Since <span className="mono">{decodeURIComponent(base)}</span></h2>
              : <h2 className="t-h2">{data.subject}</h2>}
            <p className="cd-sub">
              {compare ? `${data.count} file${data.count === 1 ? "" : "s"} changed since that checkpoint.` : <>
                <b>{data.author}</b> · {dateTime(data.at)} · <span className="mono">{data.short}</span>
                {data.change && <> · <Link className="text-link" to={`/console/code/changes/${data.change.id}`}>change #{data.change.id}</Link></>}
                {data.checkpoint && <> · checkpoint <b className="mono">{data.checkpoint}</b></>}
              </>}
            </p>
            {!compare && data.body && <p className="cd-body">{data.body}</p>}
          </header>

          {!compare && data.can_undo && (
            <div className="cm-undo">
              <span className="t-note">Take this change back out. Anything written since stays; if later work touched the same lines, it tells you instead of guessing.</span>
              <Button onClick={() => setAsking(true)}>Undo this change</Button>
            </div>
          )}

          <section className="cd-files">
            {files.filter((f) => f.path).map((f) => (
              <div key={f.path} className="cd-file">
                <div className="cd-file-head">
                  <span className="mono">{f.path}</span>
                  <span className="t-note">{VERB[f.status] || "changed"}{f.from ? ` from ${f.from}` : ""}{f.added !== undefined && ` · +${f.added} −${f.removed}`}</span>
                </div>
                {f.binary ? <p className="t-note">Not a text file.</p> : <Diff file={f} />}
              </div>
            ))}
            {hidden > 0 && <p className="t-note">{hidden} more file{hidden === 1 ? "" : "s"} in this change {hidden === 1 ? "isn't" : "aren't"} shared with you.</p>}
          </section>
        </>
      )}
      <Modal open={asking} onClose={() => setAsking(false)} title="Undo this change?" width={480}
        subtitle="This opens a new change that takes it back. Nothing happens to the code until that change is approved and merged."
        footer={<Button variant="primary" busy={busy} onClick={undo}>Open the undo</Button>} />
    </div>
  );
}
