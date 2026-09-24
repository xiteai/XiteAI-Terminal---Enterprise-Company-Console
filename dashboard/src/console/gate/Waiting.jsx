import { useEffect } from "react";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { ago, date } from "../../lib/format.js";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import EntryNav from "../../pages/shared/EntryNav.jsx";
import "./Gate.css";

// A calm page for someone whose request is waiting: what they asked for, who
// can say yes, and where it's up to. It checks back on its own and opens the
// console the moment they're approved.
export default function Waiting() {
  const { me, refresh } = useSession();
  const w = me.waiting || {};
  const declined = me.user.status === "declined";

  useEffect(() => {
    if (declined) return undefined;
    const id = setInterval(() => { if (!document.hidden) refresh(); }, 15000);
    return () => clearInterval(id);
  }, [declined, refresh]);

  const signOut = async () => {
    try { await api.post("/api/auth/logout"); } finally { window.location.assign("/login"); }
  };

  const stages = [
    { label: "Request sent", sub: date(w.requested_at), state: "done" },
    { label: declined ? "Reviewed" : "Waiting for approval", sub: declined ? date(w.decided_at) : `Sent ${ago(w.requested_at)}`, state: declined ? "done" : "current" },
    { label: declined ? "Not approved" : "Welcome to the team", sub: declined ? "" : "You'll get straight in", state: declined ? "bad" : "next" },
  ];

  return (
    <div className="entry gate">
      <EntryNav cta={<button className="plain" onClick={signOut}>Sign out</button>} />
      <main className="gate-wrap">
        <motion.div className="gate-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
          <span className={cx("gate-icon", declined && "bad")}><Icon name={declined ? "circleX" : "hourglass"} size={22} /></span>
          <h1 className="t-h1">{declined ? "Your request wasn't approved" : "Your request is in"}</h1>
          <p className="gate-sub">
            {declined
              ? w.decided_by ? `${w.decided_by} reviewed it.` : "It was reviewed by the team."
              : `It's with ${w.founder_name}${w.approver_levels?.length ? ` and anyone at ${w.approver_levels.join(", ")} level who can approve new members` : ""}. You'll get in as soon as one of them says yes.`}
          </p>
          {declined && w.decision_note && <blockquote className="gate-note">“{w.decision_note}”</blockquote>}

          <ol className="gate-steps">
            {stages.map((s) => (
              <li key={s.label} className={s.state}>
                <span className="gate-dot">
                  {s.state === "done" && <Icon name="check" size={13} stroke={2.4} />}
                  {s.state === "bad" && <Icon name="x" size={13} stroke={2.4} />}
                </span>
                <span className="gate-step-text">
                  <b>{s.label}</b>
                  {s.sub && <small>{s.sub}</small>}
                </span>
              </li>
            ))}
          </ol>

          <dl className="rows gate-facts">
            <div><dt>Signed in as</dt><dd>{me.user.email}</dd></div>
            <div><dt>Level asked for</dt><dd>{w.requested_label}</dd></div>
            <div><dt>Title</dt><dd>{me.user.title || "–"}</dd></div>
            <div><dt>Team</dt><dd>{me.user.department || "–"}</dd></div>
          </dl>
          {!declined && <p className="gate-foot">You can close this page. It opens the console by itself once you're approved.</p>}
        </motion.div>
      </main>
    </div>
  );
}
