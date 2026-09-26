import { createElement, forwardRef } from "react";
import { motion as framer } from "framer-motion";

// Framer's `motion`, with one fix: fades never blink as they finish.
//
// framer-motion 11 hands opacity to the browser's own animation engine. When
// that animation finishes, Framer cancels it and only writes the end value on
// its next frame, so for one frame the element falls back to its starting
// style: every fade-in ends with a blank flash. Framer keeps animations on
// its own frame loop (no gap) whenever a component has an `onUpdate`, so each
// element here gets an empty one. Import `motion` from this file, not from
// framer-motion; AnimatePresence and the rest still come from framer-motion.
const steady = () => {};
const made = new Map();

export const motion = new Proxy({}, {
  get(_, tag) {
    if (!made.has(tag)) {
      const Base = framer[tag];
      const Steady = forwardRef((props, ref) => createElement(Base, { onUpdate: steady, ...props, ref }));
      Steady.displayName = `motion.${String(tag)}`;
      made.set(tag, Steady);
    }
    return made.get(tag);
  },
});

// The house entrance, in one place.
//
// Nineteen files had grown their own copy of these numbers, which is how a
// page ends up easing differently from the one beside it. New work imports
// these; the older files keep their own timings until someone has a reason to
// touch them, because a sweeping rewrite of all of them would change how
// every page moves to fix nothing anyone can see.
//
// `EASE` is the same curve the CSS uses (--ease), so a thing that animates in
// JS and a thing that animates in CSS arrive together.
export const EASE = [0.16, 1, 0.3, 1];

/** Parent: children arrive one after another, not all at once. */
export const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};

/** Child of `stagger`, or used alone: up and in. */
export const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } },
};

/** For something that should appear when it is scrolled to, once. */
export const whenSeen = {
  variants: rise,
  initial: "hidden",
  whileInView: "show",
  viewport: { once: true, margin: "-60px" },
};
