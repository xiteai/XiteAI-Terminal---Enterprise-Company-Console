/* The public site's copy and data, carried over from the ELLA OS site
   (XOS1web/website1, content/site.ts and content/legal.ts) so the Terminal's
   public pages and that site are one object rather than two that resemble
   each other.

   Adding a policy is ONE entry in `legalDocs`. The hub page, the footer and
   the sitemap all read from this array, so nothing has to be updated in three
   places and then forgotten in a fourth. */

export const site = {
  name: "ELLA OS",
  company: "XiteAI Technologies",
  // The marketing site. Pages that only exist there are linked absolutely, so
  // the footer never points at a route this app does not serve.
  web: "https://ella.xiteai.com",
  terminal: "https://xtec.xiteai.com",
  minimumAge: 18,
  contact: {
    general: "support@xiteai.com",
    privacy: "privacy@xiteai.com",
    // Kept separate from privacy@ deliberately: a vulnerability report should
    // not land in the same inbox as data-subject requests.
    security: "security@xiteai.com",
    legal: "legal@xiteai.com",
  },
};

/** Processed on the user's machine. Never transmitted. */
export const staysLocal = [
  { what: "Your voice recording", where: "transcribed on-device" },
  { what: "Your voiceprint", where: "a mathematical template, not audio" },
  { what: "Her spoken voice", where: "generated on-device" },
  { what: "Everything she remembers", where: "local database" },
  { what: "Notes, calendar, wallet, history", where: "local files" },
  { what: "Your documents", where: "read locally, never uploaded" },
];

/** Leaves the machine. Every hostname here is real. */
export const leavesDevice = [
  { what: "Your messages and her replies", where: "deepinfra · cerebras · groq" },
  { what: "Text she is deciding to remember", where: "openai" },
  { what: "What you ask her to look up", where: "duckduckgo · brave · yahoo" },
  { what: "Tickers you view", where: "yahoo finance · coingecko · nse" },
  { what: "Cities you save", where: "open-meteo" },
  { what: "News requests", where: "bbc · google news · indiatimes · livemint" },
  { what: "Updates and model fetches", where: "github · hugging face" },
];

export const legalGroups = [
  "Terms & Usage",
  "Privacy & Data",
  "AI & Ethics",
  "Support & Operations",
  "Other",
];

/* `status` says who is blocking the page, not how finished it looks:
     drafted  — written, needs a solicitor's pass
     ready    — draftable now from the codebase alone
     decision — needs a commercial answer first */
export const legalDocs = [
  // ── Terms & Usage ──────────────────────────────────────────
  {
    slug: "terms", path: "terms-of-service",
    title: "Terms of Service",
    group: "Terms & Usage",
    summary: "The agreement between you and us. Eligibility, licence, subscriptions, and where you stand.",
    status: "drafted",
    updated: "2 September 2026",
    version: "0.1 draft",
  },
  {
    slug: "acceptable-use-policy",
    title: "Acceptable Use Policy",
    group: "Terms & Usage",
    summary: "What she must not be used for, including enrolling another person's voice without telling them.",
    status: "ready",
  },
  {
    slug: "fair-usage-policy",
    title: "Fair Usage Policy",
    group: "Terms & Usage",
    summary: "What each tier includes, and what happens at the limits.",
    status: "decision",
  },
  {
    slug: "refund-policy",
    title: "Refund Policy",
    group: "Terms & Usage",
    summary: "When you get your money back, and how quickly.",
    status: "decision",
  },
  {
    slug: "beta-terms",
    title: "Beta Terms",
    group: "Terms & Usage",
    summary: "What is different while she is still in beta.",
    status: "decision",
  },

  // ── Privacy & Data ─────────────────────────────────────────
  {
    slug: "privacy", path: "privacy-policy",
    title: "Privacy Policy",
    group: "Privacy & Data",
    summary: "What stays on your computer, what leaves it, and who receives it.",
    status: "drafted",
    updated: "2 September 2026",
    version: "0.1 draft",
  },
  {
    slug: "biometrics-policy",
    title: "Biometrics Policy",
    group: "Privacy & Data",
    summary: "How your voiceprint and faceprint are made, stored, and destroyed.",
    status: "ready",
  },
  {
    slug: "data-deletion",
    title: "Data Deletion",
    group: "Privacy & Data",
    summary: "How to erase everything, and what 'everything' actually means.",
    status: "ready",
  },
  {
    slug: "third-party-disclosure",
    title: "Third-Party Disclosure",
    group: "Privacy & Data",
    summary: "Every outside service she contacts, and exactly what each one receives.",
    status: "ready",
  },
  {
    slug: "minors-policy",
    title: "Minors Policy",
    group: "Privacy & Data",
    summary: "The minimum age is 18, and the reasons it is not just a formality.",
    status: "ready",
  },
  {
    slug: "cookie-policy",
    title: "Cookie Policy",
    group: "Privacy & Data",
    summary: "What this website stores in your browser.",
    status: "ready",
  },
  {
    slug: "copyright-policy",
    title: "Copyright Policy",
    group: "Privacy & Data",
    summary: "Ownership of what she produces, and how to report infringement.",
    status: "decision",
  },

  // ── AI & Ethics ────────────────────────────────────────────
  {
    slug: "ai-disclaimer",
    title: "AI Disclaimer",
    group: "AI & Ethics",
    summary: "She can be confidently wrong. What that means for money, health and law.",
    status: "ready",
  },
  {
    slug: "responsible-ai",
    title: "Responsible AI",
    group: "AI & Ethics",
    summary: "Emotion inference, the bond she forms, and the limits we hold her to.",
    status: "ready",
  },
  {
    slug: "file-prompt-policy",
    title: "File & Prompt Policy",
    group: "AI & Ethics",
    summary: "What she may read on your disk, what she may write, and what she never sends.",
    status: "ready",
  },

  // ── Support & Operations ───────────────────────────────────
  {
    slug: "security",
    title: "Security",
    group: "Support & Operations",
    summary: "How the app and this site are protected, and how to report a vulnerability.",
    status: "ready",
  },
  {
    slug: "support-policy",
    title: "Support Policy",
    group: "Support & Operations",
    summary: "How to reach a human, and how quickly one answers.",
    status: "decision",
  },
  {
    slug: "uptime-policy",
    title: "Uptime Policy",
    group: "Support & Operations",
    summary: "What we promise about availability, and what we cannot.",
    status: "decision",
  },

  // ── Other ──────────────────────────────────────────────────
  {
    slug: "brand-guidelines",
    title: "Brand Guidelines",
    group: "Other",
    summary: "Using the ELLA OS name and mark.",
    status: "ready",
  },
];

export const published = legalDocs.filter((d) => d.status === "drafted");
export const docsInGroup = (g) => legalDocs.filter((d) => d.group === g);
export const findDoc = (slug) => legalDocs.find((d) => d.slug === slug);
