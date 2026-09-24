import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Spinner from "../../../components/Spinner.jsx";

// Who reports to whom, as an indented tree with hairline connectors.
function Node({ node, open }) {
  const p = node.person;
  return (
    <li className="org-li">
      <button className="org-node" onClick={() => open(p.id)}>
        <Avatar initials={p.initials} level={p.level} size={30} />
        <span className="org-text">
          <b>{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
          <small>{p.title}{node.children.length > 0 ? ` · ${node.children.length} reporting` : ""}</small>
        </span>
        <span className="org-level">{p.level_label}</span>
      </button>
      {node.children.length > 0 && (
        <ul className="org-ul">{node.children.map((c) => <Node key={c.person.id} node={c} open={open} />)}</ul>
      )}
    </li>
  );
}

export default function OrgChart() {
  const navigate = useNavigate();
  const { data, error, reload } = useData(() => api.get("/api/people/org"), []);
  const roots = useMemo(() => {
    if (!data) return [];
    const nodes = new Map(data.items.map((p) => [p.id, { person: p, children: [] }]));
    const top = [];
    nodes.forEach((n) => {
      const boss = n.person.reports_to && nodes.get(n.person.reports_to);
      (boss ? boss.children : top).push(n);
    });
    return top;
  }, [data]);
  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (!data) return <div className="drawer-wait"><Spinner delay={300} /></div>;
  return (
    <ul className="org-ul org-root">
      {roots.map((r) => <Node key={r.person.id} node={r} open={(id) => navigate(`/console/people/${id}`)} />)}
    </ul>
  );
}
