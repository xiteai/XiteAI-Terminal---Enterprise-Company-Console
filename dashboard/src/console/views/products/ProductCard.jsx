import { Link } from "react-router-dom";
import { num } from "../../../lib/format.js";
import { STATUS, words } from "../../../lib/product.jsx";
import Icon from "../../../components/Icon.jsx";
import ProductLogo from "../../../components/ProductLogo.jsx";

// One product on the home screen: who it is, and four numbers. The whole
// row opens it. A status only shows when it isn't the normal "live".
export default function ProductCard({ product: p }) {
  const w = words(p);
  const s = p.stats || {};
  const status = p.status && p.status !== "live" ? STATUS[p.status]?.label : null;
  return (
    <Link to={`/console/p/${p.slug}`} className="pcard">
      <div className="pcard-head">
        <ProductLogo product={p} size={36} />
        <div className="pcard-name">
          <b>{p.name}{p.is_demo && <span className="demo-tag">Demo</span>}</b>
          <span>{[w.kind, p.latest_version && `v${p.latest_version}`, status].filter(Boolean).join(" · ")}</span>
        </div>
        <Icon name="chevronRight" size={16} className="pcard-go" />
      </div>
      <dl className="pcard-stats">
        <div><dt>{w.unit}</dt><dd className="tnum">{num(s.installs)}</dd></div>
        <div><dt>Active today</dt><dd className="tnum">{num(s.active_today)}</dd></div>
        <div><dt>Open tickets</dt><dd className="tnum">{num(s.open_tickets)}</dd></div>
        <div><dt>Team</dt><dd className="tnum">{num(s.team)}</dd></div>
      </dl>
    </Link>
  );
}
