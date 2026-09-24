import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import { cx } from "../lib/cx.js";
import Icon from "./Icon.jsx";
import { Portal, useOverlay } from "./Overlay.jsx";
import "./Modal.css";

export default function Modal({ open, onClose, title, subtitle, children, footer, width = 460, tone }) {
  const panel = useOverlay(open, onClose);
  return (
    <Portal>
      <AnimatePresence>
        {open && (
          <motion.div
            className="modal-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
          >
            <motion.div
              ref={panel}
              tabIndex={-1}
              role="dialog"
              aria-modal="true"
              aria-label={typeof title === "string" ? title : undefined}
              className={cx("modal", tone && `modal-${tone}`)}
              style={{ width: `min(${width}px, calc(100vw - 32px))` }}
              initial={{ opacity: 0, y: 14, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.985 }}
              transition={{ type: "spring", stiffness: 420, damping: 34, mass: 0.8 }}
            >
              <header className="modal-head">
                <div>
                  <h2 className="modal-title">{title}</h2>
                  {subtitle && <p className="modal-sub">{subtitle}</p>}
                </div>
                <button className="modal-x" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
              </header>
              <div className="modal-body">{children}</div>
              {footer && <footer className="modal-foot">{footer}</footer>}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </Portal>
  );
}
