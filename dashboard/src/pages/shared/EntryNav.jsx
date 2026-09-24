import { Link } from "react-router-dom";
import Wordmark from "../../components/Wordmark.jsx";
import "./Entry.css";

// The bar on every page outside the console: the mark, a few quiet links,
// and at most one solid button on the right.
export default function EntryNav({ links = [], cta, sub = "Terminal", home = "/" }) {
  return (
    <header className="en">
      <nav className="en-bar">
        <Link to={home} className="en-brand"><Wordmark sub={sub} inline /></Link>
        <div className="en-links">
          {links.map((l) => (l.href
            ? <a key={l.label} href={l.href} className="en-link">{l.label}</a>
            : <Link key={l.label} to={l.to} className="en-link">{l.label}</Link>))}
        </div>
        {cta && <div className="en-cta">{cta}</div>}
      </nav>
    </header>
  );
}
