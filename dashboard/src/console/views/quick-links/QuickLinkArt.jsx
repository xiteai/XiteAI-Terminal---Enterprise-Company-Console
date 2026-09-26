// Drawn artwork for the Quick Links tiles. Editorial, not illustrative: fine
// hairlines on paper, grey for everything secondary, and ink for exactly one
// detail per scene — the one the tile is actually about. Pieces marked
// `float`, `pop`, `slide` or `draw` move when the tile is hovered.
const ART = {
  leave: (
    <>
      <rect className="paper" x="52" y="40" width="132" height="104" rx="7" />
      <path className="hair" d="M52 64h132" />
      <path className="hair" d="M80 32v14M156 32v14" />
      <rect className="mid" x="68" y="78" width="18" height="12" rx="3" />
      <rect className="mid" x="94" y="78" width="18" height="12" rx="3" />
      <rect className="mid" x="120" y="78" width="18" height="12" rx="3" />
      <rect className="mid" x="146" y="78" width="18" height="12" rx="3" />
      <rect className="mid" x="68" y="98" width="18" height="12" rx="3" />
      <rect className="ink pop" x="94" y="98" width="70" height="12" rx="6" />
      <rect className="mid" x="68" y="118" width="18" height="12" rx="3" />
      <rect className="mid" x="94" y="118" width="18" height="12" rx="3" />
      <path className="dash float" d="M196 118c22-6 34-22 38-46" />
      <path className="hair float" d="m214 48 28-12-10 29-6-11z" />
    </>
  ),
  helpdesk: (
    <>
      <rect className="paper" x="46" y="36" width="158" height="100" rx="7" />
      <path className="hair" d="M46 58h158" />
      <circle className="dot" cx="60" cy="47" r="2.5" />
      <circle className="dot" cx="70" cy="47" r="2.5" />
      <circle className="dot" cx="80" cy="47" r="2.5" />
      <rect className="mid" x="62" y="74" width="66" height="18" rx="9" />
      <rect className="ink pop" x="106" y="100" width="82" height="18" rx="9" />
      <path className="hair float" d="M204 118v-12a26 26 0 0 1 52 0v12" />
      <rect className="paper float" x="198" y="112" width="14" height="24" rx="7" />
      <rect className="paper float" x="248" y="112" width="14" height="24" rx="7" />
      <path className="hair float" d="M256 136v4a10 10 0 0 1-10 10h-12" />
    </>
  ),
  hr: (
    <>
      <path className="hair" d="m124 24 20 26M164 24l-20 26" />
      <rect className="paper" x="98" y="46" width="92" height="102" rx="8" />
      <rect className="ink" x="132" y="40" width="24" height="10" rx="5" />
      <circle className="mid-s pop" cx="144" cy="84" r="16" />
      <path className="mid pop" d="M122 122c0-12 10-21 22-21s22 9 22 21z" />
      <rect className="ink" x="118" y="132" width="52" height="7" rx="3.5" />
      <circle className="hair float" cx="52" cy="82" r="13" />
      <path className="hair float" d="M32 118c0-11 9-19 20-19s20 8 20 19" />
      <circle className="hair float" cx="236" cy="82" r="13" />
      <path className="hair float" d="M216 118c0-11 9-19 20-19s20 8 20 19" />
    </>
  ),
  pay: (
    <>
      <path className="paper" d="M54 30h108v118l-10-8-11 8-11-8-11 8-11-8-11 8-11-8-12 8z" />
      <rect className="mid" x="72" y="50" width="72" height="8" rx="4" />
      <path className="hair-2" d="M72 74h60M72 88h48" />
      <rect className="ink pop" x="72" y="104" width="72" height="20" rx="6" />
      <rect className="mid" x="72" y="134" width="44" height="7" rx="3.5" />
      <ellipse className="paper float" cx="220" cy="122" rx="34" ry="12" />
      <path className="hair float" d="M186 98v24a34 12 0 0 0 68 0V98" />
      <ellipse className="paper float" cx="220" cy="98" rx="34" ry="12" />
      <path className="hair float" d="M194 78v20a26 9 0 0 0 52 0V78" />
      <ellipse className="paper float" cx="220" cy="78" rx="26" ry="9" />
      <path className="hair float" d="M220 70v16M214 75h12M214 81h12" />
    </>
  ),
  performance: (
    <>
      <rect className="paper" x="46" y="34" width="160" height="106" rx="7" />
      <path className="dash" d="M64 64h124M64 92h124M64 118h124" />
      <path className="ink-l draw" d="m68 118 32-22 28 10 32-36 30-14" />
      <circle className="ink" cx="68" cy="118" r="3.5" />
      <circle className="ink" cx="100" cy="96" r="3.5" />
      <circle className="ink" cx="128" cy="106" r="3.5" />
      <circle className="ink" cx="160" cy="70" r="3.5" />
      <circle className="paper" cx="222" cy="104" r="34" />
      <circle className="hair pop" cx="222" cy="104" r="24" />
      <circle className="hair pop" cx="222" cy="104" r="14" />
      <circle className="ink pop" cx="222" cy="104" r="5" />
    </>
  ),
  handbook: (
    <>
      <path className="paper" d="M140 58c-15-11-37-16-58-13v76c21-3 43 2 58 13z" />
      <path className="paper" d="M140 58c15-11 37-16 58-13v76c-21-3-43 2-58 13z" />
      <path className="hair" d="M140 58v76" />
      <path className="hair-2" d="M96 70h28M96 84h32M96 98h24M156 70h28M156 84h32M156 98h24" />
      <path className="ink slide" d="M160 42v42l13-11 13 11V42z" />
    </>
  ),
  asset: (
    <>
      <rect className="paper float" x="96" y="34" width="88" height="56" rx="5" />
      <rect className="mid float" x="104" y="42" width="72" height="40" rx="2" />
      <path className="hair float" d="M88 90h104" />
      <path className="paper" d="M70 96h140v48a5 5 0 0 1-5 5H75a5 5 0 0 1-5-5z" />
      <path className="hair" d="M140 96v53" />
      <path className="paper float" d="m70 96 20-20h50v20zM210 96l-20-20h-50v20z" />
      <rect className="ink pop" x="122" y="108" width="36" height="12" rx="6" />
    </>
  ),
  expense: (
    <>
      <path className="paper" d="M52 30h104v112l-10-7-12 7-11-7-11 7-11-7-11 7-11-7-14 7z" />
      <rect className="mid" x="70" y="48" width="66" height="8" rx="4" />
      <path className="hair-2" d="M70 72h50M70 86h58M70 100h42" />
      <path className="hair" d="M70 114h68" />
      <rect className="ink pop" x="70" y="122" width="42" height="9" rx="4.5" />
      <rect className="paper float" x="164" y="74" width="104" height="66" rx="8" />
      <rect className="ink float" x="164" y="90" width="104" height="13" rx="0" />
      <rect className="mid float" x="176" y="116" width="34" height="7" rx="3.5" />
    </>
  ),
};

export default function QuickLinkArt({ name }) {
  const a = ART[name];
  if (!a) return null;
  return (
    <svg className="qlart" viewBox="0 0 280 170" fill="none"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {a}
    </svg>
  );
}
