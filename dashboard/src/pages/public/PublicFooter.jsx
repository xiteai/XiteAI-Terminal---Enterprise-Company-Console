import { Link } from "react-router-dom";
import { ago } from "../../lib/format.js";
import Wordmark from "../../components/Wordmark.jsx";

export default function PublicFooter({ company = "XiteAI Technologies", version, checkedAt }) {
  return (
    <footer className="entry-foot">
      <div className="pub-foot">
        <div>
          <Wordmark sub="" />
          <p className="t-note pub-foot-line">XOS1 remembers you. On your machine, not ours.</p>
        </div>
        <div>
          <span className="pub-foot-h">Company</span>
          <Link to="/careers">Careers</Link>
          <a href="#help">Support</a>
        </div>
        <div>
          <span className="pub-foot-h">The team</span>
          <Link to="/login">Sign in</Link>
          <Link to="/join">Join XiteAI</Link>
        </div>
      </div>
      <div className="entry-foot-in">
        <span>© {new Date().getFullYear()} {company}. All rights reserved.</span>
        <span>{version ? `XOS1 ${version}` : "XiteAI OS1"}{checkedAt ? ` · checked ${ago(checkedAt)}` : ""}</span>
      </div>
    </footer>
  );
}
