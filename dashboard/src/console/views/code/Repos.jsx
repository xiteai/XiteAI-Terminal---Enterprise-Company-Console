import { useState } from "react";
import { api } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Switch from "../../../components/Switch.jsx";
import { useToast } from "../../../components/Toast.jsx";
import CloneProgress from "./CloneProgress.jsx";

const mb = (n) => (n >= 1073741824 ? `${(n / 1073741824).toFixed(1)} GB` : `${Math.max(1, Math.round(n / 1048576))} MB`);

// The founder's room: the GitHub repositories behind the Codebase, and
// everything that keeps them safe.
export default function Repos({ data, reload }) {
  const toast = useToast();
  const [form, setForm] = useState({ name: "", url: "", branch: "" });
  const [busy, setBusy] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const ready = data.items.filter((r) => r.status === "ready");

  // Reload either way: a refused sync (the history guard holding) changes what this page must show.
  const call = async (key, fn, done) => {
    setBusy(key);
    try { const out = await fn(); if (done) toast(done); setConfirm(null); return out; }
    catch (e) { toast.error(e.message); setConfirm(null); return null; }
    finally { setBusy(null); reload(); }
  };
  const connect = () => call("connect", () => api.post("/api/code/repos", form), "Copying it from GitHub. A big repository takes a few minutes.")
    .then((ok) => ok && setForm({ name: "", url: "", branch: "" }));

  return (
    <div>
      {data.can_connect && data.items.filter((r) => r.held_remote).map((r) => (
        <Card key={`held${r.id}`} title={`GitHub's history for ${r.name} was rewritten`}
          subtitle="Someone force-pushed: GitHub no longer contains history it had. The Terminal kept the real history and stopped following, so nothing is lost. Nothing merges until you choose.">
          <div className="rp-held">
            <div>
              <b>Put the real history back on GitHub</b>
              <p className="t-note">Usually right: undoes the rewrite. GitHub goes back to what the Terminal kept.</p>
              <Button variant="primary" busy={busy === `put${r.id}`} onClick={() => setConfirm({
                title: "Put the real history back on GitHub?", text: "GitHub's branch goes back to the history the Terminal kept. The rewritten version stays in GitHub's own records.",
                button: "Put it back", plain: true, run: () => call(`put${r.id}`, () => api.post(`/api/code/repos/${r.id}/history/put-back`), "GitHub has the real history again."),
              })}>Put it back</Button>
            </div>
            <div>
              <b>Follow GitHub's new history</b>
              <p className="t-note">Only if the rewrite was on purpose. What the Terminal had stays pinned here and in the backups.</p>
              <Button busy={busy === `acc${r.id}`} onClick={() => setConfirm({
                title: "Follow GitHub's new history?", text: "The Terminal moves to what GitHub has now. The old history stays pinned on this server, never deleted.",
                button: "Follow GitHub", run: () => call(`acc${r.id}`, () => api.post(`/api/code/repos/${r.id}/history/accept`), "Following GitHub again."),
              })}>Follow GitHub</Button>
            </div>
          </div>
        </Card>
      ))}

      <Card title="Connected repositories" flush>
        {data.items.length === 0 && <p className="t-note">None yet.</p>}
        {data.items.length > 0 && (
          <div className="table">
            <table>
              <thead><tr><th>Name</th><th>GitHub</th><th>State</th><th>Last sync</th><th className="r" /></tr></thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.id}>
                    <td className="strong">{r.name} <span className="faint">{r.branch}</span></td>
                    <td className="mono code-url" title={r.remote_url}>{r.remote_url.replace("https://github.com/", "")}</td>
                    <td>
                      {r.status === "ready" ? (r.status_detail || (r.pushes ? "Following GitHub" : "Merges stay here until a GitHub token is set"))
                        : r.status === "cloning" ? <CloneProgress progress={r.progress} compact />
                        : <span className="form-error">{r.status_detail}</span>}
                    </td>
                    <td title={r.last_sync_at ? dateTime(r.last_sync_at) : ""}>{r.last_sync_at ? ago(r.last_sync_at) : "–"}</td>
                    <td className="r code-actions">
                      {data.can_sync && r.status === "ready" && (
                        <Button size="sm" busy={busy === `sync${r.id}`} onClick={() => call(`sync${r.id}`, () => api.post(`/api/code/repos/${r.id}/sync`), "Up to date with GitHub.")}>Sync now</Button>
                      )}
                      {data.can_connect && (r.status === "cloning" ? (
                        <button className="text-link" onClick={() => setConfirm({
                          title: `Cancel copying ${r.name}?`, text: "Stops right away. Nothing was kept, and GitHub itself is untouched.",
                          button: "Cancel it", run: () => call(`remove${r.id}`, () => api.del(`/api/code/repos/${r.id}`), `Cancelled. ${r.name} wasn't added.`),
                        })}>Cancel</button>
                      ) : (
                        <button className="text-link" onClick={() => setConfirm({
                          title: `Remove ${r.name}?`, text: "Its grants, features, change requests and checkpoints here go with it. GitHub itself is untouched.",
                          button: "Remove", run: () => call(`remove${r.id}`, () => api.del(`/api/code/repos/${r.id}`), `${r.name} removed. GitHub is untouched.`),
                        })}>Remove</button>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {data.can_connect && <Security />}
      {data.can_connect && ready.map((r) => <Protected key={`p${r.id}`} repo={r} />)}
      {data.can_connect && ready.map((r) => <Backups key={`b${r.id}`} repo={r} />)}

      {data.can_connect && (
        <Card title="Connect a repository" subtitle="The server copies it once, then follows GitHub. Approved changes are pushed back under their author's name.">
          <div className="code-form code-connect">
            <div className="code-two">
              <Field label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="XOS1" />
              <Field label="Branch" value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value })}
                placeholder="Leave blank to use its default" />
            </div>
            <Field label="GitHub address" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder="https://github.com/you/repository" />
            <div className="callout">
              <span>
                For a private repository, and for merges to reach GitHub, the server's <span className="code">.env</span> needs{" "}
                <span className="code">GITHUB_TOKEN</span>: a fine-grained token with <b>Contents: Read and write</b> on this one repository.
                It's never written to disk. On GitHub, also turn on branch protection for <b>{form.branch || "its default branch"}</b> with
                force-pushes and deletion blocked.
              </span>
            </div>
            <div><Button variant="primary" busy={busy === "connect"} disabled={!form.name.trim() || !form.url.trim()} onClick={connect}>Connect</Button></div>
          </div>
        </Card>
      )}

      <Modal open={Boolean(confirm)} onClose={() => setConfirm(null)} tone={confirm?.plain ? undefined : "danger"} title={confirm?.title}
        subtitle={confirm?.text}
        footer={<Button variant={confirm?.plain ? "primary" : "danger"} busy={Boolean(busy)} onClick={confirm?.run}>{confirm?.button}</Button>} />
    </div>
  );
}

// Who can open code, and on what terms.
function Security() {
  const toast = useToast();
  const { data, error, mutate } = useData(() => api.get("/api/code/security"), []);
  const [asking, setAsking] = useState(false);
  const flip = async (on) => {
    try { const next = await api.put("/api/code/security", { require_mfa: on }); mutate(() => next); setAsking(false);
      toast(on ? "Code opens only in sessions signed in with an authenticator." : "Turned off. Passwords alone now open code."); }
    catch (e) { toast.error(e.message); }
  };
  const resume = async (p) => {
    try { const next = await api.post(`/api/code/people/${p.id}/resume`); mutate(() => next); toast(`${p.name} can open code again.`); }
    catch (e) { toast.error(e.message); }
  };
  if (error || !data) return null;
  return (
    <Card title="Security" subtitle="Who can open code, and what stops an account that goes wrong.">
      <div className="rp-sec">
        <div className="code-row">
          <span><b>Authenticator required to open code</b><small>A stolen password alone gets nobody in. Keep this on.</small></span>
          <Switch checked={data.require_mfa} onChange={(on) => (on ? flip(true) : setAsking(true))} label="Authenticator required" />
        </div>
        {data.no_authenticator.length > 0 && (
          <p className="t-note"><b>Not set up yet:</b> {data.no_authenticator.map((p) => p.name).join(", ")}. They can't open code until they do (Account).</p>
        )}
        <div>
          <p className="t-note">
            <b>Reading alarm:</b> if one account opens {data.alarm.alert_files} different files in an hour you're told; at {data.alarm.pause_files} its
            code access pauses by itself until you resume it. Same for {data.alarm.alert_searches} and {data.alarm.pause_searches} searches.
          </p>
          {data.paused.length === 0 && <p className="t-note">Nobody is paused.</p>}
          {data.paused.length > 0 && (
            <ul className="rp-list">
              {data.paused.map((p) => (
                <li key={p.id}><span><b>{p.name}</b> <span className="faint">{p.level_label}</span> · paused</span>
                  <Button size="sm" onClick={() => resume(p)}>Resume</Button></li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <Modal open={asking} onClose={() => setAsking(false)} tone="danger" title="Let passwords alone open code?"
        subtitle="Anyone who learns a password could read whatever that person can. Only for a short while, if ever."
        footer={<Button variant="danger" onClick={() => flip(false)}>Turn it off</Button>} />
    </Card>
  );
}

// The founder's walls.
function Protected({ repo }) {
  const toast = useToast();
  const { data, mutate } = useData(() => api.get(`/api/code/${repo.id}/protected`), [repo.id, repo.head_sha]);
  const [path, setPath] = useState("");
  const add = async (p) => {
    try { const next = await api.post(`/api/code/${repo.id}/protected`, { path: p }); mutate(() => next); setPath(""); toast(`${p} is protected.`); }
    catch (e) { toast.error(e.message); }
  };
  const remove = async (p) => {
    try { const next = await api.del(`/api/code/${repo.id}/protected?path=${encodeURIComponent(p)}`); mutate(() => next); toast(`${p} is no longer protected.`); }
    catch (e) { toast.error(e.message); }
  };
  if (!data) return null;
  return (
    <Card title={`Protected code in ${repo.name}`}
      subtitle="Only you read these, give access to them, and merge changes to them. Folder grants, owners and “read all code” stop at their edge.">
      <ul className="rp-list">
        {data.items.map((p) => (
          <li key={p.path}><span><b className="mono">{p.path}</b> <span className="faint">{p.by}, {ago(p.at)}</span></span>
            <button className="text-link" onClick={() => remove(p.path)}>Unprotect</button></li>
        ))}
        {data.items.length === 0 && <li><span className="t-note">Nothing protected.</span></li>}
      </ul>
      {data.suggested.length > 0 && (
        <p className="t-note rp-suggest">Worth protecting: {data.suggested.map((p) => (
          <button key={p} className="text-link mono" onClick={() => add(p)}>{p}</button>
        ))}</p>
      )}
      <div className="rp-add">
        <Field value={path} onChange={(e) => setPath(e.target.value)} placeholder="A folder or file, like core/system/update" aria-label="Path to protect" />
        <Button size="sm" disabled={!path.trim()} onClick={() => add(path.trim())}>Protect</Button>
      </div>
    </Card>
  );
}

// Offline copies of the whole history, restorable without GitHub.
function Backups({ repo }) {
  const toast = useToast();
  const { data, mutate } = useData(() => api.get(`/api/code/${repo.id}/backups`), [repo.id]);
  const [busy, setBusy] = useState(false);
  const now = async () => {
    setBusy(true);
    try { const next = await api.post(`/api/code/${repo.id}/backups`); mutate(() => next); toast("Backed up."); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  if (!data) return null;
  return (
    <Card title={`Backups of ${repo.name}`}
      subtitle={`The whole history in one file, made every day, newest ${data.keep} kept. Restores with git clone even if GitHub is gone.`}
      action={<Button size="sm" busy={busy} onClick={now}>Back up now</Button>}>
      {data.items.length === 0 && <p className="t-note">None yet. The first one is made within a day, or now.</p>}
      {data.items.length > 0 && (
        <ul className="rp-list">
          {data.items.map((b) => (
            <li key={b.name}><span><b className="mono">{b.name}</b> <span className="faint">{mb(b.size)} · {ago(b.at)}</span></span></li>
          ))}
        </ul>
      )}
      <p className="t-note">On the server in <span className="code">{data.folder}</span>. To restore: <span className="code">git clone {"<file>"} restored</span>.</p>
    </Card>
  );
}
