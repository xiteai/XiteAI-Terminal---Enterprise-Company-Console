import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api.js";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Avatar from "../../components/Avatar.jsx";
import Icon from "../../components/Icon.jsx";
import Popover from "../../components/Popover.jsx";

// You, at the foot of the sidebar. Behind it: your account, the customer
// page, sign-out and (Founder only) seeing the console as another level.
export default function UserMenu() {
  const navigate = useNavigate();
  const { me, isFounder, preview, setPreview } = useSession();
  const [open, setOpen] = useState(false);
  const signOut = async () => {
    try { await api.post("/api/auth/logout"); } finally { window.location.assign("/login"); }
  };
  const u = me.user;
  return (
    <div className="um">
      <button className={cx("um-btn", open && "on")} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Avatar initials={u.initials} level={u.level} size={32} />
        <span className="um-text">
          <b>{u.display_name}</b>
          <small>{u.level_label}{preview ? ` · previewing ${me.level_label}` : ""}</small>
        </span>
        <Icon name="chevronsUpDown" size={15} className="um-caret" />
      </button>
      <Popover open={open} onClose={() => setOpen(false)} align="left" up width={264}>
        <div className="um-head">
          <b>{u.display_name}</b>
          <span>{u.email}</span>
        </div>
        {isFounder && (
          <div className="um-block">
            <span className="um-block-head">View the console as</span>
            <div className="um-levels">
              {me.levels.map((l) => {
                const value = l.key === "founder" ? null : l.key;
                const on = (preview || null) === value;
                return (
                  <button key={l.key} className={cx("um-level", on && "on")} onClick={() => { setPreview(value); setOpen(false); }}>
                    {l.key === "founder" ? "Myself" : l.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div className="um-block um-links">
          <button onClick={() => { setOpen(false); navigate("/console/account"); }}><Icon name="account" size={16} /> Account</button>
          <a href="/" target="_blank" rel="noreferrer"><Icon name="external" size={16} /> Customer page</a>
          <button onClick={signOut}><Icon name="logout" size={16} /> Sign out</button>
        </div>
      </Popover>
    </div>
  );
}
