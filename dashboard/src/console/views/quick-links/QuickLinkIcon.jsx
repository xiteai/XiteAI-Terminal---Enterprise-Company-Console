// Bespoke glyphs for Quick Links, drawn on a 24x24 grid. Each one is built
// from a quiet base and a `ql-accent` detail that moves on hover.
const GLYPHS = {
  leave: (
    <>
      <path d="M4 7.5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
      <path d="M4 10.5h16" />
      <path d="M8.5 3.5v4M15.5 3.5v4" />
      <path d="m8.75 15.25 2.25 2.25 4.25-4.5" className="ql-accent" />
    </>
  ),
  helpdesk: (
    <>
      <path d="M5 13v-1.5a7 7 0 0 1 14 0V13" />
      <path d="M3.5 14a2 2 0 0 1 2-2H7v5.5H5.5a2 2 0 0 1-2-2zM20.5 14a2 2 0 0 0-2-2H17v5.5h1.5a2 2 0 0 0 2-2z" />
      <path d="M19 17.5v.5a3 3 0 0 1-3 3h-2.5" className="ql-accent" />
    </>
  ),
  hr: (
    <>
      <path d="M9 11.5a3.25 3.25 0 1 0 0-6.5 3.25 3.25 0 0 0 0 6.5Z" />
      <path d="M3 20.5c0-3.3 2.7-5.75 6-5.75s6 2.45 6 5.75" />
      <path d="M16 5.6a3.25 3.25 0 0 1 0 6.3M18.5 15.3c1.9.75 3 2.7 3 5.2" className="ql-accent" />
    </>
  ),
  pay: (
    <>
      <path d="M2.5 7a2 2 0 0 1 2-2h15a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2z" />
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" className="ql-accent" />
      <path d="M6 12h.02M18 12h.02" />
    </>
  ),
  performance: (
    <>
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
      <path d="M12 16.5a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Z" />
      <path d="M12 13.2a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Z" className="ql-accent" fill="currentColor" stroke="none" />
    </>
  ),
  handbook: (
    <>
      <path d="M4.5 4.5a2 2 0 0 1 2-2H18a1.5 1.5 0 0 1 1.5 1.5v14H6.5a2 2 0 0 0-2 2z" />
      <path d="M4.5 17.5a2 2 0 0 1 2-2h13" />
      <path d="M8.5 7.5h7M8.5 10.75h4.5" className="ql-accent" />
    </>
  ),
  asset: (
    <>
      <path d="m12 2.75 8.5 4.4v9.7L12 21.25l-8.5-4.4v-9.7z" />
      <path d="m3.5 7.15 8.5 4.4 8.5-4.4M12 11.55v9.7" />
      <path d="m7.75 4.95 8.5 4.4" className="ql-accent" />
    </>
  ),
};

export default function QuickLinkIcon({ name, size = 24 }) {
  const g = GLYPHS[name];
  if (!g) return null;
  return (
    <svg className="ql-glyph" width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {g}
    </svg>
  );
}
