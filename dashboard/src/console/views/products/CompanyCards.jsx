import { Link } from "react-router-dom";
import { ago, num } from "../../../lib/format.js";
import BarList from "../../../charts/BarList.jsx";
import Avatar from "../../../components/Avatar.jsx";
import Card from "../../../components/Card.jsx";

// The team at a glance, and (for anyone who approves) who's waiting.
export default function CompanyCards({ data }) {
  const waiting = data.pending;
  return (
    <div className="grid-2 home-company">
      <Card title="Team" subtitle={`${num(data.headcount)} active, by department`}
        action={<Link className="text-link" to="/console/people">People</Link>}>
        <BarList items={data.by_department} empty="Nobody yet." />
      </Card>
      {waiting && (
        <Card title="Join requests" subtitle={waiting.length ? `${waiting.length} waiting for you` : "Nobody is waiting"}
          action={waiting.length > 0 && <Link className="text-link" to="/console/people/requests">Review</Link>}>
          {waiting.length > 0 && (
            <ul className="home-list">
              {waiting.map((p) => (
                <li key={p.id}>
                  <Link to={`/console/people/requests/${p.id}`} className="home-row">
                    <Avatar initials={p.initials} size={30} />
                    <span className="home-row-main">
                      <b>{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
                      <span>{p.level_label} · {p.title}</span>
                    </span>
                    <span className="home-row-time">{ago(p.created_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {data.recent_decisions?.length > 0 && (
            <>
              <p className="home-list-head">Decided recently</p>
              <ul className="home-list">
                {data.recent_decisions.map((p) => (
                  <li key={`d${p.id}`}>
                    <Link to={`/console/people/${p.id}`} className="home-row">
                      <Avatar initials={p.initials} size={30} />
                      <span className="home-row-main">
                        <b>{p.display_name}</b>
                        <span>
                          {p.status === "active" ? `Approved as ${p.level_label}` : <em className="home-declined">Declined</em>}
                          {" · "}{p.decider || "the team"}
                        </span>
                      </span>
                      <span className="home-row-time">{ago(p.decided_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
