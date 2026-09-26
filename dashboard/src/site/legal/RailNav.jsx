import { useEffect, useRef, useState } from "react";

/* The section rail, with the current section marked. Carried over from the
   ELLA OS site (website1 components/legal/RailNav.tsx).

   Knowing where you are in a 4,000-word document is the whole job of this
   element. Without it the rail is a table of contents you read once; with it,
   it is a position indicator you keep glancing at — which is how people
   actually read terms, in passes, hunting for one clause.

   IntersectionObserver rather than a scroll handler: the browser does the
   geometry off the main thread, and this page is long enough that measuring
   12 headings per frame would be felt. */

export default function RailNav({ groups }) {
  const [active, setActive] = useState("");
  const seen = useRef(new Set());

  useEffect(() => {
    const ids = groups
      .flatMap((g) => g.items)
      .filter((i) => i.href.startsWith("#"))
      .map((i) => i.href.slice(1));

    const nodes = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!nodes.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) seen.current.add(e.target.id);
          else seen.current.delete(e.target.id);
        }
        // The topmost visible section wins. Without ordering, whichever
        // observer fired last would win and the marker would jump around on
        // fast scrolls.
        const first = ids.find((id) => seen.current.has(id));
        if (first) setActive(first);
      },
      {
        // A band across the upper third: a section counts as "current" once
        // its heading reaches comfortable reading height, not when its last
        // line leaves the screen.
        rootMargin: "-88px 0px -68% 0px",
        threshold: 0,
      },
    );

    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, [groups]);

  return (
    <nav aria-label="On this page" className="rail">
      {groups.map((g) => (
        <div key={g.title}>
          <p className="rail-title">{g.title}</p>
          {g.items.map((it) => (
            <a key={it.href} href={it.href}
              aria-current={it.href === `#${active}` ? "true" : undefined}>
              {it.label}
            </a>
          ))}
        </div>
      ))}
    </nav>
  );
}
