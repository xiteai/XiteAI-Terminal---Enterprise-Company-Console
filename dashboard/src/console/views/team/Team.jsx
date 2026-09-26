import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { date } from "../../../lib/format.js";
import { useProduct } from "../../../lib/product.jsx";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import Card from "../../../components/Card.jsx";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Select from "../../../components/Select.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { useToast } from "../../../components/Toast.jsx";
import AddMemberModal from "./AddMemberModal.jsx";
import "./Team.css";

const ROLE_NOTE = { Owner: "Final say on the product", Lead: "Runs it day to day", Member: "Works on it" };

// Who works on this product. Anyone at the company can be on several products.
export default function Team() {
  const toast = useToast();
  const { product, slug } = useProduct();
  const { data, error, reload, mutate } = useData(() => api.get(`/api/products/${slug}/team`), [slug]);
  const [adding, setAdding] = useState(false);
  const manage = data?.can_manage;

  const setRole = async (person, role) => {
    try {
      const r = await api.post(`/api/products/${slug}/team`, { staff_id: person.id, role });
      mutate((d) => ({ ...d, items: r.items }));
      toast(`${person.display_name} is now ${role.toLowerCase()} on ${product.name}.`);
    } catch (e) { toast.error(e.message); }
  };
  const remove = async (person) => {
    try {
      const r = await api.del(`/api/products/${slug}/team/${person.id}`);
      mutate((d) => ({ ...d, items: r.items }));
      toast(`${person.display_name} is off the ${product.name} team.`);
    } catch (e) { toast.error(e.message); }
  };

  const counts = (data?.items || []).reduce((a, p) => ({ ...a, [p.role]: (a[p.role] || 0) + 1 }), {});
  return (
    <div>
      <PageHeader title="Team" subtitle={`Who builds and runs ${product.name}.`}
        meta={data && <>{["Owner", "Lead", "Member"].map((r) => counts[r] ? <span key={r}><b>{counts[r]}</b> {counts[r] === 1 ? r.toLowerCase() : `${r.toLowerCase()}s`}</span> : null)}</>}>
        {manage && <Button variant="primary" icon="plus" onClick={() => setAdding(true)}>Add people</Button>}
      </PageHeader>
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && (
        <Card flush>
          {data.items.length === 0 ? (
            <Empty title="Nobody on this product yet."
              action={manage && <Button variant="ghost" icon="plus" onClick={() => setAdding(true)}>Add people</Button>}>
              Add the people who work on {product.name} so everyone knows who to ask.
            </Empty>
          ) : (
            <div className="table">
              <table>
                <thead>
                  <tr><th>Name</th><th>Title</th><th>Level</th><th>Role on {product.name}</th><th>Added</th>{manage && <th className="r" />}</tr>
                </thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link to={`/console/people/${p.id}`} className="tm-person">
                          <Avatar src={p.avatar_url} initials={p.initials} level={p.level} size={32} />
                          <span className="tm-person-text">
                            <b>{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
                            <small>{p.email}</small>
                          </span>
                        </Link>
                      </td>
                      <td>{p.title || "–"}<small className="tm-dept">{p.department}</small></td>
                      <td className="muted">{p.level_label}</td>
                      <td>
                        {manage ? (
                          <Select size="sm" className="select-bare" value={p.role} onChange={(v) => setRole(p, v)} label={undefined}
                            options={data.roles.map((r) => ({ value: r, label: r }))} aria-label={`Role for ${p.display_name}`} />
                        ) : (
                          <span className="tm-role">{p.role}<small>{ROLE_NOTE[p.role]}</small></span>
                        )}
                      </td>
                      <td className="muted">{date(p.added_at)}</td>
                      {manage && (
                        <td className="r"><Button size="sm" variant="quiet" onClick={() => remove(p)}>Remove</Button></td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
      <AddMemberModal open={adding} onClose={() => setAdding(false)} current={data?.items || []} roles={data?.roles || []}
        onDone={(items) => mutate((d) => ({ ...d, items }))} />
    </div>
  );
}
