import { SessionProvider, useSession } from "../lib/session.jsx";
import Spinner from "../components/Spinner.jsx";
import ForcePassword from "./gate/ForcePassword.jsx";
import Waiting from "./gate/Waiting.jsx";
import Shell from "./shell/Shell.jsx";

// Who gets what: pending and declined people see their request, anyone told
// to change their password does that first, everyone else gets the console.
function Gate() {
  const { me, error } = useSession();
  if (!me) {
    return (
      <div style={{ height: "100vh", display: "grid", placeItems: "center", color: "var(--muted)" }}>
        {error ? <p>{error.message}</p> : <Spinner size={20} delay={300} />}
      </div>
    );
  }
  if (me.user.status !== "active") return <Waiting />;
  if (me.user.must_change_pw) return <ForcePassword />;
  return <Shell />;
}

export default function Console() {
  return (
    <SessionProvider>
      <Gate />
    </SessionProvider>
  );
}
