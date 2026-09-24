import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../lib/api.js";
import { useSession } from "../../lib/session.jsx";
import Switch from "../../components/Switch.jsx";
import { useToast } from "../../components/Toast.jsx";

// Show or hide demo data everywhere, instantly. Hiding keeps it in the
// database; removing it for good lives in Account.
export default function DemoSwitch() {
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const { me, can, refresh, preview } = useSession();
  const [busy, setBusy] = useState(false);
  if (!can("demo.manage") || !me.has_demo || preview) return null;

  const flip = async (show) => {
    setBusy(true);
    try {
      await api.put("/api/settings/demo", { show });
      const onDemoProduct = me.products.find((p) => p.is_demo && location.pathname.startsWith(`/console/p/${p.slug}`));
      if (!show && onDemoProduct) navigate("/console/p/xos1");
      await refresh();
      toast.info(show ? "Demo data is showing." : "Demo data is hidden. Only real data shows now.");
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <label className="sb-demo">
      <span className="sb-demo-text">
        <b>Demo data</b>
        <small>{me.show_demo ? "Shown" : "Hidden"}</small>
      </span>
      <Switch size="sm" checked={me.show_demo} disabled={busy} onChange={flip} label="Show demo data" />
    </label>
  );
}
