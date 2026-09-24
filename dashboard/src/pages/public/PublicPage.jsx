import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { ago } from "../../lib/format.js";
import { useData } from "../../lib/useData.js";
import ProductLogo from "../../components/ProductLogo.jsx";
import EntryNav from "../shared/EntryNav.jsx";
import DataPromise from "./DataPromise.jsx";
import HelpForm from "./HelpForm.jsx";
import PublicFooter from "./PublicFooter.jsx";
import TrackRequest from "./TrackRequest.jsx";
import WhatsNew from "./WhatsNew.jsx";
import "../shared/Entry.css";
import "./PublicPage.css";

const XOS1 = { name: "XOS1", logo: "xos1-mark.png", logo_invert: true };
const rise = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } };

// The customer page: no sign-in. The latest version, what changed, a line to
// the people who build it, and exactly what leaves your computer.
export default function PublicPage() {
  const status = useData(() => api.get("/api/public/status"), []);
  const releases = useData(() => api.get("/api/public/releases"), []);
  useEffect(() => { document.title = "XOS1 · Status and support"; }, []);
  const s = status.data;
  const ok = s?.state === "operational";

  return (
    <div className="entry pub">
      <EntryNav
        sub="XOS1"
        links={[{ href: "#new", label: "What's new" }, { href: "#help", label: "Support" }, { href: "#data", label: "Privacy" }]}
        cta={<>
          <Link to="/login" className="plain">Team sign in</Link>
          {s?.download_url && <a className="ink" href={s.download_url} target="_blank" rel="noreferrer">Download</a>}
        </>}
      />

      <section className="pub-hero">
        <motion.div {...rise}><ProductLogo product={XOS1} size={56} /></motion.div>
        <motion.h1 className="t-display pub-title" {...rise} transition={{ ...rise.transition, delay: 0.05 }}>
          {s?.product_full || "XiteAI OS1"}
        </motion.h1>
        <motion.p className="t-lede pub-lede" {...rise} transition={{ ...rise.transition, delay: 0.1 }}>
          Release notes, support, and exactly what leaves your computer.
        </motion.p>
        <motion.div className="pub-cta" {...rise} transition={{ ...rise.transition, delay: 0.15 }}>
          {s?.download_url && <a className="pub-download" href={s.download_url} target="_blank" rel="noreferrer">Download XOS1</a>}
          <a className="pub-secondary" href="#help">Get support</a>
        </motion.div>
        <motion.p className="pub-meta" {...rise} transition={{ ...rise.transition, delay: 0.2 }}>
          {status.error
            ? <span className="pub-meta-bad">Service status unavailable</span>
            : s && <>Version {s.latest?.version}<i />Windows 10 and later<i />{ok ? "Service normal" : "Service degraded"}, checked {ago(s.checked_at)}</>}
        </motion.p>
      </section>

      <main className="pub-main">
        <WhatsNew releases={releases.data?.releases || []} />
        <section className="pub-sec pub-help" id="help">
          <div className="pub-help-copy">
            <h2 className="t-h1">Support</h2>
            <p className="t-lede">
              A small team in Noida. Every request reaches a person. If XOS1 touched your files in a way it shouldn't
              have, say so and it goes to the top.
            </p>
            <TrackRequest />
          </div>
          <HelpForm />
        </section>
        <DataPromise />
      </main>
      <PublicFooter company={s?.company} />
    </div>
  );
}
