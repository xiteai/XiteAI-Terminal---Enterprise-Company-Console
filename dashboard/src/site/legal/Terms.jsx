import { Banner, Clause, Fill, Flag } from "./prose.jsx";
import LegalLayout from "./LegalLayout.jsx";

// Carried over verbatim from the ELLA OS site (website1
// app/legal/terms/page.tsx). The text is the published draft; do not edit one
// copy without the other.

const rail = [
  {
    title: "Terms",
    items: [
      { href: "#t1", label: "1 · The agreement" },
      { href: "#t2", label: "2 · Licence" },
      { href: "#t3", label: "3 · Subscriptions" },
      { href: "#t4", label: "4 · Acceptable use" },
      { href: "#t5", label: "5 · What she says" },
      { href: "#t6", label: "6 · Your files" },
      { href: "#t7", label: "7 · Availability" },
      { href: "#t8", label: "8 · Liability" },
      { href: "#t9", label: "9 · Ending it" },
      { href: "#t10", label: "10 · Law & disputes" },
    ],
  },
];

export default function Terms() {
  return (
    <LegalLayout slug="terms" rail={rail}>
      <Banner label="Draft, not yet reviewed by counsel">
        <p>
          Written against what the software actually does. Every blank marked in orange
          is a commercial or legal decision that is yours to make, and several of them
          vary by country, because consumer-protection law in the EU, UK and India limits how
          far some of these clauses can reach.
        </p>
      </Banner>

      <Clause n="1" id="t1" title="The agreement">
        <p>These terms are a contract between you and XiteAI Technologies. Installing or using ELLA means you accept them. If you do not, do not install it.</p>
        <p>You must be at least <strong>18</strong>, legally able to enter a contract, and not barred from receiving our software under any applicable sanctions or export law.</p>
      </Clause>

      <Clause n="2" id="t2" title="What you may do with it">
        <p>We grant you a personal, non-exclusive, non-transferable, revocable licence to install and use ELLA on devices you own or control, for your own use, for as long as your subscription is active.</p>
        <p>You may not copy, resell, sublicense or redistribute it; reverse-engineer, decompile or extract the models, prompts or configuration it ships with; remove attribution; or use it to build a competing product. The software, its models and its prompts remain ours.</p>
      </Clause>

      <Clause n="3" id="t3" title="Subscriptions, billing and cancellation">
        <p>ELLA is sold on a subscription. Prices, tiers and what each includes are shown before you pay. <Fill>[State the currency and whether prices include GST/VAT.]</Fill></p>
        <ul>
          <li><strong>It renews automatically</strong> at the end of each period at the then-current price, until you cancel.</li>
          <li><strong>You can cancel any time</strong> from Settings, in as few steps as it took to subscribe. Cancelling stops the next renewal; it does not refund the current period.</li>
          <li><strong>We will remind you</strong> before an annual renewal, and before any price increase, with enough notice to cancel first.</li>
          <li><strong>Refunds:</strong> <Fill>[Your policy. Note that EU consumers have a 14-day withdrawal right they can waive only by expressly consenting to immediate delivery.]</Fill></li>
          <li><strong>If payment fails</strong> we may suspend access until it is resolved. Your local data stays on your machine.</li>
        </ul>
      </Clause>

      <Clause n="4" id="t4" title="How you may not use her">
        <p>Do not use ELLA to break the law; to harass, defraud or impersonate anyone; to generate content that sexualises children or incites violence; to attack systems or bypass security; to process other people’s personal data without a lawful basis; or to feed her material you have no right to give her.</p>
        <p>She recognises voices and faces. <strong>Do not enrol another person without telling them and getting their agreement</strong>. In several jurisdictions doing so is itself unlawful, and it is your responsibility, not ours.</p>
      </Clause>

      <Clause n="5" id="t5" title="What she says is not advice">
        <p>ELLA is an AI. She can be confidently wrong, misread what you said, and produce information that is out of date or fabricated. Check anything that matters.</p>
        <p><strong>She is not a financial adviser.</strong> Prices, portfolio valuations, market news and any observation she makes about your holdings are for information only, come from third-party sources we do not control, may be delayed or wrong, and are <strong>not investment advice, a recommendation, or an offer to deal.</strong> Investment decisions are yours alone and we are not liable for them.</p>
        <p>She is likewise not a lawyer, a doctor, a therapist or an accountant, and nothing she says is professional advice in any of those fields. If you are in crisis, contact a qualified professional or your local emergency service.</p>
        <Flag label="Why this clause is longer than the others">
          <p>
            She ships with live market data, a portfolio valuer and a wallet. A user who loses
            money after acting on something she said is the most plausible claim this product
            will ever face, and a general “AI can be wrong” line does not cover it. Ask counsel
            whether your markets require a specific financial-promotions disclaimer on top.
          </p>
        </Flag>
      </Clause>

      <Clause n="6" id="t6" title="Your files, and what she can do to them">
        <p>ELLA has her own workspace folder on your disk that she can read and write. She can also <strong>browse and read</strong> the rest of your computer, and by default she cannot write to or delete anything outside her workspace. If you switch on full-device access, you take responsibility for what follows.</p>
        <p>She asks before anything destructive. She can still make mistakes. <strong>Keep backups of anything you cannot afford to lose.</strong> You are responsible for having the right to let her read the files you point her at.</p>
      </Clause>

      <Clause n="7" id="t7" title="Availability and things outside our control">
        <p>She depends on third-party AI providers and data sources. When they are down, rate-limited, or have changed their terms, parts of her stop working, and we do not promise uninterrupted service.</p>
        <p>We may change, suspend or discontinue features, and we may update the software automatically to fix security problems. If we discontinue something you paid for, <Fill>[state the remedy; a pro-rata refund is the usual and safest answer]</Fill>.</p>
      </Clause>

      <Clause n="8" id="t8" title="Warranties and liability">
        <p>Except where the law says otherwise, ELLA is provided “as is”, without warranty of any kind, and we do not warrant that she will be accurate, uninterrupted or fit for a particular purpose.</p>
        <p>To the fullest extent the law permits, we are not liable for indirect, incidental, special or consequential loss, lost profits, lost data, or losses from decisions made in reliance on anything she said. Our total liability for any claim is capped at <strong>the amount you paid us in the twelve months before it arose</strong>.</p>
        <p>Nothing here excludes liability that cannot lawfully be excluded, including death or personal injury caused by negligence, fraud, or your non-waivable statutory rights as a consumer. <Fill>[Consumer law in the EU, UK, India and Australia limits how far the paragraph above can reach; counsel should confirm the wording per market.]</Fill></p>
      </Clause>

      <Clause n="9" id="t9" title="Ending it">
        <p>You can stop at any time: cancel, and uninstall. Your local data is yours and stays on your machine until you delete it, and a factory reset removes it permanently.</p>
        <p>We may suspend or end your access if you materially breach these terms, and we will tell you why unless the law prevents us. The sections on liability, intellectual property and governing law survive.</p>
      </Clause>

      <Clause n="10" id="t10" title="Governing law and disputes">
        <p>These terms are governed by the laws of <Fill>[India, name the city for jurisdiction]</Fill>, and the courts there have exclusive jurisdiction, <strong>except</strong> that consumers keep the right to bring proceedings in their own country of residence where local law gives them that right, and nothing here removes protections their local law makes non-waivable.</p>
        <p><Fill>[Decide: a quiet negotiation period first? arbitration? Mandatory arbitration and class-action waivers are unenforceable against consumers in the EU and UK, so one global clause will not work.]</Fill></p>
      </Clause>
    </LegalLayout>
  );
}
