// The site's own split, the one the privacy page rests on: what stays on the
// machine and what leaves it, as two plain columns.
const STAYS = [
  ["Your conversations and your voice", "transcribed on-device"],
  ["Your memories, notes and files", "stored on your computer"],
  ["Your calendar, portfolio, everything you make", "never uploaded"],
];
const LEAVES = [
  ["An install code, the XOS1 and Windows versions", "every check-in"],
  ["Whether updates installed, how often it had trouble", "every check-in"],
  ["Your name and age", "only if you said yes at setup"],
  ["Which features get used", "only if you turned sharing on"],
];

export default function DataPromise() {
  return (
    <section className="pub-sec" id="data">
      <div className="pub-sec-head">
        <h2 className="t-h1">Privacy</h2>
        <p className="t-lede">What stays on your computer, and what reaches us. Switch sharing off in Settings and the next check-in clears what we held.</p>
      </div>
      <div className="ledger">
        <div className="ledger-col ledger-stays">
          <div className="ledger-head">
            <span className="eyebrow">Never leaves your computer</span>
            <p>Processed on your machine. No copy is sent, and we can't see it.</p>
          </div>
          <ul>{STAYS.map(([what, how]) => <li key={what}><span>{what}</span><span className="mono">{how}</span></li>)}</ul>
        </div>
        <div className="ledger-col ledger-leaves">
          <div className="ledger-head">
            <span className="eyebrow">Sent to XiteAI</span>
            <p>So we can keep XOS1 working and updated. Nothing more.</p>
          </div>
          <ul>{LEAVES.map(([what, how]) => <li key={what}><span>{what}</span><span className="mono">{how}</span></li>)}</ul>
        </div>
      </div>
    </section>
  );
}
