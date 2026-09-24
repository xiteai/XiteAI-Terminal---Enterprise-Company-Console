import { useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import "./Popover.css";

// A small floating panel anchored to its trigger (menus, the bell). Closes on
// outside click and Escape.
export default function Popover({ open, onClose, children, align = "right", up = false, width = 340, className = "" }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.parentElement.contains(e.target)) onClose(); };
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={ref}
          className={`popover popover-${align} ${up ? "popover-up" : ""} ${className}`}
          style={{ width }}
          initial={{ opacity: 0, y: up ? 6 : -6, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: up ? 4 : -4, scale: 0.98, transition: { duration: 0.14 } }}
          transition={{ type: "spring", stiffness: 520, damping: 38 }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
