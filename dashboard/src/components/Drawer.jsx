import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import Icon from "./Icon.jsx";
import { Portal, useOverlay } from "./Overlay.jsx";
import "./Drawer.css";

// A panel that slides in from the right, for the details of one thing
// (an install, a person) without leaving the list.
export default function Drawer({ open, onClose, title, eyebrow, children, width = 520, actions }) {
  const panel = useOverlay(open, onClose);
  return (
    <Portal>
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className="drawer-scrim"
              onClick={onClose}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22 }}
            />
            <motion.aside
              ref={panel}
              tabIndex={-1}
              role="dialog"
              aria-modal="true"
              aria-label={typeof title === "string" ? title : "Details"}
              className="drawer"
              style={{ width: `min(${width}px, calc(100vw - 16px))` }}
              initial={{ x: "calc(100% + 16px)" }}
              animate={{ x: 0 }}
              exit={{ x: "calc(100% + 16px)" }}
              transition={{ type: "spring", stiffness: 380, damping: 40, mass: 0.9 }}
            >
              <header className="drawer-head">
                <div className="drawer-titles">
                  {eyebrow && <span className="label">{eyebrow}</span>}
                  <h2 className="drawer-title">{title}</h2>
                </div>
                <div className="drawer-actions">
                  {actions}
                  <button className="modal-x" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
                </div>
              </header>
              <div className="drawer-body">{children}</div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </Portal>
  );
}
