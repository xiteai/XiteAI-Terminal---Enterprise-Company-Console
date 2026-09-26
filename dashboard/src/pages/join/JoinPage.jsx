import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { motion } from "../../lib/motion.js";
import { api } from "../../lib/api.js";
import { useDebounced } from "../../lib/useData.js";
import Button from "../../components/Button.jsx";
import Icon from "../../components/Icon.jsx";
import EntryNav from "../shared/EntryNav.jsx";
import ChoiceList from "./ChoiceList.jsx";
import PhotoCapture from "./PhotoCapture.jsx";
import PillInput from "./PillInput.jsx";
import Question from "./Question.jsx";
import Review from "./Review.jsx";
import Sent from "./Sent.jsx";
import StepRail from "./StepRail.jsx";
import { passwordRules, questionText, STEP_OF_FIELD, STEPS } from "./steps.js";
import { useDraft } from "./useDraft.js";
import "../shared/Entry.css";
import "./JoinPage.css";

const slide = {
  enter: (dir) => ({ opacity: 0, y: dir > 0 ? 18 : -18 }),
  center: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
  exit: (dir) => ({ opacity: 0, y: dir > 0 ? -12 : 12, transition: { duration: 0.18 } }),
};

function useEmailCheck(local, active) {
  const [state, setState] = useState({ status: "idle" });
  const debounced = useDebounced(local, 350);
  useEffect(() => {
    if (!active || !debounced || !/^[a-z0-9](?:[a-z0-9._-]{0,30}[a-z0-9])?$/.test(debounced)) {
      setState({ status: "idle" });
      return undefined;
    }
    let alive = true;
    setState({ status: "checking" });
    api.post("/api/join/check-email", { local: debounced })
      .then((r) => alive && setState({ status: r.available ? "free" : "taken", email: r.email }))
      .catch(() => alive && setState({ status: "idle" }));
    return () => { alive = false; };
  }, [debounced, active]);
  return state;
}

export default function JoinPage() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState(null);
  const [answers, setAnswers, clearDraft] = useDraft();
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(1);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const firstInput = useRef(null);

  const step = STEPS[index];
  const email = useEmailCheck(answers.local, step.special === "email");

  useEffect(() => {
    document.title = "Join the team · XiteAI";
    api.get("/api/join/options").then(setMeta).catch(() => setMeta({ levels: [], departments: [] }));
  }, []);
  useEffect(() => {
    const t = setTimeout(() => firstInput.current?.focus({ preventScroll: true }), 380);
    return () => clearTimeout(t);
  }, [index]);

  const set = useCallback((patch) => {
    setAnswers((a) => ({ ...a, ...patch }));
    setErrors((e) => {
      const next = { ...e };
      Object.keys(patch).forEach((k) => delete next[k]);
      delete next.agree;
      return next;
    });
  }, [setAnswers]);

  const go = useCallback((to) => {
    if (to < 0 || to >= STEPS.length) return;
    setDir(to > index ? 1 : -1);
    setIndex(to);
    setErrors({});
  }, [index]);

  const next = useCallback(() => {
    const problems = step.validate?.(answers, meta);
    if (problems) { setErrors(problems); return; }
    if (step.special === "email" && email.status === "taken") {
      setErrors({ local: `${email.email} is taken. Try another.` });
      return;
    }
    go(index + 1);
  }, [step, answers, meta, email, go, index]);

  const submit = async () => {
    const problems = step.validate?.(answers, meta);
    if (problems) { setErrors(problems); return; }
    setBusy(true);
    try {
      const body = Object.fromEntries(
        ["local", "password", "full_name", "preferred_name", "level", "title", "department", "employment_type",
          "start_date", "photo", "dob", "gender", "phone", "personal_email", "city", "address", "emergency_name",
          "emergency_relation", "emergency_phone", "qualification", "institution", "graduation_year",
          "experience_years", "previous_company", "skills", "linkedin", "portfolio", "about"]
          .map((k) => [k, (answers[k] || "").toString()]),
      );
      await api.post("/api/join", { ...body, agree_accurate: true, agree_storage: true });
      clearDraft();
      setSent(true);
    } catch (err) {
      setBusy(false);
      if (err.field && STEP_OF_FIELD[err.field] !== undefined) {
        setDir(-1);
        setIndex(STEP_OF_FIELD[err.field]);
        setErrors({ [err.field]: err.message });
      } else {
        setErrors({ agree: err.message });
      }
    }
  };

  const pick = (key, value) => {
    set({ [key]: value });
    setTimeout(() => { setDir(1); setIndex((i) => Math.min(i + 1, STEPS.length - 1)); }, 240);
  };

  const q = questionText(step, answers);
  const levelLabel = meta?.levels?.find((l) => l.key === answers.level)?.label;

  const body = useMemo(() => {
    if (step.kind === "intro") return null;
    if (step.kind === "review") {
      return <Review answers={answers} meta={meta} set={set} onJump={go} error={errors.agree} />;
    }
    if (step.kind === "choice") {
      return (
        <>
          <ChoiceList options={step.options(meta, answers)} value={answers[step.key]} onPick={(v) => pick(step.key, v)} dense={step.dense} />
          {errors[step.key] && <p className="pill-note" role="alert">{errors[step.key]}</p>}
        </>
      );
    }
    if (step.kind === "photo") {
      return <PhotoCapture value={answers.photo} onChange={(v) => set({ photo: v })} error={errors.photo} />;
    }
    const suggestions = step.suggest?.(meta, answers) || [];
    return (
      <div className={step.fields.length > 1 ? "jfields" : "jfield-one"}>
        {step.fields.map((f, i) => (
          <div key={f.key} className="jfield">
            <PillInput
              ref={i === 0 ? firstInput : undefined}
              label={f.label}
              value={answers[f.key]}
              onChange={(v) => set({ [f.key]: v })}
              onEnter={i === step.fields.length - 1 ? next : () => {
                const inputs = document.querySelectorAll(".jfields .pill-input");
                inputs[i + 1]?.focus();
              }}
              placeholder={f.placeholder}
              type={f.type}
              inputMode={f.inputMode}
              autoComplete={f.autoComplete}
              suffix={f.suffix === "@domain" ? `@${meta?.domain || "xos1.com"}` : f.suffix}
              textarea={f.textarea}
              lower={f.lower}
              error={errors[f.key]}
            />
            {f.chips && meta?.[f.chips] && (
              <div className="jchips">
                {meta[f.chips].map((c) => (
                  <button key={c} type="button" className={answers[f.key] === c ? "on" : ""} onClick={() => set({ [f.key]: c })}>{c}</button>
                ))}
              </div>
            )}
          </div>
        ))}
        {suggestions.length > 0 && (
          <div className="jchips">
            {suggestions.map((s) => (
              <button key={s} type="button" className={answers.title === s ? "on" : ""} onClick={() => set({ title: s })}>{s}</button>
            ))}
          </div>
        )}
        {step.special === "email" && (
          <p className={`jstatus jstatus-${email.status}`} aria-live="polite">
            {email.status === "checking" && "Checking…"}
            {email.status === "free" && <><Icon name="check" size={14} /> {email.email} is yours if you want it.</>}
            {email.status === "taken" && <><Icon name="x" size={14} /> {email.email} is taken.</>}
          </p>
        )}
        {step.special === "password" && (
          <ul className="jrules">
            {passwordRules(answers.password).map((r) => (
              <li key={r.text} className={r.ok ? "ok" : ""}><Icon name={r.ok ? "check" : "x"} size={13} /> {r.text}</li>
            ))}
          </ul>
        )}
      </div>
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, answers, meta, errors, email, next]);

  if (sent) {
    return (
      <div className="entry join">
        <EntryNav />
        <main className="join-sent-wrap">
          <Sent
            name={(answers.preferred_name || answers.full_name || "").trim().split(/\s+/)[0]}
            levelLabel={levelLabel}
            onContinue={() => navigate("/console", { replace: true })}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="entry join">
      <EntryNav cta={<Link to="/login" className="plain">Already on the team? Sign in</Link>} />

      <main className="join-stage">
        <StepRail index={index} onJump={go} />
        <div className="join-card">
          <AnimatePresence mode="wait" custom={dir} initial={false}>
            <motion.div key={step.id} custom={dir} variants={slide} initial="enter" animate="center" exit="exit" className="join-step">
              <Question text={q} sub={step.sub} />
              {body && <div className="join-body">{body}</div>}
              <div className="join-actions">
                {index > 0 && (
                  <Button variant="quiet" icon="arrowLeft" onClick={() => go(index - 1)}>Back</Button>
                )}
                <span className="join-spacer" />
                {step.kind === "intro" && (
                  <Button variant="primary" size="lg" iconRight="arrowRight" onClick={() => go(1)}>Let's begin</Button>
                )}
                {step.optional && step.kind !== "intro" && (
                  <Button variant="quiet" onClick={() => go(index + 1)}>Skip</Button>
                )}
                {step.kind !== "intro" && step.kind !== "review" && step.kind !== "choice" && (
                  <Button variant="primary" iconRight="arrowRight" onClick={next}>Continue</Button>
                )}
                {step.kind === "choice" && answers[step.key] && (
                  <Button variant="primary" iconRight="arrowRight" onClick={next}>Continue</Button>
                )}
                {step.kind === "review" && (
                  <Button variant="primary" size="lg" busy={busy} onClick={submit}>Send my request</Button>
                )}
              </div>
              {step.kind === "fields" && <p className="join-hint">Press <kbd>Enter</kbd> to continue</p>}
              {step.kind === "choice" && <p className="join-hint">Or press a number key to choose</p>}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
