import { Link } from "react-router-dom";
import Wordmark from "../../components/Wordmark.jsx";

export default function PublicFooter({ company = "XiteAI Technologies" }) {
  return (
    <footer className="entry-foot">
      <div className="pub-foot">
        <div>
          <Wordmark sub="" />
          <p className="t-note pub-foot-line">XOS1 remembers you. On your machine, not ours.</p>
        </div>
        <div>
          <span className="pub-foot-h">XOS1</span>
          <a href="#new">What's new</a>
          <a href="#help">Support</a>
          <a href="#data">Privacy</a>
        </div>
        <div>
          <span className="pub-foot-h">The team</span>
          <Link to="/login">Sign in</Link>
          <Link to="/join">Join XiteAI</Link>
        </div>
      </div>
      <div className="entry-foot-in"><span>© {new Date().getFullYear()} {company}. All rights reserved.</span><span>XiteAI OS1</span></div>
    </footer>
  );
}
