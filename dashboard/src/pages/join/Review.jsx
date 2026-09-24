import Summary from "./Summary.jsx";

function Tick({ checked, onChange, children }) {
  return (
    <label className="jtick">
      <input type="checkbox" checked={Boolean(checked)} onChange={(e) => onChange(e.target.checked)} />
      <span className="jtick-box" aria-hidden />
      <span>{children}</span>
    </label>
  );
}

// The last step: every answer, then two plain promises.
export default function Review({ answers, meta, set, onJump, error }) {
  return (
    <div className="jreview">
      <Summary answers={answers} meta={meta} onJump={onJump} />
      <div className="jreview-ticks">
        <Tick checked={answers.agree_accurate} onChange={(v) => set({ agree_accurate: v })}>
          The details above are accurate.
        </Tick>
        <Tick checked={answers.agree_storage} onChange={(v) => set({ agree_storage: v })}>
          XiteAI may keep these details for employment and HR purposes, seen only by the Founder and the people
          whose role needs them.
        </Tick>
        {error && <p className="pill-note" role="alert">{error}</p>}
      </div>
    </div>
  );
}
