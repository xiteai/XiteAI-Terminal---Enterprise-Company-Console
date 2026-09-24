import { motion } from "../../lib/motion.js";
import Button from "../../components/Button.jsx";
import Icon from "../../components/Icon.jsx";

// After sending: a clear confirmation, then on to the waiting page.
export default function Sent({ name, levelLabel, onContinue }) {
  return (
    <motion.div className="jsent" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
      <span className="jsent-mark"><Icon name="check" size={24} stroke={2.4} /></span>
      <h1 className="jq-hero">Request sent{name ? `, ${name}` : ""}</h1>
      <p className="jq-sub">
        It's with the Founder and anyone above {levelLabel || "your level"} who can approve new members. You'll get in
        as soon as one of them says yes, and you'll see it happen on the next page.
      </p>
      <Button variant="primary" size="lg" iconRight="arrowRight" onClick={onContinue}>See your request</Button>
    </motion.div>
  );
}
