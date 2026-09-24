import { motion } from "../../lib/motion.js";

// The question, then one line of context. It fades in as a whole: calm and
// quick, so the next answer is never waiting on an animation.
export default function Question({ text, sub }) {
  return (
    <div className="jq">
      <motion.h1 className="jq-hero" key={text} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
        {text}
      </motion.h1>
      {sub && (
        <motion.p className="jq-sub" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.08, duration: 0.3 }}>
          {sub}
        </motion.p>
      )}
    </div>
  );
}
