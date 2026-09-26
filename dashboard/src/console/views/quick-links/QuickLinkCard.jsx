import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "../../../lib/motion.js";
import QuickLinkArt from "./QuickLinkArt.jsx";

const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } },
};

// One quick link: its scene above, its name below. The card lifts, the scene
// settles, and a soft light follows the cursor across it.
export default function QuickLinkCard({ link }) {
  const ref = useRef(null);

  const track = (e) => {
    const r = ref.current.getBoundingClientRect();
    ref.current.style.setProperty("--mx", `${e.clientX - r.left}px`);
    ref.current.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <motion.div variants={rise}>
      <Link ref={ref} to={link.to} className="qlcard artcard" onMouseMove={track}>
        <span className="qlcard-scene">
          <QuickLinkArt name={link.art} />
        </span>
        <span className="qlcard-foot">
          <span className="qlcard-body">
            <b>{link.label}</b>
            <span>{link.sub}</span>
          </span>
          <svg className="qlcard-go" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </span>
        <span className="artcard-glow" aria-hidden="true" />
      </Link>
    </motion.div>
  );
}
