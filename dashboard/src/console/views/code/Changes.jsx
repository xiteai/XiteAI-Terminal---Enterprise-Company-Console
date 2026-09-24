import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Seg from "../../../components/Seg.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useRepo } from "./Code.jsx";

export const STATUS = {
  draft: "Draft", review: "Waiting for review", changes: "Changes asked", conflict: "Needs redoing",
  merged: "Merged", rejected: "Rejected", withdrawn: "Withdrawn",
};
const OPEN = ["draft", "review", "changes", "conflict"];

// Change requests you can see: your own, and anything touching code you
// answer for (or everything, if you can merge anything).
export default function Changes() {
  const { rid } = useRepo();
  const navigate = useNavigate();
  const [filter, setFilter] = useState("open");
  const { data, error, reload } = useData(() => api.get(`/api/code/${rid}/changes`), [rid], { poll: 30000 });
  const items = (data?.items || []).filter((c) =>
    filter === "open" ? OPEN.includes(c.status) : filter === "merged" ? c.status === "merged" : ["rejected", "withdrawn"].includes(c.status));
  const count = (f) => (data?.items || []).filter((c) =>
    f === "open" ? OPEN.includes(c.status) : f === "merged" ? c.status === "merged" : ["rejected", "withdrawn"].includes(c.status)).length;

  return (
    <div>
      <div className="code-bar">
        <Seg size="sm" value={filter} onChange={setFilter} label="Which changes"
          options={[{ value: "open", label: "Open", count: data && count("open") },
            { value: "merged", label: "Merged", count: data && count("merged") },
            { value: "closed", label: "Closed", count: data && count("closed") }]} />
        <span className="t-note">A change starts from a file: open it, edit your lines, and add them to a change.</span>
      </div>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && items.length === 0 && <Empty title={filter === "open" ? "Nothing open." : "Nothing here yet."} />}
      {items.length > 0 && (
        <div className="table">
          <table>
            <thead><tr><th>Change</th><th>By</th><th>Status</th><th className="r">Lines</th><th className="r">Updated</th></tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="row-link" tabIndex={0} onClick={() => navigate(`/console/code/changes/${c.id}`)}
                  onKeyDown={(e) => e.key === "Enter" && navigate(`/console/code/changes/${c.id}`)}>
                  <td className="strong"><span className="mono faint">#{c.id}</span> {c.title}</td>
                  <td>{c.author}</td>
                  <td className={c.status === "review" || c.status === "conflict" ? "strong" : ""}>{STATUS[c.status]}</td>
                  <td className="r tnum">+{c.added} −{c.removed}</td>
                  <td className="r" title={dateTime(c.updated_at)}>{ago(c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
