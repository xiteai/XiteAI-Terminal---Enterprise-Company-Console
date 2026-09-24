import "./PageHeader.css";

// How every console page opens: a title (with an optional logo before it and
// a badge after it), one plain line under it, and the page's controls on the right.
export default function PageHeader({ title, lead, badge, subtitle, meta, children }) {
  return (
    <header className="page-head">
      <div className="page-titles">
        <div className="page-title-row">
          {lead}
          <h1 className="t-h1">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="page-sub">{subtitle}</p>}
        {meta && <div className="page-meta">{meta}</div>}
      </div>
      {children && <div className="page-tools">{children}</div>}
    </header>
  );
}
