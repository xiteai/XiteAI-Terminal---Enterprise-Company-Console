import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import Button from "../../components/Button.jsx";
import Field from "../../components/Field.jsx";
import Icon from "../../components/Icon.jsx";
import "./LoginPage.css";

// Two halves: what this is on the left, the way in on the right.
//
// The old page was a form floating in white space, which reads as unfinished
// rather than restrained. The panel gives the form something to sit against
// and somewhere to say what the Terminal is, without a word of marketing.
const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.08 } } };
const rise = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

// Quiet geometry, drawn on a grid — the same hairline language as the rest of
// the console, not a stock illustration.
function PanelArt() {
  return (
    <svg className="lg-art" viewBox="0 0 400 400" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="lgfade" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.14" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <circle cx="200" cy="200" r="150" stroke="#fff" strokeOpacity="0.10" />
      <circle cx="200" cy="200" r="110" stroke="#fff" strokeOpacity="0.12" />
      <circle cx="200" cy="200" r="70" stroke="#fff" strokeOpacity="0.16" />
      <circle cx="200" cy="200" r="150" fill="url(#lgfade)" />
      <path d="M50 200h300M200 50v300" stroke="#fff" strokeOpacity="0.07" />
      <circle cx="200" cy="130" r="5" fill="#fff" fillOpacity="0.5" />
      <circle cx="270" cy="200" r="3.5" fill="#fff" fillOpacity="0.32" />
      <circle cx="200" cy="270" r="3.5" fill="#fff" fillOpacity="0.32" />
      <circle cx="130" cy="200" r="3.5" fill="#fff" fillOpacity="0.32" />
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [domain, setDomain] = useState("xos1.com");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needCode, setNeedCode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const codeRef = useRef(null);

  useEffect(() => {
    document.title = "Sign in · XiteAI Terminal";
    api.get("/api/join/options").then((o) => setDomain(o.domain)).catch(() => {});
  }, []);
  useEffect(() => { if (needCode) codeRef.current?.focus(); }, [needCode]);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) { setError("Enter your work email and password."); return; }
    setBusy(true);
    setError("");
    try {
      await api.post("/api/auth/login", { email: email.trim(), password, code });
      navigate("/console", { replace: true });
    } catch (err) {
      if (err.needCode) setNeedCode(true);
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="lg">
      <motion.aside className="lg-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}>
        <PanelArt />
        <div className="lg-panel-in">
          <img className="lg-mark" src="/brand/xiteai.png" alt="" />
          <div className="lg-panel-words">
            <h2>The company, in one place.</h2>
            <p>People, products, code and pay — behind one sign-in, with every action on the record.</p>
          </div>
          <span className="lg-panel-foot">XiteAI Technologies</span>
        </div>
      </motion.aside>

      <main className="lg-side">
        <motion.form className="lg-form" onSubmit={submit} noValidate
          variants={stagger} initial="hidden" animate="show">
          <motion.div className="lg-head" variants={rise}>
            <h1 className="t-h1">Sign in</h1>
            <p>XiteAI Terminal, for the team.</p>
          </motion.div>

          <motion.div variants={rise}>
            <Field label="Work email" autoComplete="username" placeholder="yourname" autoFocus
              suffix={email.includes("@") ? null : `@${domain}`} value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </motion.div>

          <motion.div variants={rise}>
            <Field label="Password" type="password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </motion.div>

          <AnimatePresence>
            {needCode && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}>
                <Field ref={codeRef} label="Code from your authenticator app" inputMode="numeric"
                  autoComplete="one-time-code" maxLength={6} placeholder="6 digits" value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {error && (
              <motion.p className="lg-error" role="alert"
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <Icon name="alert" size={15} /> {error}
              </motion.p>
            )}
          </AnimatePresence>

          <motion.div variants={rise}>
            <Button type="submit" variant="primary" size="lg" block busy={busy}>Sign in</Button>
          </motion.div>

          <motion.p className="lg-foot" variants={rise}>
            New to the team? <Link to="/join" className="text-link">Ask to join</Link>
          </motion.p>
        </motion.form>

        <p className="lg-note">Every sign-in is recorded in the audit log.</p>
        <Link to="/" className="lg-back">← XiteAI</Link>
      </main>
    </div>
  );
}
