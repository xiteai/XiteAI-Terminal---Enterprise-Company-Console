import { api } from "../../../lib/api.js";
import { ago } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Icon from "../../../components/Icon.jsx";
import { useToast } from "../../../components/Toast.jsx";

const browser = (ua = "") => {
  const b = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "A browser";
  const os = /Windows/.test(ua) ? "Windows" : /Mac OS/.test(ua) ? "macOS" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Linux/.test(ua) ? "Linux" : "";
  return os ? `${b} on ${os}` : b;
};

export default function Sessions() {
  const toast = useToast();
  const { data, reload } = useData(() => api.get("/api/account/sessions"), []);
  const others = (data?.items || []).filter((s) => !s.current).length;
  const revoke = async () => {
    try {
      const r = await api.post("/api/account/sessions/revoke-others");
      toast(`Signed out of ${r.revoked} other session${r.revoked === 1 ? "" : "s"}.`);
      reload();
    } catch (e) { toast.error(e.message); }
  };
  return (
    <Card title="Where you're signed in" action={others > 0 && <Button size="sm" variant="ghost" onClick={revoke}>Sign out the others</Button>}>
      <ul className="acc-sessions">
        {(data?.items || []).map((s, i) => (
          <li key={i}>
            <Icon name={/Android|iPhone|iPad/.test(s.user_agent) ? "tablet" : "laptop"} size={17} />
            <span className="acc-session-text">
              <b>{browser(s.user_agent)}</b>
              <span>{s.ip || "unknown address"} · signed in {ago(s.created_at)} · active {ago(s.last_seen_at)}</span>
            </span>
            {s.current && <span className="acc-current">This device</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
