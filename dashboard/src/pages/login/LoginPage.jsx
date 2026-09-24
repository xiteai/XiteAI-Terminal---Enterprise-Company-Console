import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import Button from "../../components/Button.jsx";
import Field from "../../components/Field.jsx";
import Icon from "../../components/Icon.jsx";
import EntryNav from "../shared/EntryNav.jsx";
import "./LoginPage.css";

// One card, centred: the mark, two fields, one button.
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
    <div className="entry login-page">
      <EntryNav cta={<Link to="/" className="plain">XOS1 status and support</Link>} />
      <main className="login-wrap">
        <motion.form className="login-card" onSubmit={submit} noValidate
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
          <img className="login-logo" src="/brand/xiteai.png" alt="XiteAI" />
          <div className="login-head">
            <h1 className="t-h1">Sign in</h1>
            <p>XiteAI Terminal, for the team.</p>
          </div>
          <Field label="Work email" autoComplete="username" placeholder="yourname" autoFocus
            suffix={email.includes("@") ? null : `@${domain}`} value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <AnimatePresence>
            {needCode && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                <Field ref={codeRef} label="Code from your authenticator app" inputMode="numeric" autoComplete="one-time-code"
                  maxLength={6} placeholder="6 digits" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              </motion.div>
            )}
          </AnimatePresence>
          {error && <p className="login-error" role="alert"><Icon name="alert" size={15} /> {error}</p>}
          <Button type="submit" variant="primary" size="lg" block busy={busy}>Sign in</Button>
          <p className="login-foot">New to the team? <Link to="/join" className="text-link">Ask to join</Link></p>
        </motion.form>
        <p className="login-note">Every sign-in is recorded in the audit log.</p>
      </main>
    </div>
  );
}
