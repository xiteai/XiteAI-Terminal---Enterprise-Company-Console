// The live bar while a repository copies from GitHub: a percentage once git
// reports one (the bulk of a clone — "Receiving objects: 43%"), an animated
// sweep before that (still working, just no number yet), and an elapsed
// timer throughout, so a big repository never looks stuck.
const mmss = (s) => {
  const total = Math.max(0, Math.round(s || 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

const PHASES = {
  "Cloning into": "Starting…",
  "Enumerating objects": "Listing what's there…",
  "Counting objects": "Counting objects…",
  "Compressing objects": "Compressing…",
  "Receiving objects": "Downloading…",
  "Resolving deltas": "Putting it together…",
  "Updating files": "Writing files…",
};

function label(progress) {
  if (!progress?.phase) return "Starting…";
  const known = Object.keys(PHASES).find((k) => progress.phase.startsWith(k));
  return known ? PHASES[known] : progress.phase;
}

export default function CloneProgress({ progress, compact = false }) {
  const pct = progress?.pct;
  return (
    <div className={`rp-progress${compact ? " rp-progress-sm" : ""}`}>
      <div className="rp-progress-head">
        <span>{label(progress)}</span>
        <span className="tnum faint">{typeof pct === "number" ? `${pct}%` : ""} {mmss(progress?.elapsed_s)}</span>
      </div>
      <div className="rp-progress-track">
        {typeof pct === "number" ? (
          <div className="rp-progress-fill" style={{ width: `${Math.min(100, Math.max(2, pct))}%` }} />
        ) : (
          <div className="rp-progress-sweep" />
        )}
      </div>
    </div>
  );
}
