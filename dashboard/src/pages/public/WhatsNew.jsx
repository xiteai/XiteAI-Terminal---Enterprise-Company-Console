import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";

function Sections({ release }) {
  return (
    <div className="pub-sections">
      {release.sections.map((s) => (
        <div className="pub-section" key={s.title}>
          <h3 className="t-h3">{s.title}</h3>
          <ul>{s.items.map((it) => <li key={it}>{it}</li>)}</ul>
        </div>
      ))}
    </div>
  );
}

// The changelog, from the same notes the app's update notice shows.
export default function WhatsNew({ releases }) {
  const [open, setOpen] = useState(null);
  const withNotes = releases.filter((r) => r.sections?.length);
  if (!withNotes.length) return null;
  const [latest, ...older] = withNotes;
  return (
    <section className="pub-sec" id="new">
      <div className="pub-sec-head">
        <span className="eyebrow">What's new in {latest.version}</span>
        <h2 className="t-h1">{latest.headline || `Version ${latest.version}`}</h2>
        {latest.notes && <p className="t-lede">{latest.notes}</p>}
      </div>
      <Sections release={latest} />
      {latest.data_safety && <p className="pub-safety">{latest.data_safety}</p>}
      {older.length > 0 && (
        <div className="pub-older">
          <span className="eyebrow">Earlier versions</span>
          {older.map((r) => {
            const isOpen = open === r.version;
            return (
              <div key={r.version} className="pub-older-item">
                <button onClick={() => setOpen(isOpen ? null : r.version)} aria-expanded={isOpen}>
                  <span className="mono pub-older-v">{r.version}</span>
                  <span className="pub-older-h">{r.headline}</span>
                  <span className="pub-older-more">{isOpen ? "Hide" : "Read notes"}</span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }} style={{ overflow: "hidden" }}>
                      <Sections release={r} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
