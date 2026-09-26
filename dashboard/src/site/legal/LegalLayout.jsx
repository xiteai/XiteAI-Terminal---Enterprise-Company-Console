import { useEffect } from "react";
import { Link } from "react-router-dom";
import SiteNav from "../SiteNav.jsx";
import SiteFooter from "../SiteFooter.jsx";
import RailNav from "./RailNav.jsx";
import { site, published, findDoc } from "../content.js";

/* One shell for every policy. Carried over from the ELLA OS site (website1
   components/legal/LegalLayout.tsx).

   Each page used to build its own grid, rail and header, which means nineteen
   documents is nineteen chances for the layout to drift — exactly how the old
   site ended up maintaining a footer in thirty-one files. A policy page is
   now its content and nothing else; everything structural lives here.

   It also fixes the thing that made the old pages feel like islands: a
   breadcrumb back to the hub, and a real next/previous through the legal
   surface in reading order, so the set behaves like one document rather than
   nineteen dead ends. */

export default function LegalLayout({ slug, rail, children }) {
  const doc = findDoc(slug);
  const i = published.findIndex((d) => d.slug === slug);
  const prev = i > 0 ? published[i - 1] : null;
  const next = i >= 0 && i < published.length - 1 ? published[i + 1] : null;

  useEffect(() => {
    document.title = `${doc?.title ?? slug} · ${site.company}`;
  }, [doc, slug]);

  return (
    <div className="site">
      <SiteNav />
      <main className="site-wrap site-top">
        {/* Small, but it is the difference between a page you landed on from
            a search result and a page inside a structure. */}
        <nav aria-label="Breadcrumb" className="ld-crumb">
          <Link to="/legal">Legal</Link>
          <span>/</span>
          <b>{doc?.title ?? slug}</b>
        </nav>

        <header className="ld-head">
          <h1>{doc?.title ?? slug}</h1>
          {doc?.summary && <p className="ld-sum">{doc.summary}</p>}
          <div className="ld-meta">
            <span>Updated <b>{doc?.updated ?? "—"}</b></span>
            <span>Version <b>{doc?.version ?? "0.1"}</b></span>
            <span>Applies <b>Worldwide</b></span>
            <span>Minimum age <b>{site.minimumAge}</b></span>
          </div>
        </header>

        <div className="ld-body">
          <article className="prose-legal ld-article">{children}</article>
          <aside className="ld-rail"><RailNav groups={rail} /></aside>
        </div>

        {/* Where to go next. A legal page with no exit but the back button is
            the clearest sign nobody designed it. */}
        <nav className="ld-move">
          {[prev, next].map((d, idx) => {
            const dir = idx === 0 ? "Previous" : "Next";
            if (!d) {
              return (
                <div key={dir} className="ld-move-end">
                  <p className="ld-move-dir">{dir}</p>
                  <p className="ld-move-none">{idx === 0 ? "Start of the set" : "End of the set"}</p>
                </div>
              );
            }
            return (
              <Link key={dir} to={`/legal/${d.slug}`}>
                <p className="ld-move-dir">{dir}</p>
                <p className="ld-move-title">{d.title}</p>
              </Link>
            );
          })}
        </nav>

        {/* One place to ask a human. Every policy needs it and none of them
            should have to remember to include it. */}
        <div className="ld-ask">
          <p>Something here unclear, or wrong? That is worth knowing, because these
            pages are meant to be read, not survived.</p>
          <a href={`mailto:${site.contact.legal}`}>{site.contact.legal}</a>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
