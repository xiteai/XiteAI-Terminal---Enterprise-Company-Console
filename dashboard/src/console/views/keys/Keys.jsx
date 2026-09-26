import { useState } from "react";
import { api } from "../../../lib/api.js";
import { ago, dateTime } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import ReplaceKey from "./ReplaceKey.jsx";
import RevealKey from "./RevealKey.jsx";
import "./Keys.css";

// The keys every XOS1 install reaches its AI through. They're kept in the
// server's vault, encrypted, and used on the app's behalf — no installed copy
// of XOS1 ever holds one.
export default function Keys() {
  const toast = useToast();
  const { data, error, reload, mutate } = useData(() => api.get("/api/ai-keys"), []);
  const [editing, setEditing] = useState(null);
  const [revealing, setRevealing] = useState(null);

  const history = data
    ? data.providers.flatMap((p) => p.history.map((h) => ({ ...h, label: p.label })))
      .sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, 12)
    : [];

  return (
    <div>
      <PageHeader title="AI keys"
        subtitle="Kept encrypted in the server's vault and used on the app's behalf, so no installed copy of XOS1 ever carries one."
        meta={data && <>
          <span>Vault <b>{data.vault_ready ? "ready" : "not set up"}</b></span>
          <span>Cloudflare <b>{data.cloudflare ? "connected" : "not connected"}</b></span>
        </>} />
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && !data.cloudflare && (
        <div className="callout keys-callout">
          <Icon name="info" size={16} />
          <span>
            <b>Cloudflare isn't connected yet.</b> You can test a key now. Replacing one needs <span className="code">CF_ACCOUNT_ID</span>,{" "}
            <span className="code">CF_API_TOKEN</span> and <span className="code">CF_SECRETS_STORE_ID</span> in the server's .env.
          </span>
        </div>
      )}
      {data && (
        <Card flush>
          <div className="table">
            <table>
              <thead>
                <tr><th>Provider</th><th>Key now</th><th>Last changed</th><th className="r" /></tr>
              </thead>
              <tbody>
                {data.providers.map((p) => (
                  <tr key={p.key}>
                    <td className="keys-prov"><b>{p.label}</b><span>{p.role}</span></td>
                    <td>{p.current ? <span className="mono">…{p.current.last4}</span> : <span className="faint">Not replaced here yet</span>}</td>
                    <td>{p.current ? <span title={dateTime(p.current.at)}>{p.current.by}, {ago(p.current.at)}</span> : <span className="faint">–</span>}</td>
                    <td className="r">
                      <div className="wp-actions">
                        {data.can_reveal && p.in_vault && (
                          <Button size="sm" variant="quiet" icon="eye" onClick={() => setRevealing(p)}>Show</Button>
                        )}
                        {data.can_replace && <Button size="sm" onClick={() => setEditing(p)}>Replace</Button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {data && (
        <Card title="Recent changes" subtitle="Every attempt, including refused ones. Also in the audit log.">
          {history.length === 0 && <p className="t-note">No key has been changed from here yet.</p>}
          {history.length > 0 && (
            <ol className="keys-history">
              {history.map((h, i) => (
                <li key={i}>
                  <span className="keys-when" title={dateTime(h.at)}>{ago(h.at)}</span>
                  <span><b>{h.by}</b> {h.outcome === "live" ? "replaced" : "tried to replace"} the {h.label} key with <span className="mono">…{h.last4}</span></span>
                  <span className={h.outcome === "live" ? "keys-live" : "keys-refused"}>{h.outcome === "live" ? "Live" : "Refused"}</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
      <ReplaceKey provider={editing} needsCode={data?.needs_code} cloudflare={data?.cloudflare}
        onClose={() => setEditing(null)}
        onDone={(r) => { setEditing(null); mutate((d) => ({ ...d, providers: r.providers })); toast(r.message); }} />
      {revealing && <RevealKey provider={revealing} needsCode={data?.needs_code} onClose={() => setRevealing(null)} />}
    </div>
  );
}
