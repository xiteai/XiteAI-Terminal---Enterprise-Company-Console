import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, qs } from "../../../lib/api.js";
import { useData, useDebounced } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Field from "../../../components/Field.jsx";
import Seg from "../../../components/Seg.jsx";
import Select from "../../../components/Select.jsx";
import { STATUS } from "./labels.js";
import PersonDrawer from "./PersonDrawer.jsx";

export default function Directory() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("active");
  const [dept, setDept] = useState("");
  const [q, setQ] = useState("");
  const query = useDebounced(q, 250);
  const { data, error, reload } = useData(() => api.get(`/api/people${qs({ status, q: query })}`), [status, query]);
  const items = useMemo(() => (data?.items || []).filter((p) => !dept || p.department === dept), [data, dept]);
  const c = data?.counts || {};
  const open = (p) => navigate(`/console/people/${p.id}`);

  return (
    <>
      <div className="toolbar">
        <Field icon="search" placeholder="Search name, title, team…" value={q} onChange={(e) => setQ(e.target.value)} />
        {data?.can_see_all && (
          <Seg size="sm" value={status} onChange={setStatus} label="Status" options={[
            { value: "active", label: "Active", count: c.active || 0 },
            { value: "pending", label: "Waiting", count: c.pending || 0 },
            { value: "deactivated", label: "Deactivated", count: c.deactivated || 0 },
            { value: "declined", label: "Declined", count: c.declined || 0 },
          ]} />
        )}
        <Select size="sm" value={dept} onChange={setDept} placeholder="All teams" options={data?.departments || []} />
      </div>
      <ErrorNote error={error} onRetry={reload} />
      {data && (
        <Card flush>
          {items.length === 0 ? <Empty title="Nobody here.">Try another search or filter.</Empty> : (
            <div className="table">
              <table>
                <thead><tr><th>Name</th><th>Title</th><th>Team</th><th>Level</th><th>{status === "active" ? "Email" : "Status"}</th></tr></thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id} className="row-link" tabIndex={0} onClick={() => open(p)} onKeyDown={(e) => e.key === "Enter" && open(p)}>
                      <td>
                        <span className="pp-person">
                          <Avatar src={p.avatar_url} initials={p.initials} level={p.level} size={28} />
                          <b>{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
                        </span>
                      </td>
                      <td>{p.title || "–"}</td>
                      <td className="muted">{p.department}</td>
                      <td className="muted">{p.level_label}</td>
                      <td className="muted">{status === "active" ? p.email : STATUS[p.status].label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
      <PersonDrawer id={id} onClose={() => navigate("/console/people")} onChanged={reload} />
    </>
  );
}
