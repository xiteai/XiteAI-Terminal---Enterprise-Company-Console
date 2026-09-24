import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

// Shared behaviour for anything that floats above the page: rendered in a
// portal, closes on Escape, keeps focus inside while open, and hands focus
// back to whatever opened it.
export function useOverlay(open, onClose) {
  const panel = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const before = document.activeElement;
    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose?.(); }
      if (e.key === "Tab" && panel.current) {
        const f = panel.current.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (!f.length) return;
        const first = f[0];
        const last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey, true);
    const t = setTimeout(() => {
      const target = panel.current?.querySelector("[data-autofocus]") || panel.current;
      target?.focus({ preventScroll: true });
    }, 30);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      clearTimeout(t);
      before?.focus?.({ preventScroll: true });
    };
  }, [open, onClose]);
  return panel;
}

export const Portal = ({ children }) => createPortal(children, document.body);
