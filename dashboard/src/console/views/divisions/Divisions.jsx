import { useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import "./Divisions.css";

// engineering-ish leans structural, design leans creative, etc. — a visual
// cue, not a taxonomy; departments not listed here fall back to `org`.
const ICON = {
  Engineering: "code", Product: "box", Design: "sparkle", "Data & AI": "activity",
  Marketing: "send", Sales: "activity", "Customer Success": "heart", "People & HR": "people",
  Finance: "briefcase", Operations: "grid", Legal: "file", Leadership: "cap",
};

// One card per division: who's in it, at a glance, and a door into its own
// room. Chat, uploads and checkpoints for that team are next.
export default function Divisions() {
  const opts = useData(() => api.get("/api/join/options"), []);
  const people = useData(() => api.get("/api/people"), []);
  const names = opts.data?.departments || [];

  const byDept = useMemo(() => {
    const out = {};
    (people.data?.items || []).forEach((p) => { (out[p.department] ||= []).push(p); });
    return out;
  }, [people.data]);

  return (
    <div className="stack">
      <PageHeader title="Divisions" subtitle="Every team's own space." />
      <div className="dv-grid">
        {names.map((name) => {
          const members = byDept[name] || [];
          return (
            <Link key={name} to={`/console/divisions/${encodeURIComponent(name)}`} className="dv-card">
              <div className="dv-top">
                <span className="dv-icon"><Icon name={ICON[name] || "org"} size={20} /></span>
                <Icon name="arrowRight" size={15} className="dv-go" />
              </div>
              <span className="dv-name">{name}</span>
              <div className="dv-foot">
                {members.length > 0 ? (
                  <>
                    <div className="dv-stack">
                      {members.slice(0, 4).map((m) => <Avatar key={m.id} src={m.avatar_url} initials={m.initials} level={m.level} size={22} />)}
                    </div>
                    <span className="dv-count">{members.length} {members.length === 1 ? "person" : "people"}</span>
                  </>
                ) : <span className="dv-count">Nobody yet</span>}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
