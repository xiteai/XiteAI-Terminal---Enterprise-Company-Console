/* Content primitives for policy pages, carried over from the ELLA OS site
   (website1 components/legal/index.tsx).

   Structure — header, rail, breadcrumb, next/previous — belongs to
   LegalLayout. These are only the things that appear INSIDE a document's
   prose.

   Deliberately unanimated: legal text is read, printed, and pasted into a
   solicitor's email. Anything that fades in on scroll gets in the way of all
   three. */

/** A blank the company still has to fill in. Visually loud on purpose —
 *  publishing with one of these left in is the failure mode. */
export function Fill({ children }) {
  return <span className="fill">{children}</span>;
}

export function Clause({ n, title, id, children }) {
  return (
    <section id={id} className="cl">
      <h3><span className="cl-n">{n}</span>{title}</h3>
      {children}
    </section>
  );
}

export function Banner({ label, children }) {
  return (
    <div className="note note-warn">
      <span className="note-label">{label}</span>
      {children}
    </div>
  );
}

export function Flag({ label, children }) {
  return (
    <div className="note note-ember">
      <span className="note-label">{label}</span>
      {children}
    </div>
  );
}

/** Wide content scrolls inside its own container so the page body never does. */
export function DocTable({ head, rows }) {
  return (
    <div className="doc-table">
      <table>
        <thead>
          <tr>{head.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{r.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
