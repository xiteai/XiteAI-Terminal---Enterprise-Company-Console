import { useNavigate } from "react-router-dom";
import { ago } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import Card from "../../../components/Card.jsx";

// The last few to check in. Names appear only if your level sees them.
export default function RecentCheckins({ items }) {
  const navigate = useNavigate();
  const { product, base } = useProduct();
  const w = words(product);
  const showName = items.some((c) => c.person && "name" in c.person);
  const open = (c) => navigate(`${base}/installs/${c.id}`);
  return (
    <Card flush title="Latest check-ins">
      <div className="table">
        <table>
          <thead>
            <tr>
              <th>{w.unit.slice(0, -1)}</th>
              {showName && <th>Person</th>}
              <th>Where</th>
              <th>Version</th>
              <th className="r">When</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c, i) => (
              <tr key={`${c.id}-${i}`} className="row-link" onClick={() => open(c)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && open(c)}>
                <td className="mono">{c.code}{c.is_demo && <span className="demo-tag">Demo</span>}</td>
                {showName && <td>{c.person?.name || <span className="muted">Not shared</span>}</td>}
                <td className="muted">{[c.region, c.person?.age_band].filter(Boolean).join(" · ") || c.device_type}</td>
                <td className="tnum">{c.version}</td>
                <td className="r muted">{ago(c.at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
