import { useState } from "react";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { useSession } from "../../lib/session.jsx";
import Button from "../../components/Button.jsx";
import Field from "../../components/Field.jsx";
import Icon from "../../components/Icon.jsx";
import EntryNav from "../../pages/shared/EntryNav.jsx";
import "./Gate.css";

// After someone above you resets your password, you set your own before anything else.
export default function ForcePassword() {
  const { refresh } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/account/password", { current, new: next });
      await refresh();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="entry gate">
      <EntryNav />
      <main className="gate-wrap">
        <motion.form className="gate-card gate-narrow" onSubmit={submit} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <span className="gate-icon"><Icon name="key" size={22} /></span>
          <h1 className="t-h1">Set your own password</h1>
          <p className="gate-sub">Your password was reset. Enter the temporary one you were given, then choose a new one.</p>
          <Field label="Temporary password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          <Field label="New password" type="password" hint="12 or more characters, upper and lower case, and a number." value={next}
            onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          {error && <p className="form-error" role="alert">{error}</p>}
          <Button type="submit" variant="primary" size="lg" block busy={busy}>Save and continue</Button>
        </motion.form>
      </main>
    </div>
  );
}
