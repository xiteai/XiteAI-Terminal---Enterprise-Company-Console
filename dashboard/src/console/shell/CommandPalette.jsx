import { useEffect, useMemo, useState } from "react";
import { useMatch, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";
import { api, qs } from "../../lib/api.js";
import { pickProduct, words } from "../../lib/product.jsx";
import { useDebounced } from "../../lib/useData.js";
import { useSession } from "../../lib/session.jsx";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import { Portal, useOverlay } from "../../components/Overlay.jsx";
import { COMPANY_NAV, allowed, productNav } from "./nav.js";
import "../../components/Modal.css";

// Ctrl/⌘ K: jump to any page or product, or find an install or a person.
export default function CommandPalette({ open, onClose }) {
  const navigate = useNavigate();
  const { me, can } = useSession();
  const match = useMatch("/console/p/:slug/*");
  const product = pickProduct(me.products, match?.params.slug);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [found, setFound] = useState([]);
  const query = useDebounced(q, 200);
  const panel = useOverlay(open, onClose);

  useEffect(() => { if (open) { setQ(""); setSel(0); setFound([]); } }, [open]);
  useEffect(() => {
    if (!open || query.trim().length < 2) { setFound([]); return undefined; }
    let alive = true;
    const jobs = [];
    if (product && can("installs")) {
      jobs.push(api.get(`/api/installs${qs({ product: product.slug, q: query, page_size: 5 })}`).then((r) => r.items.map((i) => ({
        key: `i${i.id}`, icon: "installs", label: i.person?.name || i.code, sub: `${product.name} ${words(product).one} · ${i.code}`,
        to: `/console/p/${product.slug}/installs/${i.id}`,
      }))));
    }
    if (can("people.directory")) {
      jobs.push(api.get(`/api/people${qs({ q: query })}`).then((r) => r.items.slice(0, 5).map((p) => ({
        key: `p${p.id}`, icon: "people", label: p.display_name, sub: `${p.title} · ${p.level_label}`, to: `/console/people/${p.id}`,
      }))));
    }
    Promise.all(jobs.map((j) => j.catch(() => []))).then((groups) => alive && setFound(groups.flat()));
    return () => { alive = false; };
  }, [query, open, can, product]);

  const places = useMemo(() => {
    const all = [
      { key: "home", icon: "home", label: "Home", sub: "Page", to: "/console" },
      ...me.products.map((p) => ({ key: `prod-${p.slug}`, icon: "box", label: p.name, sub: "Product", to: `/console/p/${p.slug}` })),
      ...(product ? productNav(product).filter((n) => can(n.perm)).map((n) => ({
        key: `pn-${n.label}`, icon: n.icon, label: `${n.label}`, sub: product.name,
        to: n.to ? `/console/p/${product.slug}/${n.to}` : `/console/p/${product.slug}`,
      })) : []),
      ...COMPANY_NAV.filter((n) => allowed(n, can)).map((n) => ({ key: n.to, icon: n.icon, label: n.label, sub: "Page", to: n.to })),
      { key: "account", icon: "account", label: "Account", sub: "Page", to: "/console/account" },
    ];
    const needle = q.trim().toLowerCase();
    return needle ? all.filter((p) => `${p.label} ${p.sub}`.toLowerCase().includes(needle)) : all;
  }, [q, can, me.products, product]);
  const results = [...places, ...found];

  const go = (r) => { onClose(); navigate(r.to); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(results.length - 1, s + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
    if (e.key === "Enter" && results[sel]) go(results[sel]);
  };

  return (
    <Portal>
      <AnimatePresence>
        {open && (
          <motion.div className="modal-scrim cmdk-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
            <motion.div ref={panel} tabIndex={-1} className="cmdk" role="dialog" aria-label="Search the console"
              initial={{ opacity: 0, y: -8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4 }}
              transition={{ type: "spring", stiffness: 480, damping: 36 }}>
              <div className="cmdk-input">
                <Icon name="search" size={18} />
                <input data-autofocus value={q} onChange={(e) => { setQ(e.target.value); setSel(0); }} onKeyDown={onKey}
                  placeholder="Go to a page or product, or find an install or a person" />
                <kbd>Esc</kbd>
              </div>
              <div className="cmdk-list scroll-y" role="listbox">
                {results.length === 0 && <p className="cmdk-empty">No matches.</p>}
                {results.map((r, i) => (
                  <button key={r.key} role="option" aria-selected={i === sel} className={cx("cmdk-item", i === sel && "on")}
                    onMouseEnter={() => setSel(i)} onClick={() => go(r)}>
                    <Icon name={r.icon} size={16} />
                    <span className="cmdk-label">{r.label}</span>
                    <span className="cmdk-sub">{r.sub}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </Portal>
  );
}
