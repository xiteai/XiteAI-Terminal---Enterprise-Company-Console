import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api.js";
import { ago } from "../../lib/format.js";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import Popover from "../../components/Popover.jsx";

// The bell: a few short lines, newest first. Opening one marks it read and
// goes where it points.
export default function Bell() {
  const navigate = useNavigate();
  const { me, refresh } = useSession();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState({ items: [], unread: me?.counts?.unread || 0 });

  const load = useCallback(() => api.get("/api/notifications").then(setData).catch(() => {}), []);
  useEffect(() => {
    load();
    const id = setInterval(() => { if (!document.hidden) load(); }, 30000);
    return () => clearInterval(id);
  }, [load, me.show_demo]);

  const openItem = async (n) => {
    setOpen(false);
    if (!n.read_at) await api.post("/api/notifications/read", { ids: [n.id] }).catch(() => {});
    load();
    refresh();
    if (n.link) navigate(n.link);
  };
  const readAll = async () => {
    await api.post("/api/notifications/read", { ids: null }).catch(() => {});
    load();
    refresh();
  };

  return (
    <div className="tb-anchor">
      <button className={cx("tb-icon", open && "on")} onClick={() => setOpen((o) => !o)}
        aria-label={`Notifications${data.unread ? `, ${data.unread} unread` : ""}`}>
        <Icon name="bell" size={17} />
        {data.unread > 0 && <span className="tb-badge" aria-hidden />}
      </button>
      <Popover open={open} onClose={() => setOpen(false)} width={380}>
        <div className="bell-head">
          <b>Notifications</b>
          {data.unread > 0 && <button onClick={readAll}>Mark all as read</button>}
        </div>
        <div className="bell-list scroll-y">
          {data.items.length === 0 && <p className="bell-empty">No notifications.</p>}
          {data.items.map((n) => (
            <button key={n.id} className={cx("bell-item", !n.read_at && "unread")} onClick={() => openItem(n)}>
              <span className="bell-text">
                <b>{n.title}</b>
                {n.body && <span>{n.body}</span>}
                <small>{ago(n.created_at)}</small>
              </span>
            </button>
          ))}
        </div>
      </Popover>
    </div>
  );
}
