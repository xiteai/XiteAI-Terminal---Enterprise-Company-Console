import { Fragment, useState } from "react";
import { ago, dateTime } from "../../../lib/format.js";
import { cx } from "../../../lib/cx.js";
import Button from "../../../components/Button.jsx";

// A unified diff, hunk by hunk. Lines the viewer may not see arrive only as a
// count; they show as a band, never as text. With `onComment`, a line number
// opens a comment on that exact line, and comments sit under their line.
function Thread({ items, onResolve }) {
  return items.map((c) => (
    <tr key={c.id} className={cx("dv-comment", c.resolved && "done")}>
      <td colSpan={4}>
        <div className="dv-comment-in">
          <p><b>{c.by}</b> <span className="faint" title={dateTime(c.at)}>{ago(c.at)}</span>
            {c.resolved ? <span className="faint"> · done{c.resolved_by ? ` (${c.resolved_by})` : ""}</span>
              : onResolve && <button className="text-link" onClick={() => onResolve(c.id)}>Done</button>}</p>
          <p className="dv-comment-body">{c.body}</p>
        </div>
      </td>
    </tr>
  ));
}

function Draft({ onSave, onCancel }) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <tr className="dv-comment dv-draft">
      <td colSpan={4}>
        <div className="dv-comment-in">
          <textarea className="cv-textarea" rows={3} autoFocus value={body} onChange={(e) => setBody(e.target.value)}
            placeholder="What about this line?" aria-label="Comment on this line" />
          <div className="cv-editor-foot">
            <Button size="sm" variant="quiet" onClick={onCancel}>Cancel</Button>
            <Button size="sm" variant="primary" busy={busy} disabled={!body.trim()}
              onClick={async () => { setBusy(true); const ok = await onSave(body); setBusy(false); if (ok) onCancel(); }}>Comment</Button>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function Diff({ file, comments = [], onComment, onResolve }) {
  const [draft, setDraft] = useState(null);
  if (file.hidden) return <p className="t-note dv-none">This file isn't shared with you, so its changes aren't shown.</p>;
  if (!file.hunks || file.hunks.length === 0) return <p className="t-note dv-none">No changes in this file.</p>;
  const byLine = new Map();
  comments.forEach((c) => {
    const k = `${c.side}:${c.line}`;
    if (!byLine.has(k)) byLine.set(k, []);
    byLine.get(k).push(c);
  });
  return (
    <div className="dv">
      {file.hunks.map((h, hi) => (
        <table key={hi} className="dv-hunk">
          <tbody>
            {h.map((r, i) => {
              if (r.t === "hidden") {
                return <tr key={i} className="dv-hidden"><td colSpan={4}>{r.n === 1 ? "1 line" : `${r.n} lines`} not shared with you</td></tr>;
              }
              const side = r.t === "-" ? "old" : "new";
              const line = side === "old" ? r.a : r.b;
              const key = `${side}:${line}`;
              return (
                <Fragment key={i}>
                  <tr className={cx("dv-row", r.t === "+" && "add", r.t === "-" && "del", byLine.has(key) && "has-comment")}>
                    <td className="dv-no">{r.a ?? ""}</td>
                    <td className="dv-no">
                      {onComment
                        ? <button className="dv-at" title="Comment on this line" onClick={() => setDraft(key)}>{r.b ?? r.a}</button>
                        : r.b ?? ""}
                    </td>
                    <td className="dv-sign">{r.t === "+" ? "+" : r.t === "-" ? "−" : ""}</td>
                    <td className="dv-text"><code>{r.text || " "}</code></td>
                  </tr>
                  {byLine.has(key) && <Thread items={byLine.get(key)} onResolve={onResolve} />}
                  {draft === key && <Draft onCancel={() => setDraft(null)}
                    onSave={(body) => onComment({ path: file.path, side, line, body })} />}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      ))}
    </div>
  );
}
