import { useState } from "react";
import { api } from "../../../lib/api.js";
import { date } from "../../../lib/format.js";
import { useData } from "../../../lib/useData.js";
import { Status } from "../../../components/Badge.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import ApplicantsDrawer from "./ApplicantsDrawer.jsx";
import "./Careers.css";
import RoleModal from "./RoleModal.jsx";

// What's posted to the public Careers board, and who's applied. Posting and
// editing both go live immediately — there's no separate publish step.
export default function Careers() {
  const roles = useData(() => api.get("/api/careers/admin/roles"), []);
  const options = useData(() => api.get("/api/careers/admin/options"), []);
  const [editing, setEditing] = useState(null);     // null = closed, {} = new, {…} = editing that role
  const [viewing, setViewing] = useState(null);

  const items = roles.data?.items || [];

  const toggle = async (r) => {
    await api.patch(`/api/careers/admin/roles/${r.id}`, { status: r.status === "open" ? "closed" : "open" });
    roles.reload();
  };

  return (
    <div className="stack">
      <PageHeader title="Careers" subtitle="What's open on the public site.">
        <Button variant="primary" icon="plus" onClick={() => setEditing({})}>Post a role</Button>
      </PageHeader>

      <Card flush>
        <ErrorNote error={roles.error} onRetry={roles.reload} />
        {items.length === 0 ? <Empty title="Nothing posted yet.">Post a role and it shows up on the public Careers page right away.</Empty> : (
          <div className="table">
            <table>
              <thead>
                <tr><th>Role</th><th>Department</th><th>Type</th><th className="r">Applicants</th><th>Status</th><th>Posted</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td className="strong">{r.title}{r.is_demo && <span className="demo-tag">Demo</span>}</td>
                    <td>{r.department}</td>
                    <td className="wp-sub">{r.employment_type}</td>
                    <td className="r tnum">
                      <button type="button" className="text-link" onClick={() => setViewing(r.id)}>
                        {r.applicant_count > 0 ? r.applicant_count : "—"}
                      </button>
                    </td>
                    <td><Status tone={r.status === "open" ? "good" : "neutral"}>{r.status === "open" ? "Open" : "Closed"}</Status></td>
                    <td className="tnum">{date(r.posted_at)}</td>
                    <td className="r">
                      <div className="wp-actions">
                        <Button size="sm" variant="quiet" onClick={() => setEditing(r)}>Edit</Button>
                        <Button size="sm" variant="quiet" onClick={() => toggle(r)}>
                          {r.status === "open" ? "Close" : "Reopen"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <RoleModal open={Boolean(editing)} role={editing?.id ? editing : null} options={options.data}
        onClose={() => setEditing(null)} onDone={() => { setEditing(null); roles.reload(); }} />
      <ApplicantsDrawer roleId={viewing} onClose={() => setViewing(null)} />
    </div>
  );
}
