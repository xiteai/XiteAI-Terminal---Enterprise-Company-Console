import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { words } from "../../lib/product.jsx";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import Popover from "../../components/Popover.jsx";
import ProductLogo from "../../components/ProductLogo.jsx";
import NewProductModal from "../views/home/NewProductModal.jsx";

// Which product the sidebar is showing. Switching keeps you on the same kind
// of page (Support in one product opens Support in the other).
export default function ProductSwitcher({ current }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { me, can } = useSession();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const go = (slug) => {
    setOpen(false);
    const m = location.pathname.match(/^\/console\/p\/[^/]+\/?([^/]*)/);
    navigate(`/console/p/${slug}${m && m[1] ? `/${m[1]}` : ""}`);
  };

  return (
    <div className="ps">
      <button className={cx("ps-btn", open && "on")} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="listbox">
        <ProductLogo product={current} size={24} />
        <span className="ps-text">
          <b>{current.name}</b>
          <small>{words(current).kind}{current.is_demo ? " · Demo" : ""}</small>
        </span>
        <Icon name="chevronsUpDown" size={15} className="ps-caret" />
      </button>
      <Popover open={open} onClose={() => setOpen(false)} align="left" width="100%">
        <div className="ps-menu" role="listbox" aria-label="Products">
          <span className="ps-menu-head">Switch product</span>
          {me.products.map((p) => (
            <button key={p.slug} role="option" aria-selected={p.slug === current.slug}
              className={cx("ps-opt", p.slug === current.slug && "on")} onClick={() => go(p.slug)}>
              <ProductLogo product={p} size={24} />
              <span className="ps-text">
                <b>{p.name}</b>
                <small>{words(p).kind} · v{p.latest_version || "–"}{p.is_demo ? " · Demo" : ""}</small>
              </span>
              {p.slug === current.slug && <Icon name="check" size={15} />}
            </button>
          ))}
          <div className="ps-menu-foot">
            <button onClick={() => { setOpen(false); navigate("/console"); }}><Icon name="grid" size={15} /> All products</button>
            {can("products.manage") && (
              <button onClick={() => { setOpen(false); setCreating(true); }}><Icon name="plus" size={15} /> New product</button>
            )}
          </div>
        </div>
      </Popover>
      <NewProductModal open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
