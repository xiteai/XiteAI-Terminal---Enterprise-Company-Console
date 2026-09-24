import { motion } from "../../lib/motion.js";
import { cx } from "../../lib/cx.js";
import Icon from "../../components/Icon.jsx";
import { SECTIONS, STEPS } from "./steps.js";

// Where you are in joining: the six parts, each done, current or ahead.
// Finished parts can be reopened with a click. On a phone it folds into a
// single line with a segmented bar.
const questions = SECTIONS.map((_, s) => STEPS.map((st, i) => ({ st, i })).filter(({ st }) => st.section === s && st.kind !== "intro"));

export default function StepRail({ index, onJump }) {
  const step = STEPS[index];
  const current = step.kind === "intro" ? -1 : step.section;
  const posIn = (s) => questions[s].findIndex(({ i }) => i === index);

  return (
    <>
      <aside className="rail" aria-label="Your progress">
        <div className="rail-head">
          <b>Join XiteAI</b>
          <span>About 4 minutes · saved as you go</span>
        </div>
        <ol className="rail-list">
          {SECTIONS.map((name, s) => {
            const state = s < current ? "done" : s === current ? "current" : "next";
            const n = questions[s].length;
            const sub = state === "done" ? "Done" : state === "current"
              ? (n > 1 ? `Question ${posIn(s) + 1} of ${n}` : s === SECTIONS.length - 1 ? "Last step" : "1 question")
              : s === SECTIONS.length - 1 ? "Check and send" : `${n} ${n === 1 ? "question" : "questions"}`;
            const clickable = state === "done";
            return (
              <li key={name} className={cx("rail-item", state)}>
                <button type="button" disabled={!clickable} onClick={() => clickable && onJump(questions[s][0].i)}
                  aria-current={state === "current" ? "step" : undefined}>
                  <span className="rail-dot">{state === "done" ? <Icon name="check" size={13} stroke={2.4} /> : s + 1}</span>
                  <span className="rail-text">
                    <b>{name}</b>
                    <small>{sub}</small>
                  </span>
                </button>
                {state === "current" && n > 1 && (
                  <span className="rail-bar"><motion.i animate={{ scaleX: (posIn(s) + 1) / n }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }} /></span>
                )}
              </li>
            );
          })}
        </ol>
      </aside>

      <div className="rail-mobile" aria-hidden>
        <span>{current < 0 ? "Before you start" : `Part ${current + 1} of ${SECTIONS.length} · ${SECTIONS[current]}`}</span>
        <span className="rail-segs">
          {SECTIONS.map((name, s) => <i key={name} className={cx(s < current && "done", s === current && "current")} />)}
        </span>
      </div>
    </>
  );
}
