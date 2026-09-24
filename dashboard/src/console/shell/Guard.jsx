import { Navigate } from "react-router-dom";
import { useSession } from "../../lib/session.jsx";

// A page shows only if the viewer's level holds its permission.
export default function Guard({ perm, anyPerm, children, fallback = "/console" }) {
  const { can } = useSession();
  const ok = anyPerm ? anyPerm.some(can) : !perm || can(perm);
  return ok ? children : <Navigate to={fallback} replace />;
}
