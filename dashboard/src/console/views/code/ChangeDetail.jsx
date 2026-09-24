import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import Modal from "../../../components/Modal.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { STATUS } from "./Changes.jsx";
import { useRepo } from "./Code.jsx";
import Diff from "./Diff.jsx";

const VERDICT = { approve: "approved", changes: "asked for changes", reject: "rejected", comment: "commented" };

// One change request: what it does, the checks and what to look at twice, the
// diff (only what you may see) with comments on exact lines, the conversation,
// and the one next step you can take.
export default function ChangeDetail() {
  const { cid } = useParams();
  const { rid, choose, reloadRepos } = useRepo();
  const toast = useToast();
  const navigate = useNavigate();
  const [where, setWhere] = useState(null);
  const [whereErr, setWhereErr] = useState(null);

  // A link carries only the number; find its repository first.
  useEffect(() => {
    api.get(`/api/code/changes/${cid}/where`).then((d) => {
      setWhere(d.repo_id);
      if (d.repo_id !== rid) choose(d.repo_id);
    }).catch(setWhereErr);
  }, [cid]); // eslint-disable-line react-hooks/exhaustive-deps

  const { data: c, error, reload, mutate } = useData(
    () => (where ? api.get(`/api/code/${where}/changes/${cid}`) : Promise.resolve(null)), [where, cid]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const base = `/api/code/${where}/changes/${cid}`;

  const act = async (what, path, body, done) => {
    setBusy(what);
    try {
      const next = await api.post(`${base}/${path}`, body);
      mutate(() => next);
      setNote("");
      if (path === "merge") reloadRepos();          // the repository moved to a new commit
      if (done) toast(done);
    } catch (e) { toast.error(e.message); reload(); }
    finally { setBusy(null); setConfirm(null); }
  };
  const drop = async (path) => {
    try { const next = await api.del(`${base}/files?path=${encodeURIComponent(path)}`); mutate(() => next); }
    catch (e) { toast.error(e.message); reload(); }
  };
  const comment = async (payload) => {
    try { const next = await api.post(`${base}/comments`, payload); mutate(() => next); return true; }
    catch (e) { toast.error(e.message); return false; }
  };
  const resolve = async (id) => {
    try { const next = await api.post(`${base}/comments/${id}/resolve`); mutate(() => next); }
    catch (e) { toast.error(e.message); }
  };
  const undo = async () => {
    setBusy("undo");
    try {
      const d = await api.post(`${base}/undo`);
      toast(`Change #${d.id} takes it back. It goes through review like any change.`);
      setConfirm(null);
      navigate(`/console/code/changes/${d.id}`);
    } catch (e) { toast.error(e.message); setConfirm(null); } finally { setBusy(null); }
  };

  const err = whereErr || error;
  return (
    <div className="cd">
      <Link to="/console/code/changes" className="cd-back"><Icon name="arrowLeft" size={15} /> All changes</Link>
      <ErrorNote error={err} onRetry={reload} />
      {!c && !err && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {c && (
        <>
          <header className="cd-head">
            <h2 className="t-h2"><span className="mono faint">#{c.id}</span> {c.title}</h2>
            <p className="cd-sub">
              <b>{STATUS[c.status]}</b> · by {c.author} · started {ago(c.created_at)}
              {c.status === "merged" && <> · merged by {c.merged_by} <span title={dateTime(c.merged_at)}>{ago(c.merged_at)}</span></>}
            </p>
            {c.body && <p className="cd-body">{c.body}</p>}
          </header>

          <Summary c={c} />
          {c.approval.protected.length > 0 && c.status === "review" && (
            <p className="callout"><Icon name="access" size={16} />
              <span><b>Touches protected code</b> ({c.approval.protected.join(", ")}). Only the founder approves and merges it.</span>
            </p>
          )}
          <LookClosely checks={c.checks} />

          <section className="cd-files">
            {c.file_list.map((f) => (
              <div key={f.path} className="cd-file">
                <div className="cd-file-head">
                  <span className="mono">{f.path}</span>
                  {f.protected && <span className="cd-tag"><Icon name="access" size={11} /> protected</span>}
                  <span className="t-note">{f.kind === "new" ? "new file" : f.kind === "deleted" ? "deleted" : ""} +{f.added} −{f.removed}</span>
                  {c.can.edit && <button className="text-link cd-drop" onClick={() => drop(f.path)}>Remove from change</button>}
                </div>
                <Diff file={f} comments={c.comments.filter((x) => x.path === f.path)}
                  onComment={c.can.comment ? comment : undefined} onResolve={c.can.comment ? resolve : undefined} />
              </div>
            ))}
            {c.file_list.length === 0 && <p className="t-note">No files yet. Open a file, edit your lines and add them to this change.</p>}
          </section>

          {c.reviews.length > 0 && (
            <section className="cd-talk">
              <h3 className="t-h3">Conversation</h3>
              <ol>
                {c.reviews.map((r, i) => (
                  <li key={i}>
                    <p><b>{r.by}</b> {VERDICT[r.verdict]} <span className="faint" title={dateTime(r.at)}>{ago(r.at)}</span></p>
                    {r.body && <p className="cd-say">{r.body}</p>}
                  </li>
                ))}
              </ol>
            </section>
          )}

          <Actions c={c} note={note} setNote={setNote} busy={busy} act={act} setConfirm={setConfirm}
            onUndo={() => setConfirm({ title: "Undo this change?", text: "This opens a new change that takes it back. Nothing happens to the code until that one is approved and merged.", button: "Open the undo", tone: "plain", run: undo })} />
        </>
      )}
      <Modal open={Boolean(confirm)} onClose={() => setConfirm(null)} tone={confirm?.tone === "plain" ? undefined : "danger"}
        title={confirm?.title} subtitle={confirm?.text}
        footer={<Button variant={confirm?.tone === "plain" ? "primary" : "danger"} busy={Boolean(busy)} onClick={confirm?.run}>{confirm?.button}</Button>} />
    </div>
  );
}

function Summary({ c }) {
  const failed = c.checks.filter((x) => !x.ok);
  return (
    <section className="cd-summary">
      <div>
        <span className="label">Approvals</span>
        <p>{c.approval.by.length ? `Approved by ${c.approval.by.join(", ")}` : "None yet"}
          {c.status === "review" && <span className="faint"> · needs {c.need_approvals}{c.need_approvals > 1 ? " (intern's change)" : ""}</span>}</p>
      </div>
      <div>
        <span className="label">Checks</span>
        <p>{c.checks.length === 0 ? "Run when it's sent for review" : failed.length ? <span className="form-error">{failed[0].file}: {failed[0].detail}</span> : "All passed"}</p>
      </div>
      {c.comments.length > 0 && (
        <div>
          <span className="label">Line comments</span>
          <p>{c.comments.filter((x) => !x.resolved).length} open of {c.comments.length}</p>
        </div>
      )}
      {c.status === "merged" && (
        <div>
          <span className="label">GitHub</span>
          <p>{c.github === "pushed" ? <>On GitHub <span className="mono faint">{c.merged_sha.slice(0, 8)}</span></> : c.github_detail}</p>
        </div>
      )}
    </section>
  );
}

// Never blocking: lines a reviewer should read twice.
function LookClosely({ checks }) {
  const warns = checks.filter((x) => x.warn);
  if (!warns.length) return null;
  return (
    <section className="cd-look">
      <h3 className="t-h3">Look closely</h3>
      <p className="t-note">Not wrong in themselves. This is where a mistake, or something slipped in on purpose, would have to live.</p>
      <ul>
        {warns.map((w, i) => (
          <li key={i}>
            <span className="mono">{w.file}</span> <span>{w.detail}</span>
            {w.text && <code className="cd-look-code">{w.text}</code>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Actions({ c, note, setNote, busy, act, setConfirm, onUndo }) {
  const can = c.can;
  if (!(can.submit || can.review || can.merge || can.comment || can.withdraw || can.override || can.undo)) return null;
  return (
    <section className="cd-actions">
      {(can.comment || can.review) && c.status !== "merged" && (
        <Field textarea label={can.review ? "Your review" : "Add a note"} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder={can.review ? "What's good, what should change. Required when asking for changes." : "Anything the reviewers should know"} />
      )}
      <div className="cd-buttons">
        {can.submit && (
          <Button variant="primary" busy={busy === "submit"} onClick={() => act("submit", "submit", {}, "Sent for review. The people who answer for this code were told.")}>
            {c.status === "draft" ? "Send for review" : "Send again"}
          </Button>
        )}
        {can.review && (
          <>
            <Button variant="primary" busy={busy === "approve"} onClick={() => act("approve", "review", { verdict: "approve", body: note }, "Approved.")}>Approve</Button>
            <Button busy={busy === "changes"} disabled={!note.trim()} onClick={() => act("changes", "review", { verdict: "changes", body: note }, "Sent back with your notes.")}>Ask for changes</Button>
          </>
        )}
        {can.comment && !can.review && c.status !== "merged" && (
          <Button busy={busy === "comment"} disabled={!note.trim()} onClick={() => act("comment", "review", { verdict: "comment", body: note })}>Add note</Button>
        )}
        {can.merge && (
          <Button variant="primary" busy={busy === "merge"} onClick={() => act("merge", "merge", { override: false }, "Merged, and sent to GitHub.")}>Merge</Button>
        )}
        {can.undo && <Button onClick={onUndo}>Undo this change</Button>}
        <span className="cd-spacer" />
        {can.reject && (
          <Button variant="quiet" disabled={!note.trim()} onClick={() => setConfirm({
            title: "Reject this change?", text: "It closes for good. Your note tells them why.", button: "Reject",
            run: () => act("reject", "review", { verdict: "reject", body: note }, "Rejected."),
          })}>Reject</Button>
        )}
        {can.override && (
          <Button variant="quiet" onClick={() => setConfirm({
            title: "Merge without approval?", text: "Only you can do this, and it's recorded as a founder override.", button: "Merge anyway",
            run: () => act("merge", "merge", { override: true }, "Merged by founder override."),
          })}>Merge without approval</Button>
        )}
        {can.withdraw && (
          <Button variant="quiet" onClick={() => setConfirm({
            title: "Withdraw this change?", text: "It closes, and nothing in it reaches GitHub.", button: "Withdraw",
            run: () => act("withdraw", "withdraw", {}, "Withdrawn."),
          })}>Withdraw</Button>
        )}
      </div>
      {!can.merge && c.status === "review" && can.merge_why && <p className="t-note">{can.merge_why}</p>}
    </section>
  );
}
