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
