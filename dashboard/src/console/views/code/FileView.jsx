import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { ago, dateTime, plural } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import { cx } from "../../../lib/cx.js";
import Button from "../../../components/Button.jsx";
import Drawer from "../../../components/Drawer.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import { useRepo } from "./Code.jsx";
import SaveToChange from "./SaveToChange.jsx";

// One file, as much of it as you may see. Lines that aren't shared with you
// never reach this page: they're a band that says how many there are.
function sentence(f) {
  if (f.edit_full) return "You can read and edit all of it.";
  if (f.access === "full") return f.can_edit ? "You can read all of it, and edit the marked parts." : "You can read all of it.";
  const seen = f.blocks.filter((b) => b.kind === "shown").reduce((n, b) => n + b.end - b.start + 1, 0);
  return `You can see ${plural(seen, "line")} of ${f.lines_total}${f.can_edit ? ", and edit the marked parts" : ""}.`;
}

function Who({ run }) {
  if (!run) return <span className="cv-who" />;
  return (
    <Link className="cv-who" to={run.change ? `/console/code/changes/${run.change.id}` : `/console/code/history/${run.sha}`}
      title={`${run.summary}\n${run.author}, ${run.at ? dateTime(run.at) : ""}`}>
      {run.author.split(" ")[0]} · {run.at ? ago(run.at) : run.short}
    </Link>
  );
}

function Block({ block, total, onEdit, whoAt }) {
  if (block.kind === "hidden") {
    const n = block.end - block.start + 1;
    return <div className="cv-hidden">{n === 1 ? `Line ${block.start}` : `Lines ${block.start}–${block.end}`} aren't shared with you</div>;
  }
  return (
    <div className={block.editable ? "cv-block cv-editable" : "cv-block"}>
      {block.editable && (
        <div className="cv-block-bar">
          <span>{block.start === 1 && block.end === total ? "The whole file is yours to edit" : `Lines ${block.start}–${block.end}, yours to edit`}</span>
          {onEdit && <button className="text-link" onClick={onEdit}>Edit</button>}
        </div>
      )}
      <pre className={cx("cv-lines", whoAt && "with-who")}>
        {block.lines.map((ln, i) => (
          <div key={i} className="cv-line" id={`L${block.start + i}`}>
            {whoAt && <Who run={whoAt(block.start + i)} />}
            <span className="cv-no">{block.start + i}</span>
            <code>{ln || " "}</code>
          </div>
        ))}
      </pre>
    </div>
  );
}

function Editor({ block, onCancel, onDone }) {
  const [value, setValue] = useState(block.lines.join("\n"));
  const rows = Math.min(Math.max(block.lines.length + 2, 6), 32);
  return (
    <div className="cv-editor">
      <div className="cv-block-bar"><span>Editing lines {block.start}–{block.end}</span></div>
      <textarea className="cv-textarea" value={value} rows={rows} spellCheck={false}
        onChange={(e) => setValue(e.target.value)} aria-label={`Lines ${block.start} to ${block.end}`}
        onKeyDown={(e) => {
          if (e.key === "Tab" && !e.shiftKey) {
            e.preventDefault();
            const el = e.currentTarget, s = el.selectionStart;
            setValue(value.slice(0, s) + "    " + value.slice(el.selectionEnd));
            requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = s + 4; });
          }
        }} />
      <div className="cv-editor-foot">
        <Button variant="quiet" size="sm" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" size="sm" onClick={() => onDone(value)} disabled={value === block.lines.join("\n")}>
          Add to a change
        </Button>
      </div>
    </div>
  );
}

// Every earlier version of this file; open one, and put it back if you may.
function FileHistory({ path, open, onClose, canRestore }) {
  const { rid } = useRepo();
  const toast = useToast();
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [err, setErr] = useState(null);
  const [version, setVersion] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    setVersion(null); setErr(null); setItems(null);
    api.get(`/api/code/${rid}/history${qs({ path })}`).then((d) => setItems(d.commits)).catch((e) => setErr(e.message));
  }, [open, rid, path]);
  const view = async (c) => {
    setErr(null);
    try { setVersion({ ...c, file: await api.get(`/api/code/${rid}/file${qs({ path, rev: c.sha })}`) }); }
    catch (e) { setErr(e.message); }
  };
  const restore = async () => {
    setBusy(true);
    try {
      const d = await api.post(`/api/code/${rid}/restore`, { path, rev: version.sha });
      toast(`Change #${d.id} puts it back. It goes through review like any change.`);
      onClose();
      navigate(`/console/code/changes/${d.id}`);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  return (
    <Drawer open={open} onClose={onClose} width={720} eyebrow="History" title={path.split("/").pop()}>
      <ErrorNote error={err && { message: err }} />
      {!items && !err && <div className="drawer-wait"><Spinner delay={200} /></div>}
      {items && !version && (
        <ol className="fh-list">
          {items.map((c, i) => (
            <li key={c.sha}>
              <button className="fh-row" onClick={() => view(c)}>
                <b>{c.subject}</b>
                <span>{c.author} · <span title={dateTime(c.at)}>{ago(c.at)}</span>{i === 0 ? " · now" : ""}
                  {c.change && ` · change #${c.change.id}`}{c.checkpoint && ` · checkpoint ${c.checkpoint}`}</span>
              </button>
            </li>
          ))}
        </ol>
      )}
      {version && (
        <div className="fh-version">
          <div className="fh-version-head">
            <button className="text-link" onClick={() => setVersion(null)}>All versions</button>
            <span className="t-note">As it was after “{version.subject}”, {dateTime(version.at)}</span>
            {canRestore && items[0]?.sha !== version.sha && (
              <Button size="sm" variant="primary" busy={busy} onClick={restore}>Restore this version</Button>
            )}
          </div>
          <pre className="cv-lines">
            {version.file.lines.map((ln, i) => (
              <div key={i} className="cv-line"><span className="cv-no">{i + 1}</span><code>{ln || " "}</code></div>
            ))}
          </pre>
        </div>
      )}
    </Drawer>
  );
}

export default function FileView({ path, line, canRequest }) {
  const { rid, giveAccess } = useRepo();
  const { data: f, error, reload } = useData(() => api.get(`/api/code/${rid}/file${qs({ path })}`), [rid, path]);
  const [editing, setEditing] = useState(null);
  const [pending, setPending] = useState(null);
  const [who, setWho] = useState(null);
  const [history, setHistory] = useState(false);

  // Arriving from search: bring that line into view and mark it for a moment.
  useEffect(() => {
    if (!f || !line) return undefined;
    const el = document.getElementById(`L${line}`);
    if (!el) return undefined;
    el.scrollIntoView({ block: "center" });
    el.classList.add("cv-hit");
    const t = setTimeout(() => el.classList.remove("cv-hit"), 2600);
    return () => clearTimeout(t);
  }, [f, line]);

  const whoAt = useMemo(() => {
    if (!who) return null;
    const firsts = new Map(who.runs.map((r) => [r.start, r]));
    return (n) => firsts.get(n) || null;
  }, [who]);
  const toggleWho = async () => {
    if (who) { setWho(null); return; }
    try { setWho(await api.get(`/api/code/${rid}/blame${qs({ path })}`)); } catch { setWho({ runs: [] }); }
  };
  const jump = (name) => {
    const s = f.symbols.find((x) => x.name === name);
    document.getElementById(`L${s?.start}`)?.scrollIntoView({ block: "start", behavior: "smooth" });
  };

  return (
    <div className="cv">
      <header className="cv-head">
        <div className="cv-title">
          <div className="cv-path mono" title={path}>{path}</div>
          {f && (
            <div className="cv-tools">
              <button className={cx("cv-tool", who && "on")} onClick={toggleWho} aria-pressed={Boolean(who)}>Who changed this</button>
              {f.access === "full" && <button className="cv-tool" onClick={() => setHistory(true)}>History</button>}
              {giveAccess && f.access === "full" && <button className="cv-tool" onClick={() => giveAccess([{ kind: "file", path }])}>Give access</button>}
            </div>
          )}
        </div>
        {f && (
          <div className="cv-meta">
            <span>{sentence(f)}</span>
            {f.role && <span>You {f.role === "owner" ? "own" : "review"} this.</span>}
            {f.protected && <span className="cv-protected">Protected: only the founder gives access to it or merges changes to it.</span>}
            {f.symbols.length > 0 && (
              <Select size="sm" value="" onChange={jump} placeholder="Jump to…"
                options={f.symbols.map((s) => ({ value: s.name, label: `${s.kind === "function" ? "" : `${s.kind} `}${s.name}` }))} />
            )}
          </div>
        )}
      </header>
      <ErrorNote error={error} onRetry={error?.status >= 500 ? reload : undefined} />
      {!f && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {f && (
        <div className="cv-body">
          {f.blocks.map((b) => (
            editing?.start === b.start && b.kind === "shown"
              ? <Editor key={b.start} block={b} onCancel={() => setEditing(null)}
                  onDone={(text) => setPending({ path, base_sha: f.head, mode: "segments", segments: [{ start: b.start, end: b.end, text }] })} />
              : <Block key={`${b.kind}${b.start}`} block={b} total={f.lines_total} whoAt={whoAt}
                  onEdit={canRequest ? () => setEditing(b) : undefined} />
          ))}
          {f.lines_total === 0 && <p className="t-note">This file is empty.</p>}
        </div>
      )}
      <SaveToChange payload={pending} onClose={() => setPending(null)}
        onSaved={() => { setPending(null); setEditing(null); }} />
      {f && <FileHistory path={path} open={history} onClose={() => setHistory(false)} canRestore={f.edit_full && canRequest} />}
    </div>
  );
}
