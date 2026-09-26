import { NavLink, useMatch } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";
import { pickProduct } from "../../lib/product.jsx";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import Wordmark from "../../components/Wordmark.jsx";
import DemoSwitch from "./DemoSwitch.jsx";
import { COMPANY_NAV, WORKPLACE_NAV, allowed, productNav } from "./nav.js";
import ProductSwitcher from "./ProductSwitcher.jsx";
import UserMenu from "./UserMenu.jsx";

function Item({ to, end, icon, label, count }) {
  return (
    <NavLink to={to} end={end} className={({ isActive }) => cx("sb-item", isActive && "on")}>
      <Icon name={icon} size={16} />
      <span className="sb-label">{label}</span>
      {count > 0 && <span className="sb-count tnum">{count}</span>}
    </NavLink>
  );
}

// Three groups, top to bottom: home, the product you're in (switch it at the
// top of its group), and the company. You, and the demo switch, at the foot.
function Nav() {
  const { me, can } = useSession();
  const match = useMatch("/console/p/:slug/*");
  const product = pickProduct(me.products, match?.params.slug);
  const base = product && `/console/p/${product.slug}`;
  const company = COMPANY_NAV.filter((n) => allowed(n, can));
  const workplace = WORKPLACE_NAV.filter((n) => allowed(n, can));
  return (
    <div className="sb-inner">
      <NavLink to="/console" className="sb-brand" aria-label="XiteAI Terminal, home"><Wordmark /></NavLink>
      <nav className="sb-scroll scroll-y" aria-label="Console">
        <div className="sb-group">
          <Item to="/console" end icon="home" label="Home" />
          <Item to="/console/quick-links" icon="link" label="Quick Links" />
          <Item to="/console/divisions" icon="org" label="Divisions" />
          <Item to="/console/products" icon="grid" label="Products" />
        </div>
        {product && (
          <div className="sb-group">
            <span className="sb-head">Product</span>
            <ProductSwitcher current={product} />
            {productNav(product).filter((n) => can(n.perm)).map((n) => (
              <Item key={n.label} to={n.to ? `${base}/${n.to}` : base} end={n.end} icon={n.icon} label={n.label} />
            ))}
          </div>
        )}
        {workplace.length > 0 && (
          <div className="sb-group">
            <span className="sb-head">Workplace</span>
            {workplace.map((n) => <Item key={n.to} {...n} />)}
          </div>
        )}
        {company.length > 0 && (
          <div className="sb-group">
            <span className="sb-head">Company</span>
            {company.map((n) => <Item key={n.to} {...n} count={n.badge ? me.counts?.[n.badge] : 0} />)}
          </div>
        )}
      </nav>
      <div className="sb-foot">
        <DemoSwitch />
        <UserMenu />
      </div>
    </div>
  );
}

export default function Sidebar({ open, onClose }) {
  return (
    <>
      <aside className="sb">
        <Nav />
      </aside>
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="sb-scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.aside className="sb sb-mobile" initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 420, damping: 42 }}>
              <button className="sb-close" onClick={onClose} aria-label="Close menu"><Icon name="x" size={17} /></button>
              <Nav />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
