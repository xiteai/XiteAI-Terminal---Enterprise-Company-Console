import { useState } from "react";
import { api } from "../../../lib/api.js";
import { ago, date, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";
import GiveAccess from "./GiveAccess.jsx";
import ItemBuilder from "./ItemBuilder.jsx";

// Who was given what, who answers for what, and the named features. Every
// action here is checked again on the server and lands in the audit log.
export default function AccessPage() {
  const { rid, repo } = useRepo();
  const toast = useToast();
  const { data, error, reload, mutate } = useData(() => api.get(`/api/code/${rid}/access`), [rid]);
  const people = useData(() => api.get(`/api/code/${rid}/people`), [rid]);
  const tree = useData(() => api.get(`/api/code/${rid}/tree`), [rid, repo.head_sha]);
  const [modal, setModal] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);

  // Resolves true when the server agreed, so a form only clears on success.
  const run = async (fn, done) => {
    setBusy(true);
    try {
      const next = await fn();
      mutate(() => next);
      if (done) toast(done);
      setModal(null); setConfirm(null);
      return true;
    } catch (e) { toast.error(e.message); return false; }
    finally { setBusy(false); }
  };
  const files = tree.data?.files || [];
  const ctx = { rid, files, people: people.data?.items || [], busy, run, features: data?.features || [] };

  return (
    <div>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <>
          <Card title="Access given" subtitle="Each line is one person and what they got. Features update everyone who holds them."
            action={data.can.grant && <Button size="sm" variant="primary" onClick={() => setModal("grant")}>Give access</Button>}>
            {data.grants.length === 0 ? <Empty title="Nobody has been given code yet." /> : (
              <div className="table">
                <table>
                  <thead><tr><th>Person</th><th>What</th><th>Can</th><th>Until</th><th>Given by</th><th className="r" /></tr></thead>
                  <tbody>
                    {data.grants.map((g) => (
                      <tr key={g.id} className={g.expired ? "ca-expired" : ""}>
                        <td className="ca-person"><b>{g.person.name}</b><span>{g.person.level_label}</span></td>
                        <td className="ca-what">
                          {g.feature ? <><b>{g.feature.name}</b><span className="ca-kind">feature</span></> : g.items.map((it) => (
                            <span key={it.id} className={it.missing ? "ca-missing" : ""} title={it.missing ? "This code is gone" : ""}>{it.label}</span>
                          ))}
                        </td>
                        <td>{g.can_edit ? "Read and edit" : "Read"}</td>
                        <td>{g.expired ? "Ended" : g.expires_at ? date(g.expires_at) : "No end"}</td>
                        <td title={dateTime(g.at)}>{g.by?.name || "–"}, {ago(g.at)}</td>
                        <td className="r">
                          {(data.can.revoke || data.can.grant) && (
                            <button className="text-link" onClick={() => setConfirm({
                              title: `Take this access from ${g.person.name}?`, text: "It stops at once. They keep nothing they could see before.",
                              button: "Take it away", run: () => run(() => api.del(`/api/code/${rid}/grants/${g.id}`), "Access removed."),
                            })}>Remove</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="Who answers for what" subtitle="Owners approve and merge changes to their code, and give access in it. Reviewers approve, and give read access to their own team."
            action={data.can.owners && <Button size="sm" onClick={() => setModal("owner")}>Add</Button>}>
            {data.owners.length === 0 ? <p className="t-note">Nobody yet. Until someone is, changes go to whoever can merge anything.</p> : (
              <ul className="ca-list">
                {data.owners.map((o) => (
                  <li key={o.id}>
                    <span><b>{o.person.name}</b> <span className="faint">{o.person.level_label}</span></span>
                    <span>{o.role === "owner" ? "Owner" : "Reviewer"} of <b>{o.feature ? `${o.feature.name} (feature)` : (o.path || "everything")}</b></span>
                    {data.can.owners && <button className="text-link" onClick={() => run(() => api.del(`/api/code/${rid}/owners/${o.id}`))}>Remove</button>}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Features" subtitle="A named bundle of folders, files, functions and lines. Give it to people, or make someone its owner; change it here and everyone who has it gets the change."
            action={data.can.features && <Button size="sm" onClick={() => setModal("feature")}>New feature</Button>}>
            {data.features.length === 0 ? <p className="t-note">No features yet.</p> : (
              <div className="ca-features">
                {data.features.map((f) => (
                  <div key={f.id} className="ca-feature">
                    <div className="ca-feature-head">
                      <b>{f.name}</b>
                      <span className="faint">{f.grants} {f.grants === 1 ? "person has" : "people have"} it</span>
                      {data.can.features && (
                        <span className="ca-feature-tools">
                          <button className="text-link" onClick={() => setModal({ addTo: f })}>Add to it</button>
                          <button className="text-link" onClick={() => setConfirm({
                            title: `Delete ${f.name}?`, text: `${f.grants} ${f.grants === 1 ? "person loses" : "people lose"} the access it gave.`,
                            button: "Delete feature", run: () => run(() => api.del(`/api/code/${rid}/features/${f.id}`), "Feature deleted."),
                          })}>Delete</button>
                        </span>
                      )}
                    </div>
                    {f.description && <p className="t-note">{f.description}</p>}
                    <ul className="ib-chosen">
                      {f.items.map((it) => (
                        <li key={it.id} className={it.missing ? "ca-missing" : ""}>
                          <span>{it.label}</span>
                          {data.can.features && <button aria-label={`Remove ${it.label}`} onClick={() => run(() => api.del(`/api/code/${rid}/features/${f.id}/items/${it.id}`))}>×</button>}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      <GiveAccess open={modal === "grant"} onClose={() => setModal(null)} onDone={(next) => mutate(() => next)} />
      <AddOwner open={modal === "owner"} onClose={() => setModal(null)} ctx={ctx} />
      <FeatureModal open={modal === "feature" || Boolean(modal?.addTo)} addTo={modal?.addTo} onClose={() => setModal(null)} ctx={ctx} />
      <Modal open={Boolean(confirm)} onClose={() => setConfirm(null)} tone="danger" title={confirm?.title} subtitle={confirm?.text}
        footer={<Button variant="danger" busy={busy} onClick={confirm?.run}>{confirm?.button}</Button>} />
    </div>
  );
}

function PersonPick({ people, value, onChange, filter }) {
  const list = people.filter(filter || (() => true));
  return (
    <Select label="Person" value={value} onChange={onChange} placeholder="Choose someone"
      options={list.map((p) => ({ value: p.id, label: `${p.name}${p.me ? " (you)" : ""}, ${p.level_label}${p.title ? `, ${p.title}` : ""}` }))} />
  );
}

function AddOwner({ open, onClose, ctx }) {
  const [who, setWho] = useState("");
  const [role, setRole] = useState("owner");
  const [scope, setScope] = useState("path");
  const [path, setPath] = useState("");
  const [feature, setFeature] = useState("");
  const rank = { founder: 100, vp: 80, director: 60, hr: 50, manager: 40 };
  const need = role === "owner" ? 60 : 40;
  const save = () => ctx.run(() => api.post(`/api/code/${ctx.rid}/owners`, {
    staff_id: Number(who), role, ...(scope === "feature" ? { feature_id: Number(feature) } : { path }),
  }), "Saved.");
  const folders = [...new Set(ctx.files.flatMap((f) => f.p.split("/").slice(0, -1).map((_, i, a) => a.slice(0, i + 1).join("/"))))].sort();
  return (
    <Modal open={open} onClose={onClose} title="Who answers for this code" width={520}
      footer={<Button variant="primary" busy={ctx.busy} disabled={!who || (scope === "feature" ? !feature : false)} onClick={save}>Save</Button>}>
      <div className="code-form">
        <Seg size="sm" value={role} onChange={setRole} label="Role"
          options={[{ value: "owner", label: "Owner" }, { value: "reviewer", label: "Reviewer" }]} />
        <p className="t-note">{role === "owner" ? "Approves and merges changes, gives access (read and edit). Director or above." : "Approves changes, gives read access to their own team. Manager or above."}</p>
        <PersonPick people={ctx.people} value={who} onChange={setWho} filter={(p) => (rank[p.level] || 0) >= need} />
        {ctx.features.length > 0 && (
          <Seg size="sm" value={scope} onChange={setScope} label="Of what"
            options={[{ value: "path", label: "A folder or file" }, { value: "feature", label: "A feature" }]} />
        )}
        {scope === "feature" ? (
          <Select label="Feature" value={feature} onChange={setFeature} placeholder="Choose a feature"
            options={ctx.features.map((f) => ({ value: f.id, label: f.name }))} />
        ) : (
          <>
            <Field label="Folder or file" value={path} onChange={(e) => setPath(e.target.value)} list="owner-paths"
              placeholder="core/memory (empty = everything)" />
            <datalist id="owner-paths">{[...folders, ...ctx.files.map((f) => f.p)].slice(0, 3000).map((p) => <option key={p} value={p} />)}</datalist>
          </>
        )}
      </div>
    </Modal>
  );
}

function FeatureModal({ open, addTo, onClose, ctx }) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [items, setItems] = useState([]);
  const save = () => ctx.run(() => (addTo
    ? api.post(`/api/code/${ctx.rid}/features/${addTo.id}/items`, { items })
    : api.post(`/api/code/${ctx.rid}/features`, { name, description: desc, items })), addTo ? "Added. Everyone with the feature has it now." : "Feature created.")
    .then((ok) => { if (ok) { setItems([]); setName(""); setDesc(""); } });
  return (
    <Modal open={open} onClose={onClose} width={620} title={addTo ? `Add to ${addTo.name}` : "New feature"}
      subtitle={addTo ? `Existing: ${addTo.items.map((i) => i.label).join(", ") || "nothing yet"}` : "Name a part of the product, then pick the code that makes it."}
      footer={<Button variant="primary" busy={ctx.busy} disabled={!items.length || (!addTo && name.trim().length < 2)} onClick={save}>{addTo ? "Add" : "Create feature"}</Button>}>
      <div className="code-form">
        {!addTo && (
          <div className="code-two">
            <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Memory engine" maxLength={60} />
            <Field label="What it is (optional)" value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={300} />
          </div>
        )}
        <ItemBuilder files={ctx.files} items={items} onChange={setItems} />
      </div>
    </Modal>
  );
}

