import { motion } from "../lib/motion.js";

// Children rise into place one after another when a view opens: short,
// staggered, transform + opacity only (compositor-friendly, no layout work).
export const riseContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.045, delayChildren: 0.02 } },
};
export const riseItem = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export function Reveal({ as = "div", className, children, ...rest }) {
  const M = motion[as];
  return (
    <M className={className} variants={riseContainer} initial="hidden" animate="show" {...rest}>
      {children}
    </M>
  );
}

export function Rise({ as = "div", className, children, ...rest }) {
  const M = motion[as];
  return <M className={className} variants={riseItem} {...rest}>{children}</M>;
}
