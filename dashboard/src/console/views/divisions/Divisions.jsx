import { useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "../../../lib/motion.js";
import { api } from "../../../lib/api.js";
import { useData } from "../../../lib/useData.js";
import Avatar from "../../../components/Avatar.jsx";
import Icon from "../../../components/Icon.jsx";
import PageHeader from "../../../components/PageHeader.jsx";
import DivisionArt from "./DivisionArt.jsx";
import "./Divisions.css";

const grid = { hidden: {}, show: { transition: { staggerChildren: 0.055, delayChildren: 0.05 } } };
const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } },
};

// One division: its scene above, who's in it below. Same card as Quick Links,
// because they're the same kind of thing — a door into a place.
function DivisionCard({ name, members }) {
  const ref = useRef(null);

  const track = (e) => {
    const r = ref.current.getBoundingClientRect();
    ref.current.style.setProperty("--mx", `${e.clientX - r.left}px`);
    ref.current.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <motion.div variants={rise}>
      <Link ref={ref} to={`/console/divisions/${encodeURIComponent(name)}`}
        className="dv-card artcard" onMouseMove={track}>
        <span className="dv-scene">
          <DivisionArt name={name} />
        </span>
        <span className="dv-foot">
          <span className="dv-body">
            <b>{name}</b>
            <span className="dv-count">
              {members.length > 0
                ? `${members.length} ${members.length === 1 ? "person" : "people"}`
                : "Nobody yet"}
            </span>
          </span>
          {members.length > 0 && (
            <span className="dv-stack">
              {members.slice(0, 4).map((m) => (
                <Avatar key={m.id} src={m.avatar_url} initials={m.initials} level={m.level} size={24} />
              ))}
            </span>
          )}
          <Icon name="arrowRight" size={16} className="dv-go" />
        </span>
        <span className="artcard-glow" aria-hidden="true" />
      </Link>
    </motion.div>
  );
}

// Every team's own space, one card each. Chat, uploads and checkpoints for
// that team live inside the room behind the card.
export default function Divisions() {
  const opts = useData(() => api.get("/api/join/options"), []);
  const people = useData(() => api.get("/api/people"), []);
  const names = opts.data?.departments || [];

  const byDept = useMemo(() => {
    const out = {};
    (people.data?.items || []).forEach((p) => { (out[p.department] ||= []).push(p); });
    return out;
  }, [people.data]);

  return (
    <div className="stack">
      <PageHeader title="Divisions" subtitle="Every team's own space." />
      <motion.div className="dv-grid" variants={grid} initial="hidden" animate="show">
        {names.map((name) => <DivisionCard key={name} name={name} members={byDept[name] || []} />)}
      </motion.div>
    </div>
  );
}
