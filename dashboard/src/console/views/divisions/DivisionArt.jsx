// A drawn scene per division, in the same hand as Quick Links: hairlines on
// paper, grey for anything secondary, ink for the one detail the team is
// actually about. The `float` piece moves when the card is hovered.
const ART = {
  Engineering: (
    <>
      <rect className="paper" x="54" y="38" width="172" height="104" rx="7" />
      <path className="hair" d="M54 60h172" />
      <circle className="dot" cx="68" cy="49" r="2.5" /><circle className="dot" cx="78" cy="49" r="2.5" />
      <path className="hair-2" d="M78 80h44M78 94h62M78 108h34" />
      <path className="ink-l float" d="m158 78-14 14 14 14M186 78l14 14-14 14" />
    </>
  ),
  Product: (
    <>
      <path className="paper" d="m140 30 68 36v48l-68 36-68-36V66z" />
      <path className="hair" d="m72 66 68 36 68-36M140 102v48" />
      <rect className="ink pop" x="120" y="114" width="40" height="12" rx="6" />
    </>
  ),
  Design: (
    <>
      <rect className="paper" x="58" y="36" width="164" height="108" rx="7" />
      <circle className="hair" cx="112" cy="90" r="30" />
      <path className="ink pop" d="M142 60h52v52h-52z" opacity="0.9" />
      <path className="hair-2" d="M58 122h164" />
    </>
  ),
  "Data & AI": (
    <>
      <rect className="paper" x="54" y="36" width="172" height="108" rx="7" />
      <path className="dash" d="M72 62h136M72 90h136M72 118h136" />
      <path className="ink-l draw" d="m76 124 32-26 28 12 34-38 32-16" />
      <circle className="ink" cx="76" cy="124" r="4" /><circle className="ink" cx="108" cy="98" r="4" />
      <circle className="ink pop" cx="202" cy="56" r="6" />
    </>
  ),
  Marketing: (
    <>
      <path className="paper" d="M70 78h42l58-32v88l-58-32H70z" />
      <path className="hair float" d="M186 66a30 30 0 0 1 0 48M202 54a46 46 0 0 1 0 72" />
      <rect className="ink pop" x="86" y="110" width="30" height="26" rx="4" />
    </>
  ),
  Sales: (
    <>
      <rect className="paper" x="58" y="40" width="164" height="100" rx="7" />
      <path className="hair-2" d="M78 118h124" />
      <rect className="mid" x="86" y="88" width="22" height="30" rx="3" />
      <rect className="mid" x="118" y="72" width="22" height="46" rx="3" />
      <rect className="ink pop" x="150" y="56" width="22" height="62" rx="3" />
      <path className="hair float" d="m86 70 32-16 32 10 32-24" />
    </>
  ),
  "Customer Success": (
    <>
      <rect className="paper" x="52" y="42" width="152" height="92" rx="10" />
      <path className="hair" d="M52 66h152" />
      <rect className="mid" x="70" y="84" width="66" height="18" rx="9" />
      <rect className="ink pop" x="112" y="110" width="76" height="18" rx="9" />
      <path className="hair float" d="M214 128a26 26 0 1 0-26-26" />
    </>
  ),
  "People & HR": (
    <>
      <circle className="mid-s" cx="140" cy="70" r="20" />
      <path className="mid" d="M110 126c0-16 13-28 30-28s30 12 30 28z" />
      <circle className="hair float" cx="70" cy="84" r="14" />
      <path className="hair float" d="M48 124c0-12 10-21 22-21s22 9 22 21" />
      <circle className="hair float" cx="210" cy="84" r="14" />
      <path className="hair float" d="M188 124c0-12 10-21 22-21s22 9 22 21" />
      <rect className="ink" x="116" y="134" width="48" height="8" rx="4" />
    </>
  ),
  Finance: (
    <>
      <path className="paper" d="M62 34h104v112l-10-8-11 8-11-8-11 8-11-8-11 8-11-8-12 8z" />
      <rect className="mid" x="80" y="54" width="68" height="9" rx="4.5" />
      <path className="hair-2" d="M80 78h52M80 92h44" />
      <rect className="ink pop" x="80" y="108" width="64" height="20" rx="6" />
      <ellipse className="paper float" cx="212" cy="112" rx="32" ry="11" />
      <path className="hair float" d="M180 90v22a32 11 0 0 0 64 0V90" />
      <ellipse className="paper float" cx="212" cy="90" rx="32" ry="11" />
    </>
  ),
  Operations: (
    <>
      <circle className="hair" cx="140" cy="90" r="42" />
      <circle className="paper" cx="140" cy="90" r="20" />
      <path className="hair pop" d="M140 34v16M140 130v16M84 90h16M180 90h16M100 50l11 11M169 119l11 11M180 50l-11 11M111 119l-11 11" />
      <circle className="ink pop" cx="140" cy="90" r="7" />
    </>
  ),
  Legal: (
    <>
      <path className="hair" d="M140 40v96M74 60h132" />
      <path className="paper" d="M74 60 96 112H52zM206 60l22 52h-44z" />
      <rect className="ink" x="114" y="136" width="52" height="9" rx="4.5" />
      <circle className="ink pop" cx="140" cy="40" r="6" />
    </>
  ),
  Leadership: (
    <>
      <path className="paper" d="M104 34h72v30c0 20-16 36-36 36s-36-16-36-36z" />
      <path className="hair" d="M104 44H88a17 17 0 0 0 0 34h7M176 44h16a17 17 0 0 1 0 34h-7" />
      <path className="hair" d="M140 100v18" />
      <rect className="mid" x="112" y="118" width="56" height="9" rx="3" />
      <path className="paper" d="M100 131h80v12a5 5 0 0 1-5 5h-70a5 5 0 0 1-5-5z" />
      <path className="ink pop" d="m140 46 5.5 11.2 12.4 1.8-9 8.7 2.2 12.3-11.1-5.8-11.1 5.8 2.2-12.3-9-8.7 12.4-1.8z" />
    </>
  ),
};

// A department can be added to the server's list before anyone draws it a
// scene. Rather than leave a blank band, it gets a plain one: a room, a table,
// people around it.
const FALLBACK = (
  <>
    <rect className="paper" x="54" y="38" width="172" height="104" rx="7" />
    <ellipse className="mid" cx="140" cy="96" rx="44" ry="16" />
    <circle className="hair float" cx="94" cy="72" r="10" />
    <circle className="hair float" cx="140" cy="64" r="10" />
    <circle className="hair float" cx="186" cy="72" r="10" />
    <rect className="ink pop" x="118" y="112" width="44" height="9" rx="4.5" />
  </>
);

export default function DivisionArt({ name }) {
  return (
    <svg className="qlart" viewBox="0 0 280 180" fill="none"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ART[name] || FALLBACK}
    </svg>
  );
}
