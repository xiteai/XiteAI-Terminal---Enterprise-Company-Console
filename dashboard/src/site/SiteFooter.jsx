import { Link } from "react-router-dom";
import Logo from "./Logo.jsx";
import { site, published } from "./content.js";
import "./site.css";

/* The footer, carried over from the ELLA OS site (website1
   components/chrome/Footer). Column model and every measurement kept; what
   changed is where a few links point, because this app does not serve
   /features/ or /contact/ — those live on the marketing site and are linked
   absolutely. A footer linking to a page that does not exist is the most
   common broken thing on a marketing site, and the old XiteAI site had the
   footer copied into all 31 pages, which is why it drifted. One component. */

const columns = [
  {
    title: "Product",
    links: [
      { href: `${site.web}/`, label: "Overview" },
      { href: `${site.web}/features/`, label: "What she does" },
      { to: "/legal/privacy", label: "Where data goes" },
      { href: "/download", label: "Download" },
    ],
  },
  {
    title: "Company",
    links: [
      { to: "/careers", label: "Careers" },
      { href: `${site.web}/contact/`, label: "Contact" },
      { href: `mailto:${site.contact.security}`, label: "Report a vulnerability" },
    ],
  },
];

function Item({ l }) {
  return l.to
    ? <Link to={l.to} className="ft-link">{l.label}</Link>
    : <a href={l.href} className="ft-link">{l.label}</a>;
}

export default function SiteFooter({ meta }) {
  return (
    <footer className="ft">
      <div className="ft-grid">
        <div>
          {/* The COMPANY mark here, not the product's. The page opens as the
              Terminal and closes as the company that runs it. */}
          <div className="ft-brand">
            <Logo variant="xiteai" size={22} className="ft-mark" />
            <span className="ft-company">{site.company}</span>
          </div>
          <p className="ft-tag">
            She remembers you.
            <br />
            On your machine, not ours.
          </p>
        </div>

        {columns.map((col) => (
          <nav key={col.title}>
            <p className="ft-head">{col.title}</p>
            <ul className="ft-list">
              {col.links.map((l) => <li key={l.label}><Item l={l} /></li>)}
            </ul>
          </nav>
        ))}

        <nav>
          <p className="ft-head">Legal</p>
          <ul className="ft-list">
            {/* Only what is actually published. */}
            {published.map((d) => (
              <li key={d.slug}>
                <Link to={`/legal/${d.slug}`} className="ft-link">{d.title}</Link>
              </li>
            ))}
            <li><Link to="/legal" className="ft-link">All policies →</Link></li>
          </ul>
        </nav>
      </div>

      <div className="ft-base">
        <div className="ft-base-in">
          <span>
            © {new Date().getFullYear()} {site.company}. All rights reserved.
            {/* The customer panel passes the build it is reporting on. Nothing
                else does, so the footer is otherwise identical everywhere. */}
            {meta && <> · {meta}</>}
          </span>
          <span className="ft-base-links">
            <Link to="/legal" className="ft-link">Legal</Link>
            <Link to="/legal/privacy" className="ft-link">Privacy</Link>
            <a href={`mailto:${site.contact.general}`} className="ft-link">Contact</a>
          </span>
        </div>
      </div>
    </footer>
  );
}
