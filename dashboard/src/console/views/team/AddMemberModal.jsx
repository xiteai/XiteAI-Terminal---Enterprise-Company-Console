import { useEffect, useMemo, useState } from "react";
import { api, qs } from "../../../lib/api.js";
import { useProduct } from "../../../lib/product.jsx";
import { cx } from "../../../lib/cx.js";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import Icon from "../../../components/Icon.jsx";
import Modal from "../../../components/Modal.jsx";
import Seg from "../../../components/Seg.jsx";
import { useToast } from "../../../components/Toast.jsx";

// Pick people from the company directory and give them a role on this product.
export default function AddMemberModal({ open, onClose, current, roles, onDone }) {
  const toast = useToast();
  const { product, slug } = useProduct();
  const [people, setPeople] = useState([]);
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState([]);
  const [role, setRole] = useState("Member");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQ(""); setPicked([]); setRole("Member");
    api.get(`/api/people${qs({ status: "active" })}`).then((r) => setPeople(r.items)).catch(() => setPeople([]));
  }, [open]);

  const onTeam = useMemo(() => new Set(current.map((p) => p.id)), [current]);
  const list = people.filter((p) => !onTeam.has(p.id))
    .filter((p) => !q || `${p.display_name} ${p.title} ${p.department}`.toLowerCase().includes(q.toLowerCase()));
  const toggle = (id) => setPicked((xs) => (xs.includes(id) ? xs.filter((x) => x !== id) : [...xs, id]));

  const save = async () => {
    setBusy(true);
    try {
      let items = current;
      for (const id of picked) {
        items = (await api.post(`/api/products/${slug}/team`, { staff_id: id, role })).items;
      }
      onDone(items);
      toast(`Added ${picked.length} ${picked.length === 1 ? "person" : "people"} to ${product.name}.`);
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Add people to ${product.name}`} width={540}
      subtitle="Choose from everyone active at XiteAI."
      footer={<>
        <Button variant="quiet" onClick={onClose}>Cancel</Button>
        <Button variant="primary" busy={busy} disabled={!picked.length} onClick={save}>
          {picked.length ? `Add ${picked.length} as ${role.toLowerCase()}` : "Add"}
        </Button>
      </>}>
      <Field icon="search" placeholder="Search by name, title or team" value={q} onChange={(e) => setQ(e.target.value)} data-autofocus />
      <div className="tm-pick scroll-y">
        {list.length === 0 && <p className="t-note tm-pick-empty">{people.length ? "Everyone who matches is already on the team." : "Loading…"}</p>}
        {list.map((p) => {
          const on = picked.includes(p.id);
          return (
            <button key={p.id} type="button" className={cx("tm-opt", on && "on")} onClick={() => toggle(p.id)} aria-pressed={on}>
              <Avatar src={p.avatar_url} initials={p.initials} level={p.level} size={32} />
              <span className="tm-opt-text">
                <b>{p.display_name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
                <small>{p.title} · {p.department} · {p.level_label}</small>
              </span>
              <span className="tm-check">{on && <Icon name="check" size={14} stroke={2.2} />}</span>
            </button>
          );
        })}
      </div>
      <div className="field">
        <span className="field-label">Their role on {product.name}</span>
        <Seg value={role} onChange={setRole} options={roles.map((r) => ({ value: r, label: r }))} label="Role" />
      </div>
    </Modal>
  );
}
