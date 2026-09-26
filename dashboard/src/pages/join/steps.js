// The join flow, one question per screen. Each step names the answers it
// fills (`fields`), how to check them (`validate`, mirroring the server's
// rules so errors appear before sending), and which section it belongs to.

export const SECTIONS = ["Account", "Your role", "About you", "Emergency contact", "Background", "Review"];

export const LEVEL_NOTES = {
  vp: "Leads a whole function",
  director: "Runs a team of teams",
  hr: "Hiring, onboarding and people",
  manager: "Leads a team day to day",
  employee: "Builds, designs, sells or supports",
  intern: "Learning with us for a fixed term",
};

const LOCAL = /^[a-z0-9](?:[a-z0-9._-]{0,30}[a-z0-9])?$/;
const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$/;
const PHONE = /^\+?[0-9 ()-]{7,20}$/;
const URL_RE = /^https?:\/\/\S+\.\S+/;

const need = (v, min = 2) => (v || "").trim().length >= min;
const phoneOk = (v) => PHONE.test((v || "").trim()) && ((v || "").match(/\d/g) || []).length >= 7;
const intIn = (v, lo, hi) => !v || (/^\d+$/.test(v) && +v >= lo && +v <= hi);

export function passwordRules(pw = "") {
  return [
    { ok: pw.length >= 12, text: "12 or more characters" },
    { ok: pw.toLowerCase() !== pw && pw.toUpperCase() !== pw, text: "Upper and lower case letters" },
    { ok: /\d/.test(pw), text: "At least one number" },
  ];
}

export function ageFrom(dob) {
  const d = new Date(`${dob}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  const t = new Date();
  let a = t.getFullYear() - d.getFullYear();
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a -= 1;
  return a;
}

export const STEPS = [
  {
    id: "intro", section: 0, kind: "intro",
    q: "Join the XiteAI team",
    sub: "Six short parts, about four minutes. Your answers go to the Founder and the people who approve new team members, and nowhere else. You can come back to any answer before you send.",
  },
  {
    id: "name", section: 0, kind: "fields",
    q: "What's your full name?",
    sub: "As it appears on your ID.",
    fields: [{ key: "full_name", placeholder: "First and last name", autoComplete: "name" }],
    validate: (a) => (need(a.full_name) && /\p{L}/u.test(a.full_name) ? null : { full_name: "Add your full name." }),
  },
  {
    id: "preferred", section: 0, kind: "fields", optional: true,
    q: (a) => `What should we call you, ${(a.full_name || "").trim().split(/\s+/)[0] || "there"}?`,
    sub: "The name you go by day to day. Leave it if it's your first name.",
    fields: [{ key: "preferred_name", placeholder: "Preferred name", autoComplete: "nickname" }],
  },
  {
    id: "email", section: 0, kind: "fields", special: "email",
    q: "Choose your work email",
    sub: "You'll sign in with it. Lowercase letters, numbers, dots or dashes.",
    fields: [{ key: "local", placeholder: "firstname.lastname", autoComplete: "off", suffix: "@domain", lower: true }],
    validate: (a) =>
      LOCAL.test(a.local || "") && !(a.local || "").includes("..") ? null : { local: "Use letters, numbers, dots or dashes, like priya.sharma." },
  },
  {
    id: "password", section: 0, kind: "fields", special: "password",
    q: "Set a password",
    sub: "Something only you know. You can change it later from your account.",
    fields: [{ key: "password", placeholder: "Password", type: "password", autoComplete: "new-password" }],
    validate: (a) => (passwordRules(a.password).every((r) => r.ok) ? null : { password: "Meet all three rules below." }),
  },
  {
    id: "level", section: 1, kind: "choice", key: "level",
    q: "Which level are you joining at?",
    sub: "Your request goes to people above this level. They can adjust it when they approve.",
    options: (m) => (m?.levels || []).map((l) => ({ value: l.key, label: l.label, note: LEVEL_NOTES[l.key] })),
    validate: (a) => (a.level ? null : { level: "Pick a level." }),
  },
  {
    id: "department", section: 1, kind: "choice", key: "department", dense: true,
    q: "Which team are you joining?",
    options: (m) => (m?.departments || []).map((d) => ({ value: d, label: d })),
    validate: (a) => (a.department ? null : { department: "Pick a team." }),
  },
  {
    id: "title", section: 1, kind: "fields",
    q: "What's your job title?",
    sub: "Pick one or type your own.",
    fields: [{ key: "title", placeholder: "e.g. Software Engineer (SDE I)" }],
    suggest: (m, a) => m?.titles?.[a.department] || [],
    validate: (a) => (need(a.title) ? null : { title: "Add your job title." }),
  },
  {
    id: "employment", section: 1, kind: "choice", key: "employment_type",
    q: "How are you employed?",
    options: (m) => (m?.employment_types || []).map((t) => ({ value: t, label: t })),
    validate: (a) => (a.employment_type ? null : { employment_type: "Pick one." }),
  },
  {
    id: "start", section: 1, kind: "fields", optional: true,
    q: "When do you start?",
    sub: "Your first working day, if you know it.",
    fields: [{ key: "start_date", type: "date" }],
  },
  {
    id: "photo", section: 2, kind: "photo", key: "photo",
    q: "Add a photo",
    sub: "Shows on your profile and in the team directory. Required to join.",
    validate: (a) => (a.photo ? null : { photo: "Add a photo to continue." }),
  },
  {
    id: "dob", section: 2, kind: "fields",
    q: "When were you born?",
    sub: "Used for HR records only.",
    fields: [{ key: "dob", type: "date", autoComplete: "bday" }],
    validate: (a) => {
      const age = a.dob ? ageFrom(a.dob) : null;
      return age !== null && age >= 16 && age <= 90 ? null : { dob: "That date of birth doesn't look right." };
    },
  },
  {
    id: "gender", section: 2, kind: "choice", key: "gender", optional: true,
    q: "How do you identify?",
    sub: "Optional.",
    options: (m) => (m?.genders || []).map((g) => ({ value: g, label: g })),
  },
  {
    id: "contact", section: 2, kind: "fields",
    q: "How can we reach you?",
    sub: "Outside work, for anything urgent.",
    fields: [
      { key: "phone", label: "Phone", placeholder: "+91 98765 43210", type: "tel", autoComplete: "tel", inputMode: "tel" },
      { key: "personal_email", label: "Personal email", placeholder: "you@gmail.com", type: "email", autoComplete: "email" },
    ],
    validate: (a) => {
      const e = {};
      if (!phoneOk(a.phone)) e.phone = "Add a phone number with its country code.";
      if (!EMAIL.test((a.personal_email || "").trim())) e.personal_email = "That email doesn't look right.";
      return Object.keys(e).length ? e : null;
    },
  },
  {
    id: "home", section: 2, kind: "fields",
    q: "Where are you based?",
    fields: [
      { key: "city", label: "City", placeholder: "e.g. Noida", autoComplete: "address-level2" },
      { key: "address", label: "Address", placeholder: "Optional", autoComplete: "street-address", optional: true },
    ],
    validate: (a) => (need(a.city) ? null : { city: "Add your city." }),
  },
  {
    id: "emergency", section: 3, kind: "fields",
    q: "Who should we call in an emergency?",
    sub: "Someone we can reach if something happens at work.",
    fields: [
      { key: "emergency_name", label: "Their name", placeholder: "Full name" },
      { key: "emergency_relation", label: "They are your", chips: "relationships", placeholder: "e.g. Parent" },
      { key: "emergency_phone", label: "Their phone", placeholder: "+91 …", type: "tel", inputMode: "tel" },
    ],
    validate: (a) => {
      const e = {};
      if (!need(a.emergency_name)) e.emergency_name = "Add their name.";
      if (!need(a.emergency_relation)) e.emergency_relation = "How do you know them?";
      if (!phoneOk(a.emergency_phone)) e.emergency_phone = "Add their phone number.";
      return Object.keys(e).length ? e : null;
    },
  },
  {
    id: "education", section: 4, kind: "fields",
    q: "Your education",
    sub: "Your highest qualification. This one we do need.",
    fields: [
      { key: "qualification", label: "Qualification", chips: "qualifications", placeholder: "e.g. Bachelor's degree" },
      { key: "institution", label: "College or university", placeholder: "e.g. Amity University" },
      { key: "graduation_year", label: "Year", placeholder: "e.g. 2024", inputMode: "numeric" },
    ],
    validate: (a) => {
      const e = {};
      if (!need(a.qualification)) e.qualification = "Add your qualification.";
      if (!need(a.institution)) e.institution = "Add where you studied.";
      if (!intIn(a.graduation_year, 1950, 2040)) e.graduation_year = "Use a year like 2024.";
      return Object.keys(e).length ? e : null;
    },
  },
  {
    id: "experience", section: 4, kind: "fields", optional: true,
    q: "Your experience so far",
    fields: [
      { key: "experience_years", label: "Years of experience", placeholder: "e.g. 2", inputMode: "numeric", optional: true },
      { key: "previous_company", label: "Most recent company", placeholder: "Optional", optional: true },
    ],
    validate: (a) => (intIn(a.experience_years, 0, 60) ? null : { experience_years: "A number from 0 to 60." }),
  },
  {
    id: "skills", section: 4, kind: "fields", optional: true,
    q: "What are you good at?",
    sub: "A few skills, separated by commas.",
    fields: [{ key: "skills", placeholder: "Python, React, Figma…", optional: true }],
  },
  {
    id: "links", section: 4, kind: "fields", optional: true,
    q: "Anywhere we can see your work?",
    fields: [
      { key: "linkedin", label: "LinkedIn", placeholder: "https://linkedin.com/in/…", type: "url", optional: true },
      { key: "portfolio", label: "GitHub or portfolio", placeholder: "https://…", type: "url", optional: true },
    ],
    validate: (a) => {
      const e = {};
      if (a.linkedin && !URL_RE.test(a.linkedin)) e.linkedin = "Paste the full link, starting with https://";
      if (a.portfolio && !URL_RE.test(a.portfolio)) e.portfolio = "Paste the full link, starting with https://";
      return Object.keys(e).length ? e : null;
    },
  },
  {
    id: "about", section: 4, kind: "fields", optional: true,
    q: "Anything the team should know?",
    sub: "A line about you, how you like to work, or nothing at all.",
    fields: [{ key: "about", placeholder: "Optional", textarea: true, optional: true }],
  },
  {
    id: "review", section: 5, kind: "review",
    q: "Check everything, then send",
    sub: "You can go back to any answer. Nothing is sent until you press the button.",
    validate: (a) => (a.agree_accurate && a.agree_storage ? null : { agree: "Tick both boxes to send your request." }),
  },
];

export const STEP_OF_FIELD = Object.fromEntries(
  STEPS.flatMap((s, i) => [...(s.fields || []).map((f) => [f.key, i]), ...(s.key ? [[s.key, i]] : [])]),
);

export const questionText = (step, answers) => (typeof step.q === "function" ? step.q(answers) : step.q);
