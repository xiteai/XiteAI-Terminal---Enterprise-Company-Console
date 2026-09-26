import { delta, num, pct } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import StatTile from "../../../charts/StatTile.jsx";

// The headline figures, side by side on one ruled row.
export default function Figures({ data, range }) {
  const { product } = useProduct();
  const w = words(product);
  const k = data.kpis;
  return (
    <div className="kpis">
      <StatTile label={`Active ${w.many}`} value={num(k.active_period)}
        delta={delta(k.active_period, k.active_prev_period)} period={`prior ${range} days`} />
      <StatTile label="Active today" value={num(k.active_24h)} note={`of ${num(k.total_installs)} ${w.many}`} />
      <StatTile label="Downloads" value={num(k.downloads_period)}
        note={`${num(k.downloads_total)} all time`} />
      <StatTile label="On latest" value={pct(k.on_latest)} note={`version ${data.latest_version || "–"}`} />
      {product.kind === "web"
        ? <StatTile label={`New ${w.many}`} value={num(k.new_installs)}
            delta={delta(k.new_installs, k.new_installs_prev)} period={`prior ${range} days`} />
        : <StatTile label="Updates installed" value={pct(k.update_ok, 1)} note="last update" />}
      <StatTile label="Crash-free" value={pct(k.crash_free, 1)} note="last 7 days" />
      <StatTile label="Open requests" value={num(k.open_tickets)}
        note={k.urgent_tickets ? `${k.urgent_tickets} high priority` : "none urgent"} />
    </div>
  );
}
