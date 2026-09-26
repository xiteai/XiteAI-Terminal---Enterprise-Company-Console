import { Banner, Clause, DocTable, Fill, Flag } from "./prose.jsx";
import LegalLayout from "./LegalLayout.jsx";
import { staysLocal, leavesDevice } from "../content.js";

// Carried over verbatim from the ELLA OS site (website1
// app/legal/privacy/page.tsx). The ledger below is quoted from the same two
// arrays the site uses, and a drift between them and the software is a false
// privacy claim, not a typo.

const rail = [
  {
    title: "Privacy",
    items: [
      { href: "#ledger", label: "Where your data goes" },
      { href: "#p1", label: "1 · Who we are" },
      { href: "#p2", label: "2 · What we collect" },
      { href: "#p3", label: "3 · Voice & face" },
      { href: "#p4", label: "4 · Emotional state" },
      { href: "#p5", label: "5 · Who else sees it" },
      { href: "#p6", label: "6 · Why we're allowed" },
      { href: "#p7", label: "7 · How long we keep it" },
      { href: "#p8", label: "8 · Your rights" },
      { href: "#p9", label: "9 · Security" },
      { href: "#p10", label: "10 · Children" },
      { href: "#p11", label: "11 · Contact" },
    ],
  },
];

function Col({ tone, head, note, rows }) {
  return (
    <div className={`ledger-col ledger-${tone}`}>
      <div className="ledger-head">
        <b>{head}</b>
        <span className="ledger-note">{note}</span>
      </div>
      <ul>
        {rows.map((r) => (
          <li key={r.what}>
            <b>{r.what}</b>
            <span>{r.where}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Ledger() {
  return (
    <div className="ledger">
      <Col tone="on" head="Never leaves your computer"
        note="Processed locally. No copy is transmitted, and we cannot access it."
        rows={staysLocal} />
      <Col tone="off" head="Sent to named third parties"
        note="Required to answer you. Each receives only what its job needs."
        rows={leavesDevice} />
    </div>
  );
}

export default function Privacy() {
  return (
    <LegalLayout slug="privacy" rail={rail}>
      <Banner label="Draft, not yet reviewed by counsel">
        <p>
          Accurate to what the software does today, and written to be readable. It still
          needs a qualified lawyer before it goes live. Every blank marked in orange is a
          decision only you or your solicitor can make.
        </p>
      </Banner>

      <section id="ledger" style={{ scrollMarginTop: "6rem" }}>
        <h2>Where your data actually goes</h2>
        <p>Everything below rests on one split. It was taken from the source code, not from intention.</p>
        <Ledger />
      </section>

      <Clause n="1" id="p1" title="Who we are">
        <p>
          ELLA OS is made by XiteAI Technologies, <Fill>[full registered name and address]</Fill>,
          India. For GDPR purposes we are the <strong>controller</strong> of the personal data
          described here. Reach us at <Fill>[privacy@…]</Fill>.
        </p>
      </Clause>

      <Clause n="2" id="p2" title="What we collect, and where it lives">
        <p>ELLA runs mostly on your own computer. The distinction above is the most important thing in this policy.</p>
        <p><strong>Stays on your device.</strong> Your voice recordings and their transcription, your voiceprint, your faceprint, everything she remembers about you, your notes, calendar, wallet entries, saved files and your conversation history. All of it sits in your user profile on your machine. We have no copy and no access.</p>
        <p><strong>Leaves your device.</strong> To answer you at all, the text of your conversation is sent to the AI providers listed in section 5. Depending on what you ask, we also send that specific query, whether a search phrase, a ticker symbol or a city name, to the relevant service. Nothing is sent that is not needed to produce the answer you asked for.</p>
        <p><strong>What we never collect.</strong> Your audio, your camera images, your biometric templates, your files, or the contents of her memory.</p>
      </Clause>

      <Clause n="3" id="p3" title="Voice and face recognition">
        <p>ELLA can learn to recognise you by voice, and, only if you turn the camera on, by face. She converts a sample into a <strong>mathematical template</strong>: a list of numbers from which the original audio or image cannot be reconstructed. The recording itself is discarded.</p>
        <p>These templates are <strong>biometric identifiers</strong> and are treated as sensitive personal data. They are:</p>
        <ul>
          <li>created only after you have been told and have agreed;</li>
          <li>stored on your device only, never transmitted to us or anyone else;</li>
          <li>never sold, leased, traded or used for advertising;</li>
          <li>deleted permanently when you delete them in Settings, or when you factory-reset the app;</li>
          <li>otherwise retained only while your account is active, and destroyed within <Fill>[X]</Fill> of your last use.</li>
        </ul>
        <p>The camera is off by default. With it off, it is never opened, sampled or read.</p>
        <Flag label="Product decision required before launch">
          <p>
            Onboarding currently learns the owner’s voice <strong>silently, from natural speech</strong>.
            Under Illinois BIPA, written informed consent must be obtained <em>before</em> a biometric
            identifier is captured, so this needs a consent step ahead of listening, an opt-in, or a
            geographic exclusion. No wording in this document can make silent collection lawful.
          </p>
        </Flag>
      </Clause>

      <Clause n="4" id="p4" title="Emotional state and tone">
        <p><strong>This is switched off in the current release.</strong> The capability is built and described here so that the disclosure exists before it is ever turned on, not because it is running today.</p>
        <p>When it is enabled, ELLA analyses <em>how</em> you sound, its pitch, pace and timbre, to estimate whether you seem tired, tense or animated, and adjusts how she speaks to you. That is emotion inference, and you are entitled to know when it is happening.</p>
        <p>It runs entirely on your device. What would reach the AI provider is at most a short label such as “tired”, never your audio. It stays switchable in Settings, and she works without it.</p>
        <p>She is an AI. She is not a person, not a therapist, and nothing she says is a clinical judgement about your mental state.</p>
      </Clause>

      <Clause n="5" id="p5" title="Who else sees your data">
        <p>We use the following providers to make her work. Each receives only what its function requires.</p>
        <DocTable
          head={["Provider", "What it receives", "Purpose"]}
          rows={[
            [<b key="a">DeepInfra · Cerebras · Groq</b>, "Your conversation text, and what she knows that is relevant to your question", "Generating replies; choosing which tool to run"],
            [<b key="b">OpenAI</b>, "The text of a message she is deciding whether to remember", "Extracting facts worth keeping"],
            [<b key="c">DuckDuckGo · Brave · Yahoo</b>, "Your search phrase", "Answering questions about current events"],
            [<b key="d">Yahoo Finance · CoinGecko · NSE</b>, "The symbols you look up", "Prices and market data"],
            [<b key="e">Open-Meteo</b>, "The city or coordinates you save", "Weather"],
            [<b key="f">News publishers · Wikimedia</b>, "A category or a date", "Headlines and “on this day”"],
            [<b key="g">GitHub · Hugging Face</b>, "Your app version; no personal data", "Updates and model downloads"],
          ]}
        />
        <p>We do not sell your personal data, and we do not share it for advertising.</p>
        <p><Fill>[Once zero-retention and no-training agreements are signed with each provider, state them here and make the commitment binding. Until then this section must describe what is actually true.]</Fill></p>
      </Clause>

      <Clause n="6" id="p6" title="Why we are allowed to process it">
        <DocTable
          head={["What", "Lawful basis (GDPR)"]}
          rows={[
            ["Running the conversation you started", "Performance of a contract, Art. 6(1)(b)"],
            ["Voice and face recognition", <span key="x"><b>Explicit consent</b>, Art. 9(2)(a), withdrawable at any time</span>],
            ["Emotion inference", "Consent, withdrawable in Settings"],
            ["Security, abuse prevention, crash diagnostics", "Legitimate interests, Art. 6(1)(f)"],
            ["Billing and tax records", "Legal obligation, Art. 6(1)(c)"],
          ]}
        />
        <p>Under India’s DPDP Act our basis is your consent, given through the notice shown when you first set ELLA up, and withdrawable at any time.</p>
      </Clause>

      <Clause n="7" id="p7" title="How long things are kept">
        <p><strong>On your device:</strong> until you delete them. A factory reset erases every memory, note, conversation, alarm and biometric template permanently and irreversibly.</p>
        <p><strong>With our AI providers:</strong> your conversation text is processed to produce a reply and is subject to each provider’s own retention policy. <Fill>[State today’s actual position, including any period a provider retains data for abuse monitoring.]</Fill></p>
        <p><strong>With us:</strong> account and billing records for as long as the law requires us to keep them.</p>
      </Clause>

      <Clause n="8" id="p8" title="Your rights">
        <p>Because most of your data never reaches us, you already hold the strongest form of these rights: it is on your machine, and you can delete it yourself at any time without asking us.</p>
        <p>For what we do hold, your account and your subscription, you can ask us to show it to you, correct it, delete it, hand it over in a portable format, or stop processing it. In the EU or UK you may also object to processing and complain to your national supervisory authority. In India you may nominate someone to exercise these rights for you and complain to the Data Protection Board. In California you may ask what categories we collected and opt out of sharing; we honour Global Privacy Control signals.</p>
        <p>Write to <Fill>[privacy@…]</Fill> and we will answer within <Fill>[30 days]</Fill>. We will never charge you for asking, or treat you differently for having asked.</p>
      </Clause>

      <Clause n="9" id="p9" title="Security">
        <p>Data in transit is encrypted with TLS. Your local data sits in your operating system’s user profile, protected by your device’s own account security. <strong>Which means anyone who can log into your computer can read it.</strong> Put a password on your machine, and encrypt the disk if the contents matter.</p>
        <p>If a breach affects your personal data we will notify the relevant regulator within 72 hours where required, and tell you without undue delay.</p>
      </Clause>

      <Clause n="10" id="p10" title="Children">
        <p>You must be <strong>18 or older</strong> to install or use ELLA. We do not knowingly collect data from anyone under 18; if we learn we have, we delete it.</p>
        <p>This is deliberate. She builds a detailed picture of your life, recognises you biometrically, and is designed to be someone you become attached to. We do not think that belongs in the hands of a child, and India’s DPDP Act separately prohibits behavioural monitoring of anyone under 18.</p>
      </Clause>

      <Clause n="11" id="p11" title="Contact, and changes">
        <p><strong>Grievance Officer (India, DPDP Act):</strong> <Fill>[name, email, postal address]</Fill>. Required by law to be published, and to respond within a fixed period.</p>
        <p><strong>EU/UK representative:</strong> <Fill>[required under GDPR Art. 27 where there is no EU establishment]</Fill>.</p>
        <p>If we change this policy in a way that affects you, we will tell you inside the app before it takes effect. Continuing to use ELLA after that means you accept the new version.</p>
      </Clause>
    </LegalLayout>
  );
}
