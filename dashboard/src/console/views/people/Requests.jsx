import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { ageFrom, ago, date } from "../../../lib/format.js";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import PersonDrawer from "./PersonDrawer.jsx";

// Everyone waiting for someone at your level (or above) to let them in.
export default function Requests() {
  const { rid } = useParams();
  const navigate = useNavigate();
  const { refresh } = useSession();
  const { data, error, reload } = useData(() => api.get("/api/requests"), []);
  const open = (id) => navigate(`/console/people/requests/${id}`);
  return (
    <>
      <ErrorNote error={error} onRetry={reload} />
      {data && data.items.length === 0 && (
        <Empty title="Nobody is waiting.">New requests for levels below yours arrive here and in your notifications.</Empty>
      )}
      {data && data.items.length > 0 && (
        <ul className="rq-list">
          {data.items.map((p) => {
            const pr = p.profile || {};
            const facts = [pr.city, pr.dob && `${ageFrom(pr.dob)} years old`, pr.experience?.years && `${pr.experience.years} years' experience`,
              pr.education?.institution, p.start_date && `Starts ${date(`${p.start_date}T00:00:00`)}`].filter(Boolean);
            return (
              <li key={p.id}>
                <button className="rq" onClick={() => open(p.id)}>
                  <Avatar src={p.avatar_url} initials={p.initials} size={36} />
                  <span className="rq-main">
                    <span className="rq-name">{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</span>
                    <span className="rq-role">{p.title} · {p.department} · {p.employment_type}</span>
                    {facts.length > 0 && <span className="rq-facts">{facts.join(" · ")}</span>}
                  </span>
                  <span className="rq-side">
                    <span className="rq-level">{p.level_label}</span>
                    <span className="rq-time">Asked {ago(p.created_at)}</span>
                  </span>
                  <Icon name="chevronRight" size={16} className="rq-go" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <PersonDrawer id={rid} onClose={() => navigate("/console/people/requests")} onChanged={() => { reload(); refresh(); }} />
    </>
  );
}
