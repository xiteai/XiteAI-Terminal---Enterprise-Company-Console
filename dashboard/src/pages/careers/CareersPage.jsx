import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { useData } from "../../lib/useData.js";
import Spinner from "../../components/Spinner.jsx";
import SiteFooter from "../../site/SiteFooter.jsx";
import SiteNav from "../../site/SiteNav.jsx";
import "../shared/Entry.css";
import "./Careers.css";

const rise = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } };
const grid = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } } };

function RoleCard({ role }) {
  return (
    <motion.div variants={item}>
      <Link to={`/careers/${role.id}`} className="cr-card">
        <div className="cr-card-top">
          <h3>{role.title}</h3>
          {role.applicant_count && <span className="cr-count">{role.applicant_count}+ applied</span>}
        </div>
        <p className="cr-summary">{role.summary}</p>
        <div className="cr-card-foot">
          <span>{role.employment_type}</span><i />
          <span>{role.location}</span>
          <svg className="cr-go" width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 10h12M11.5 5.5 16 10l-4.5 4.5" />
          </svg>
        </div>
      </Link>
    </motion.div>
  );
}

function Department({ dept }) {
  return (
    <section className="cr-dept">
      <h2 className="t-h2">{dept.department}</h2>
      <motion.div className="cr-grid" variants={grid} initial="hidden" animate="show">
        {dept.roles.map((r) => <RoleCard key={r.id} role={r} />)}
      </motion.div>
    </section>
  );
}

// Only teams with something open — a team with nothing to show says
// nothing, rather than spending a section on saying so.
export default function CareersPage() {
  const board = useData(() => api.get("/api/careers/board"), []);
  useEffect(() => { document.title = "Careers · XiteAI"; }, []);
  const depts = board.data?.departments || [];
  const openCount = depts.reduce((n, d) => n + d.roles.length, 0);

  return (
    <div className="site pub">
      <SiteNav cta={<Link to="/join" className="nav-cta">Already have an offer?</Link>} />

      <section className="cr-hero site-top">
        <motion.span className="eyebrow" {...rise}>Careers</motion.span>
        <motion.h1 className="t-display" {...rise} transition={{ ...rise.transition, delay: 0.05 }}>
          Build XiteAI with us.
        </motion.h1>
        <motion.p className="t-lede cr-lede" {...rise} transition={{ ...rise.transition, delay: 0.1 }}>
          A small team, shipping fast, in Noida and remote. {board.data && (openCount > 0
            ? `${openCount} open role${openCount === 1 ? "" : "s"} across ${depts.length} team${depts.length === 1 ? "" : "s"}.`
            : "Nothing open right now — check back soon.")}
        </motion.p>
      </section>

      <main className="cr-main">
        {board.loading && <div className="cr-wait"><Spinner delay={300} /></div>}
        {depts.map((d) => <Department key={d.department} dept={d} />)}
      </main>
      <SiteFooter />
    </div>
  );
}
