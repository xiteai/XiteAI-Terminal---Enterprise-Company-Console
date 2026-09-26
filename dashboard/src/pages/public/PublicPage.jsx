import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { useData } from "../../lib/useData.js";
import ProductLogo from "../../components/ProductLogo.jsx";
import EntryNav from "../shared/EntryNav.jsx";
import HelpForm from "./HelpForm.jsx";
import PublicFooter from "./PublicFooter.jsx";
import TrackRequest from "./TrackRequest.jsx";
import "../shared/Entry.css";
import "./PublicPage.css";

const XOS1 = { name: "XOS1", logo: "xos1-mark.png", logo_invert: true };
const rise = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } };

// The company page: who we are, what to download, how to reach support, and
// the door in to the team we're building. No version history, no data
// ledger — that noise lives elsewhere; this is the one page.
export default function PublicPage() {
  const status = useData(() => api.get("/api/public/status"), []);
  useEffect(() => { document.title = "XiteAI"; }, []);
  const s = status.data;

  return (
    <div className="entry pub">
      <EntryNav
        sub=""
        links={[{ to: "/careers", label: "Careers" }, { href: "#help", label: "Support" }]}
        cta={<>
          <Link to="/login" className="plain">Team sign in</Link>
          <a className="ink" href="/download">Download</a>
        </>}
      />

      <section className="pub-hero">
        <motion.div {...rise}><ProductLogo product={XOS1} size={56} /></motion.div>
        <motion.h1 className="t-display pub-title" {...rise} transition={{ ...rise.transition, delay: 0.05 }}>
          {s?.company || "XiteAI"}
        </motion.h1>
        <motion.p className="t-lede pub-lede" {...rise} transition={{ ...rise.transition, delay: 0.1 }}>
          We build {s?.product_full || "XOS1"} — the AI layer for your PC. On your machine, not ours.
        </motion.p>
        <motion.div className="pub-cta" {...rise} transition={{ ...rise.transition, delay: 0.15 }}>
          <a className="pub-download" href="/download">Download XOS1</a>
          <a className="pub-secondary" href="#help">Get support</a>
        </motion.div>
      </section>

      <main className="pub-main">
        <motion.section className="pub-careers-cta" {...rise} transition={{ ...rise.transition, delay: 0.2 }}>
          <div>
            <span className="eyebrow">We're hiring</span>
            <h2 className="t-h1">Build XiteAI with us</h2>
            <p className="t-lede">Open roles across engineering, design and the rest of the company.</p>
          </div>
          <Link to="/careers" className="pub-careers-go">
            Explore careers
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 10h12M11.5 5.5 16 10l-4.5 4.5" />
            </svg>
          </Link>
        </motion.section>

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
      </main>
      <PublicFooter company={s?.company} checkedAt={s?.checked_at} version={s?.latest?.version} />
    </div>
  );
}
