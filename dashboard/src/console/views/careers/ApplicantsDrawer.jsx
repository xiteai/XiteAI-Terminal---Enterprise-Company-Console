import { api } from "../../../lib/api.js";
import { date } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Drawer from "../../../components/Drawer.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Spinner from "../../../components/Spinner.jsx";

export default function ApplicantsDrawer({ roleId, onClose }) {
  const { data, error, loading } = useData(() => (roleId ? api.get(`/api/careers/admin/roles/${roleId}/applicants`) : Promise.resolve(null)), [roleId]);

  return (
    <Drawer open={Boolean(roleId)} onClose={onClose} eyebrow={data?.role?.department}
      title={data ? `${data.role.title} — applicants` : "Applicants"} width={560}>
      <ErrorNote error={error} />
      {loading && !data && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (data.items.length === 0 ? <Empty title="Nobody's applied yet." /> : (
        <ul className="ap-list">
          {data.items.map((p) => (
            <li key={p.id}>
              <Avatar initials={p.name[0]} size={34} />
              <div className="ap-text">
                <b>{p.name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
                <span>{p.email}{p.phone && ` · ${p.phone}`}</span>
                {p.portfolio && <a href={p.portfolio} target="_blank" rel="noreferrer" className="text-link">{p.portfolio}</a>}
                {p.note && <p className="ap-note">“{p.note}”</p>}
              </div>
              <span className="ap-when">{date(p.applied_at)}</span>
            </li>
          ))}
        </ul>
      ))}
    </Drawer>
  );
}
