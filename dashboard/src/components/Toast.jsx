import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import Icon from "./Icon.jsx";
import { Portal } from "./Overlay.jsx";
import "./Toast.css";

const ToastContext = createContext(() => {});
let seq = 0;

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const dismiss = useCallback((id) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const push = useCallback((message, { tone = "good", ms = 3600 } = {}) => {
    const id = ++seq;
    setItems((xs) => [...xs.slice(-3), { id, message, tone }]);
    setTimeout(() => dismiss(id), ms);
  }, [dismiss]);
  const toast = useMemo(() => Object.assign(push, {
    error: (m) => push(m, { tone: "bad", ms: 5200 }),
    info: (m) => push(m, { tone: "info" }),
  }), [push]);
  return (
    <ToastContext.Provider value={toast}>
      {children}
      <Portal>
        <div className="toasts" role="status" aria-live="polite">
          <AnimatePresence initial={false}>
            {items.map((t) => (
              <motion.div
                key={t.id}
                layout
                className={`toast toast-${t.tone}`}
                initial={{ opacity: 0, y: 16, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.97, transition: { duration: 0.18 } }}
                transition={{ type: "spring", stiffness: 480, damping: 36 }}
              >
                <Icon name={t.tone === "bad" ? "alert" : t.tone === "info" ? "info" : "circleCheck"} size={16} />
                <span>{t.message}</span>
                <button onClick={() => dismiss(t.id)} aria-label="Dismiss"><Icon name="x" size={14} /></button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </Portal>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
