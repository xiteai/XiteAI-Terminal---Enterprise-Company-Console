import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "../lib/motion.js";
import Icon from "./Icon.jsx";
import { Portal } from "./Overlay.jsx";
import "./UpdateNotice.css";

// A page left open across an update keeps showing the screens it loaded with.
// This compares its own build id with the one the server's page carries now
// (vite.config.js writes both) and, when they differ, offers Reload. It never
// reloads on its own: someone may be halfway through writing something.
// A missing chunk means the same thing, but then the screen can't open at
// all, so that one does reload (at most once a minute).
const MINE = typeof __UI_BUILD__ === "string" ? __UI_BUILD__ : "";
const EVERY_MS = 30_000;
const BUILD_META = /<meta[^>]*name="ui-build"[^>]*content="([^"]+)"/;

async function serverBuild() {
  try {
    const r = await fetch("/", { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) return "";
    const m = (await r.text()).match(BUILD_META);
    return m ? m[1] : "";
  } catch {
    return "";
  }
}

function reloadForMissingChunk(event) {
  let last = 0;
  try { last = Number(sessionStorage.getItem("tc-chunk-reload")) || 0; } catch { /* storage off */ }
  if (Date.now() - last < 60_000) return;
  event.preventDefault();
  try { sessionStorage.setItem("tc-chunk-reload", String(Date.now())); } catch { /* storage off */ }
  window.location.reload();
}

export default function UpdateNotice() {
  const [newer, setNewer] = useState("");
  const [hidden, setHidden] = useState("");
  const busy = useRef(false);

  useEffect(() => {
    if (import.meta.env.DEV || !MINE) return undefined;
    const check = async () => {
      if (busy.current || document.visibilityState !== "visible") return;
      busy.current = true;
      const now = await serverBuild();
      busy.current = false;
      if (now && now !== MINE) setNewer(now);
    };
    const timer = setInterval(check, EVERY_MS);
    document.addEventListener("visibilitychange", check);
    window.addEventListener("focus", check);
    window.addEventListener("vite:preloadError", reloadForMissingChunk);
    check();
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", check);
      window.removeEventListener("focus", check);
      window.removeEventListener("vite:preloadError", reloadForMissingChunk);
    };
  }, []);

  const show = newer && newer !== hidden;
  return (
    <Portal>
      <AnimatePresence>
        {show && (
          <motion.div
            className="update-notice"
            role="status"
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.97, transition: { duration: 0.18 } }}
            transition={{ type: "spring", stiffness: 480, damping: 36 }}
          >
            <span>A newer version of this page is ready.</span>
            <button className="update-reload" onClick={() => window.location.reload()}>Reload</button>
            <button className="update-later" onClick={() => setHidden(newer)} aria-label="Not now">
              <Icon name="x" size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </Portal>
  );
}
