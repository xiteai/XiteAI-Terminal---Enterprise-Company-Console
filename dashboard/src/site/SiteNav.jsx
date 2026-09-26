import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Logo from "./Logo.jsx";
import { site } from "./content.js";
import "./site.css";

/* The nav, carried over from the ELLA OS site (website1 components/chrome/Nav)
   so the two halves of xiteai.com are the same object. Two behaviours, and
   they are separate on purpose:

   MATERIALISE is progressive, not a switch. The chrome fades up across the
   first 120px of scroll via --nav-t (0→1), so the bar appears to condense out
   of the page rather than snapping on at a threshold. A binary toggle is the
   thing that reads as "a component with a scrolled state"; a ramp reads as a
   surface.

   RETREAT is directional. Scrolling down is reading, so the bar leaves;
   scrolling up is looking for something, so it returns immediately. It never
   leaves near the top, and never while keyboard focus is inside it.

   Aligned to the content measure: pages are 1180px wide with 28px gutters, so
   their text spans 1124px and so does this. */

/** How far you scroll before the chrome is fully present. */
const RAMP_PX = 120;
/** Half the first screen. The bar never retreats while you are still reading
 *  the opening — a flat threshold pulls it away mid-sentence on a tall hero. */
const keepPx = () => (typeof window === "undefined" ? 110 : window.innerHeight / 2);
/** Ignore jitter smaller than this so a trackpad twitch cannot flip it. */
const DIR_PX = 6;

const DEFAULT_LINKS = [
  { href: `${site.web}/features/`, label: "What she does" },
  { to: "/legal/privacy", label: "Your data" },
  { to: "/legal", label: "Legal" },
  { to: "/careers", label: "Careers" },
];

export default function SiteNav({ links = DEFAULT_LINKS, cta, home = "/" }) {
  const ref = useRef(null);
  const lastY = useRef(0);
  const keep = useRef(220);
  const pinned = useRef(false); // keyboard focus is inside — never retreat
  // Sheen velocity: last y sampled, when, and the timer that zeroes it once
  // the page stops moving (and the scroll frames stop with it).
  const vY = useRef(0);
  const vAt = useRef(0);
  const vIdle = useRef(0);
  const [away, setAway] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;

    // Re-measured on resize: a phone rotating, or desktop chrome appearing,
    // changes what "the first screen" means.
    const measure = () => { keep.current = keepPx(); };
    measure();
    vAt.current = performance.now();

    const read = () => {
      frame = 0;
      const y = Math.max(0, window.scrollY);

      // Progressive presence. Written straight to a custom property rather
      // than through React state: this changes on every frame of every
      // scroll, and re-rendering a component that often to move one number is
      // how a smooth page becomes a janky one.
      el.style.setProperty("--nav-t", String(Math.min(y / RAMP_PX, 1)));

      const dy = y - lastY.current;
      if (Math.abs(dy) > DIR_PX) {
        const down = dy > 0;
        setAway(!reduced && !pinned.current && down && y > keep.current);
        lastY.current = y;
      }
      if (y <= keep.current) setAway(false);

      // The liquid in the glass: a 0..1 charge for how fast the page is
      // sliding under the bar, in px/ms, normalised so a firm flick saturates
      // it. Only ever pushed here — CSS owns the glide home (transition on
      // --nav-v), and the timer below catches the instant scrolling stops.
      // Off under reduced-motion: a highlight that chases the scroll is still
      // motion.
      if (!reduced) {
        const now = performance.now();
        const v = Math.abs(y - vY.current) / Math.max(now - vAt.current, 1);
        vY.current = y;
        vAt.current = now;
        el.style.setProperty("--nav-v", Math.min(v / 3.2, 1).toFixed(3));
        clearTimeout(vIdle.current);
        vIdle.current = window.setTimeout(() => el.style.setProperty("--nav-v", "0"), 110);
      }
    };

    // One read per frame. The listener itself must stay trivial.
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(read); };

    read();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", measure, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", measure);
      if (frame) cancelAnimationFrame(frame);
      clearTimeout(vIdle.current);
    };
  }, []);

  return (
    <header
      ref={ref}
      data-away={away ? "" : undefined}
      onFocusCapture={() => { pinned.current = true; setAway(false); }}
      onBlurCapture={() => { pinned.current = false; }}
      className="nav-shell"
    >
      <nav className="nav-bar">
        <Link to={home} className="nav-brand">
          <Logo variant="xiteai" size={18} className="nav-mark" />
          XiteAI
        </Link>

        <span className="nav-rule" />

        {links.map((l) => (l.href
          ? <a key={l.label} href={l.href} className="nav-link">{l.label}</a>
          : <Link key={l.label} to={l.to} className="nav-link">{l.label}</Link>))}

        <span className="nav-spacer" />
        {cta || <a href="/download" className="nav-cta">Download</a>}
      </nav>
    </header>
  );
}
