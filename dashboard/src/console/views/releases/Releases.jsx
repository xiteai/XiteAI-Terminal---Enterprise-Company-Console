import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../../lib/motion.js";
import { api, qs } from "../../../lib/api.js";
import { num, pct } from "../../../lib/format.js";
import { useProduct, words } from "../../../lib/product.jsx";
import { useData } from "../../../lib/useData.js";
import { cx } from "../../../lib/cx.js";
import Empty, { ErrorNote } from "../../../components/Empty.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import Spinner from "../../../components/Spinner.jsx";
import "./Releases.css";

// Every version: what changed (the same notes people see in the app), and how
// many active installs run it.
export default function Releases() {
  const { product, slug } = useProduct();
  const w = words(product);
  const { data, error, reload } = useData(() => api.get(`/api/releases${qs({ product: slug })}`), [slug]);
  const [open, setOpen] = useState(null);
  return (
    <div>
      <PageHeader title="Releases"
        meta={data && <><span>Latest <b>{data.latest_version || "–"}</b></span><span><b>{num(data.active_installs)}</b> active {w.many} in 30 days</span></>} />
      <ErrorNote error={error} onRetry={reload} />
      {!data && !error && <div className="drawer-wait"><Spinner delay={300} /></div>}
      {data && data.releases.length === 0 && (
        <Empty title="No releases yet.">Versions appear here once {w.many} check in with them.</Empty>
      )}
      {data && data.releases.length > 0 && (
        <ol className="rel-list">
          {data.releases.map((r) => {
            const isOpen = open === r.version || (open === null && r.is_latest);
            const canOpen = r.sections.length > 0;
            return (
              <li key={r.version} className={cx("rel", r.is_latest && "latest", isOpen && "open")}>
                <button className="rel-head" onClick={() => canOpen && setOpen(isOpen ? "" : r.version)} aria-expanded={canOpen ? isOpen : undefined} disabled={!canOpen}>
                  <span className="rel-version">
                    <b className="mono">{r.version}</b>
                    {r.is_latest && <small>Latest</small>}
                  </span>
                  <span className="rel-main">
                    <span className="rel-headline">{r.headline || "No release notes for this version."}</span>
                    {r.notes && <span className="rel-notes-line">{r.notes}</span>}
                  </span>
                  <span className="rel-adopt">
                    <span className="rel-adopt-num"><span><b className="tnum">{num(r.installs)}</b> {w.many}</span><em className="tnum">{pct(r.share, 1)}</em></span>
                    <span className="rel-meter"><motion.i initial={{ scaleX: 0 }} animate={{ scaleX: r.share || 0 }} transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }} /></span>
                    {r.update_failed > 0 && <span className="rel-failed">{r.update_failed} failed to update</span>}
                  </span>
                  {canOpen && <Icon name={isOpen ? "chevronUp" : "chevronDown"} size={16} className="rel-caret" />}
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && canOpen && (
                    <motion.div className="rel-body" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>
                      <div className="rel-sections">
                        {r.sections.map((s) => (
                          <div key={s.title}>
                            <h4 className="t-h3">{s.title}</h4>
                            <ul>{s.items.map((it) => <li key={it}>{it}</li>)}</ul>
                          </div>
                        ))}
                      </div>
                      {r.data_safety && <p className="rel-safety">{r.data_safety}</p>}
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
