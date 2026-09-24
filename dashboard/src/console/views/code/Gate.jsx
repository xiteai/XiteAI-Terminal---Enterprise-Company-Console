import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api.js";
import { useSession } from "../../../lib/session.jsx";
import Button from "../../../components/Button.jsx";
import Empty from "../../../components/Empty.jsx";

// What someone sees instead of code when the door is shut: no authenticator
// yet, a session opened without a code, or access paused by the reading alarm.
export default function Gate({ kind }) {
  const { me } = useSession();
  const [busy, setBusy] = useState(false);
  const again = async () => {
    setBusy(true);
    try { await api.post("/api/auth/logout"); } catch { /* signing in again is the point either way */ }
    window.location.assign("/login");
  };
  if (kind === "paused") {
    return (
      <Empty title="Your code access is paused.">
        A lot of code was opened from your account in a short time, so it paused itself. The founder has been told and
        can resume it. If that was you, let them know; if it wasn't, change your password now.
      </Empty>
    );
  }
  const on = me?.authenticator?.on;
  return (
    <Empty title="Company code needs your authenticator."
      action={on
        ? <Button variant="primary" busy={busy} onClick={again}>Sign out and back in with a code</Button>
        : <Link className="text-link" to="/console/account#authenticator">Set it up in Account</Link>}>
      {on
        ? "Your authenticator is on, but this session was opened before it was. Sign in again, with a code, to open code."
        : "A 6-digit code from your phone at every sign-in. It takes a minute to set up; then sign in again with a code."}
    </Empty>
  );
}
