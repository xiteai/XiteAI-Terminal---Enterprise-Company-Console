import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import { useSession } from "../../../lib/session.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { Checkbox } from "../../../components/Switch.jsx";
import { useToast } from "../../../components/Toast.jsx";
import "./Access.css";

// The Founder's control over who sees what. Each checkbox saves the moment it
// changes; a small bar marks anything changed from its level's default.
export default function Access() {
  const toast = useToast();
  const { refresh } = useSession();
  const { data, error, reload, mutate } = useData(() => api.get("/api/access"), []);
  const [saving, setSaving] = useState(null);

  const flip = async (level, perm, allowed) => {
    setSaving(`${level}:${perm}`);
    mutate((d) => ({ ...d, matrix: { ...d.matrix, [level]: allowed ? [...d.matrix[level], perm] : d.matrix[level].filter((p) => p !== perm) } }));
    try {
      const next = await api.put("/api/access", { level, perm, allowed });
      mutate(() => next);
      refresh();
    } catch (e) {
      toast.error(e.message);
      reload();
    } finally {
      setSaving(null);
    }
  };
  const resetLevel = async (level, label) => {
    try {
      const next = await api.del(`/api/access/${level}`);
      mutate(() => next);
      toast(`${label} is back to its defaults.`);
    } catch (e) { toast.error(e.message); reload(); }
  };

  return (
    <div>
      <PageHeader title="Access" subtitle="What each level can see and do. Changes save as you make them."
        meta={data && <><span><b>{data.overrides}</b> changed from default</span><span><b>{data.levels.length}</b> levels</span></>} />
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <Card flush>
          <div className="table ac-wrap">
            <table>
              <thead>
                <tr>
                  <th className="ac-perm-h">Permission</th>
                  {data.levels.map((l) => (
                    <th key={l.key} className="ac-level-h">
                      <span className="ac-level">{l.label}</span>
                      <button className="ac-reset" onClick={() => resetLevel(l.key, l.label)}>Reset</button>
                    </th>
                  ))}
                </tr>
              </thead>
              {data.groups.map((g) => (
                <tbody key={g.name}>
                  <tr className="ac-group"><td colSpan={data.levels.length + 1}>{g.name}</td></tr>
                  {g.perms.map((p) => (
                    <tr key={p.key}>
                      <td className="ac-perm"><b>{p.label}</b><span>{p.hint}</span></td>
                      {data.levels.map((l) => {
                        const on = data.matrix[l.key].includes(p.key);
                        const changed = on !== data.defaults[l.key].includes(p.key);
                        return (
                          <td key={l.key} className="ac-cell">
                            <span className="ac-cell-in">
                              <Checkbox checked={on} disabled={saving === `${l.key}:${p.key}`}
                                onChange={(v) => flip(l.key, p.key, v)} label={`${p.label} for ${l.label}`} />
                              {changed && <i className="ac-changed" title="Changed from the default" />}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              ))}
            </table>
          </div>
        </Card>
      )}
      {data && (
        <p className="ac-foot">
          {data.overrides ? `${data.overrides} setting${data.overrides > 1 ? "s" : ""} changed from the defaults, marked with a small bar. ` : "Every level is on its defaults. "}
          You always have everything. People powers (approve, change, deactivate, reset) only work on levels below the holder's own.
        </p>
      )}
    </div>
  );
}
