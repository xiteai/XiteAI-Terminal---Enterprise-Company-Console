# Handoff — XiteAI Terminal

Read this whole file before touching anything.

You are continuing work on **XiteAI Terminal**, the company console at
`c:\Users\SURAJ\XiteAI Terminal`, live at **xtec.xiteai.com**. The companion
desktop app **XOS1 V17** is at `c:\Users\SURAJ\XOS1\XOS1-CORE\XOS1 V17`. The
public marketing site **website1** (Next.js, ella.xiteai.com) is at
`C:\Users\SURAJ\XOS1web\website1` — it is the reference for anything
public-facing.

The owner is Suraj Verma, founder and CEO. Commits are authored as
`SURAJ <incxiteai@gmail.com>`, **no co-author line, ever.**

---

## The two standing rules

In his words:

> **"we fix functionalities then UI makeup shit"**

> **"SECURITY FIRST"**

And on how to work:

> "don't fuck it up" — verify each step, build before you claim done.
> "dont think much i said" — execute, don't deliberate.
> "why dont you answer my qs simple" — short answers.
> "no i am designing this so later when it grows to millions" — architect for
> scale now, not later.

---

## The UI bar — read this before writing any component

He rejected three passes of Quick Links with:

> "basic as fuck"
> "bruh a little premium and more proper na"
> "take space ... properly"
> "use premium svg's ....."
> "and it should be premium .. not childish"
> "did you not listen what i said ? its so emoty .. and svg .. means properly
> images ... like not icons"

What finally worked, and is now the house style:

- **Drawn scenes, not icons.** Each card gets a small illustration built from
  hairlines on paper, grey for everything secondary, and ink for exactly one
  detail — the thing the card is actually about.
- The vocabulary lives in `dashboard/src/styles/art.css`: classes `paper`,
  `hair`, `hair-2`, `dash`, `mid`, `mid-s`, `dot`, `ink`, `ink-l`, and the
  motion hooks `float`, `pop`, `slide`, `draw`. A card that wants the hover
  motion adds **`artcard`** beside its own class.
- Working examples: `console/views/quick-links/QuickLinkArt.jsx` and
  `console/views/divisions/DivisionArt.jsx`.
- Animate by default: staggered entrance, 0.5–0.6s,
  `cubic-bezier(0.16, 1, 0.3, 1)`. Always honour `prefers-reduced-motion`.
- Go premium on the **first** pass. He should not have to ask twice.

---

## What is DONE (do not redo)

- **#6 login page** — `pages/login/` — ink panel beside the form, staggered
  entrance, panel collapses to a header band on mobile.
- **#2.5 divisions** — twelve drawn scenes, cards structurally identical to
  Quick Links, art vocabulary extracted to `styles/art.css`.
- **#5 footer and nav** — carried over from website1. Details below.
- Legal surface: `/legal`, `/legal/privacy`, `/legal/terms`, served by the
  server and in the sitemap.

### How #5 was done, so you don't undo it

His words were:

> "btw iwant you to copy paste their footer 100% and and copy all the files
> from footer.. legal and documentation all .. just copy and make a resuable
> footer element .. and then ... put it in bottom"

> "make sure the nav bar should loook 100% exact.. why look take the nav bar
> for pc design from website1"

What exists now, all under `dashboard/src/site/`:

| File | What it is |
|---|---|
| `SiteNav.jsx` | website1's `components/chrome/Nav.tsx`, ported. Liquid-glass bar that condenses over the first 120px (`--nav-t`), a sheen that rides scroll velocity (`--nav-v`), and directional retreat — leaves on scroll down, returns on scroll up, never near the top, never while keyboard focus is inside. |
| `SiteFooter.jsx` | website1's `components/chrome/Footer.tsx`, ported. Four columns, Legal column reads published policies from `content.js`. |
| `content.js` | website1's `content/site.ts` + `content/legal.ts` merged. **One entry adds a policy** — hub, footer and sitemap all read from it. |
| `site.css` | Everything above as real CSS (website1 is Tailwind, this app is not). |
| `legal/` | `LegalHub`, `LegalLayout`, `RailNav`, `prose.jsx`, `Privacy.jsx`, `Terms.jsx` — all ported. |
| `Logo.jsx` | The marks. ELLA art is the white edition, so `brightness(0)` flattens it to ink; the XiteAI mark is already black and must NOT be filtered. |

Two things worth understanding before you edit them:

1. **The palette is scoped to `.site`, not `:root`.** It re-points the
   Terminal's own tokens (`--surface`, `--ink`, `--muted`…) to website1's warm
   paper palette, so every component inside lands in the warm world with no
   edits. The console stays monochrome. Deleting that one block in
   `site.css` puts the public pages back to white.
2. **Fonts are self-hosted.** Newsreader and IBM Plex Mono were lifted with
   their `.woff2` files out of website1's build into `dashboard/public/fonts/`
   and declared in `styles/fonts.css`. npm has no network in this environment,
   so **do not try `npm i @fontsource/...`** — it fails.

Two deliberate departures from a literal 100% copy, both to avoid shipping
broken links:

- website1's footer links `/features/`, `/contact/` and `/company/` — this app
  serves none of them, and `/company/` is already dead on website1 itself.
  Those now point absolutely at `https://ella.xiteai.com/...`, except
  `/company/` which was replaced with **Careers** (which the Terminal owns).
- `SiteFooter` takes an optional `meta` prop. Only the customer panel passes
  it, to keep the "XOS1 v1.0.7 · checked 3m ago" line the old footer had. The
  footer is otherwise byte-identical everywhere.

**Open risk to raise with him:** the privacy policy and terms are now
published in two places (ella.xiteai.com and xtec.xiteai.com). Two copies of a
legal document drift, and a drifted privacy policy is a real legal problem,
not a styling one. He asked for the copy and got it; if he'd rather have one
source, the fix is to point the Terminal's footer at
`https://ella.xiteai.com/legal/` and delete `src/site/legal/`.

---

## What is LEFT — his exact words

### 1. Apple-like animations, everywhere — NOT STARTED

> "very premium apple like animations when things appear .. smooth .. fade or
> ease whatever makes it feel premium . on whole things"

Individual pieces have entrance animation (Quick Links, Divisions, login,
legal hub). There is **no consistent system** — most console pages still just
appear. What's needed: one shared set of variants (a `stagger` parent and a
`rise` child are already duplicated in four files — hoist them into
`lib/motion.js`), then applied across every console view. Respect
`prefers-reduced-motion` throughout.

### 2. Codebase page as a real editor — NOT STARTED, biggest remaining

> "in the codebase page.. remove the heading codebase and unnecesary .. let it
> look like vs code properly.. like cursor... with dark theme options too"

`console/views/code/`. Drop the page header and chrome, go full-bleed, file
tree on the left, tabs, and a genuine dark theme toggle. This is the largest
single item left.

### 3. Mobile and tablet — PARTIAL

> "make it work on mobile and tablet properly"

Breakpoints exist across the console and the new site pages, but **nothing has
ever been checked on a real device.** Go through every page at 390px and
820px. Known un-verified: the new `.site` pages, the collapsible sidebar, the
codebase page.

### 4. Logs for AI control — PARTIAL

> "logs for AI control"

The audit trail is thorough (`console/views/audit/`). There is no API surface
for an AI to read or act on it. Clarify with him what he wants before
building.

### 5. Disable inspect — DELIBERATELY NOT DONE

> "code scurity for people inspecting.. disable it.. there is no way anyone in
> any case could hack the system"

**This was refused, honestly, and he was told why.** You cannot prevent
inspection of code you send to a browser, and any library claiming to is
theatre. Do not implement it, do not fake it, and do not quietly pretend it's
handled. What *was* done instead is real: server-side permission checks on
every route, HMAC session tokens, an AES-256-GCM vault, Ed25519 device
signatures, and an audit log. If he raises it again, repeat the honest answer
and offer the real measures.

---

## His action items, still outstanding

- Add `dashboard/public/brand/og.png` (1200×630). `index.html` already
  references it; the file does not exist.
- **Rotate the API keys** that were pasted into a chat transcript: OpenAI,
  Cerebras, DeepInfra, Groq, OpenRouter, Deepgram, NVAPI, the Google client
  secret, and the Mongo password. (Razorpay is `rzp_test_`, fine.)
- Add `checkin.start()` to XOS1's boot sequence.
- On a second machine, copy `.env` and `data/secret.key` by hand — they are
  not in the repo.

---

## How to work here

- `cd dashboard && npm run build` after every frontend change. It is ~3s and
  it is the only check that exists. Never report done without it.
- No test suite for the frontend. The server has tests; run them if you touch
  `server/`.
- npm **cannot reach the network** here. Work with what is installed:
  react 18, react-router-dom 6, framer-motion 11 (via `lib/motion.js`),
  `@fontsource/inter`, qrcode.
- Design tokens: `src/styles/tokens.css` (console, monochrome) and the `.site`
  block in `src/site/site.css` (public pages, warm paper).
- Permissions: `server/access/catalog.py`. `perms.over()` requires both the
  permission **and** outranking the target. Levels, highest first:
  founder › vp › director › hr › manager › employee › intern.
- Commit as `SURAJ <incxiteai@gmail.com>`. **No co-author line.** Write the
  message as a colleague explaining what changed and why, not as a changelog.
