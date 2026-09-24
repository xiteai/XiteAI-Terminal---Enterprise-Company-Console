import { useState } from "react";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Button from "../../../components/Button.jsx";
import Drawer from "../../../components/Drawer.jsx";
import { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { STATUS } from "./labels.js";
import ProfileSections from "./ProfileSections.jsx";
import ApproveModal from "./modals/ApproveModal.jsx";
import ChangeRoleModal from "./modals/ChangeRoleModal.jsx";
import DeactivateModal from "./modals/DeactivateModal.jsx";
import DeclineModal from "./modals/DeclineModal.jsx";
import ResetAuthenticatorModal from "./modals/ResetAuthenticatorModal.jsx";
import ResetPasswordModal from "./modals/ResetPasswordModal.jsx";

// One team member: everything their viewer may see, and the powers the
// viewer holds over them.
export default function PersonDrawer({ id, onClose, onChanged }) {
  const { refresh } = useSession();
  const { data, error, reload } = useData(() => (id ? api.get(`/api/people/${id}`) : Promise.resolve(null)), [id]);
  const [modal, setModal] = useState(null);
  const done = () => { setModal(null); reload(); onChanged?.(); refresh(); };
  const p = data;
  const st = p && STATUS[p.status];

  return (
    <Drawer open={Boolean(id)} onClose={onClose} eyebrow={p ? `${p.department || "No team"} · ${p.email}` : "Person"} title={p?.display_name || "Loading…"} width={640}>
      <ErrorNote error={error} onRetry={reload} />
      {!p && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {p && (
        <>
          <div className="pd-top">
            <Avatar initials={p.initials} level={p.level} size={44} />
            <div className="pd-top-text">
              <b>{p.title || "No title yet"}</b>
              <span>{[p.level_label, p.employment_type, st.label !== "Active" && st.label, p.is_demo && "Demo"].filter(Boolean).join(" · ")}</span>
            </div>
          </div>

          {p.status === "pending" && p.can.approve && (
            <p className="callout"><Icon name="hourglass" size={16} />
              <span><b>Waiting for a decision.</b> {p.preferred_name} asked to join as {p.requested_label || p.level_label}. Whoever decides first settles it; everyone else is told.</span>
            </p>
          )}

          {(p.can.approve || p.can.manage || p.can.fire || p.can.reset) && (
            <div className="pd-actions">
              {p.can.approve && <Button variant="primary" icon="check" onClick={() => setModal("approve")}>Approve</Button>}
              {p.can.approve && <Button variant="ghost" onClick={() => setModal("decline")}>Decline</Button>}
              {p.can.manage && <Button variant="ghost" onClick={() => setModal("role")}>Change role</Button>}
              {p.can.reset && <Button variant="ghost" onClick={() => setModal("reset")}>Reset password</Button>}
              {p.can.reset && p.status === "active" && <Button variant="ghost" onClick={() => setModal("auth")}>Reset authenticator</Button>}
              {p.can.fire && p.status === "active" && <Button variant="danger" onClick={() => setModal("fire")}>Deactivate</Button>}
              {p.can.fire && p.status === "deactivated" && <Button variant="ghost" onClick={() => setModal("rehire")}>Reactivate</Button>}
            </div>
          )}

          <ProfileSections person={p} />

          <ApproveModal open={modal === "approve"} person={p} onClose={() => setModal(null)} onDone={done} />
          <DeclineModal open={modal === "decline"} person={p} onClose={() => setModal(null)} onDone={done} />
          <ChangeRoleModal open={modal === "role"} person={p} onClose={() => setModal(null)} onDone={done} />
          <ResetPasswordModal open={modal === "reset"} person={p} onClose={() => setModal(null)} />
          <ResetAuthenticatorModal open={modal === "auth"} person={p} onClose={() => setModal(null)} />
          <DeactivateModal open={modal === "fire" || modal === "rehire"} rehire={modal === "rehire"} person={p}
            onClose={() => setModal(null)} onDone={done} />
        </>
      )}
    </Drawer>
  );
}
