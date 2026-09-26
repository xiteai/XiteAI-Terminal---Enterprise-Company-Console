# XiteAI Terminal

**Live at [xtec.xiteai.com](https://xtec.xiteai.com).**

The XiteAI company console — every product, not just XOS1. One app, four doors:

| Door | Who | What |
|---|---|---|
| `/` | Anyone, no sign-in | The company page: what XiteAI builds, download XOS1, reach support |
| `/careers` | Anyone, no sign-in | Open roles, and applying to one |
| `/join` | New team members | Sign up with a `name@xos1.com` email; the request waits for someone above them |
| `/console` | The team | Home, Quick Links, Divisions, Products, Workplace, People, Careers, Codebase, AI keys, Access, Audit, Account |

It's a website, running at **[xtec.xiteai.com](https://xtec.xiteai.com)**. On your own PC it also
lives at **http://localhost:8710/console**, and that link always shows the newest code.
Deploying is in [DEPLOY.md](DEPLOY.md).

## First run

```
pip install -r requirements.txt
cd dashboard && npm install && cd ..
python dev.py --autostart on
```

That starts the local server and makes it start with Windows. It keeps the link current by itself
([dev.py](dev.py)):

- **Server code or `.env` changes:** the server restarts on the same port. A request made during
  the restart waits a second instead of failing.
- **Screens change:** they're rebuilt beside the live ones and swapped in. A page you left open
  shows *A newer version of this page is ready* with a **Reload** button.
- **An older server is still on the port** (this once hid a whole day's work): it's replaced.
  Nothing else can bind the port while the Terminal holds it.
- **It crashes:** it starts again. A broken edit is retried at the next save.

Its log is `data/logs/dev.log`. `python dev.py --autostart off` stops it and stops it starting
with Windows. `python run.py` is the plain one-off server, for hosting (DEPLOY.md).

Sign in with `FOUNDER_EMAIL` / `FOUNDER_PASSWORD` from `.env` (you can type just `suraj`).
Demo data (marked **DEMO** everywhere) fills every panel from one button; remove it from
**Account → Demo data** before real installs start checking in.

## The hierarchy

Founder › Vice President › Director › HR › Manager › Employee › Intern.

- **Joining:** anyone signs up at `/join` and picks the level they're joining at. Their account is
  *pending* and they see a waiting page. Everyone who can approve that level gets **one**
  notification. The first to decide wins; the others' notification is replaced by
  "X approved Y", so nobody's bell piles up.
- **Powers over people** (approve, change level/title/team, deactivate, reset password) only
  work on levels **below** your own, and only if your level holds that power. Nobody acts on
  the founder.
- **Access** (founder only): a grid of every level against every permission, including exactly
  what each level sees about customers (full name, first name only, exact age, age band, date
  of birth, region, machine fingerprints). Switches save instantly. Everything is enforced on
  the server; the UI only hides what the API already refuses.
- **Preview** (founder only): the switch in the top bar shows the console exactly as another
  level sees it, read-only.

## Where things live

```
server/
  core/        config (.env), db, schema, clock, audit trail, notifications, vault, sqlite
  security/    passwords (scrypt), sessions (hashed tokens), authenticator codes, lockout
  access/      levels, permission catalogue + defaults, effective permissions, data shaping
  web/         who's asking (deps), security headers + cross-site guard, page routes
  bootstrap/   start-up (schema, .env accounts, demo data), holding the port, keeping the build fresh
  features/    one folder per feature: routes.py (+ service.py where there's real logic)
    auth  join  people  requests  access_grid  notifications  products  settings  overview
    installs  releases  support  audit_log  account  demo  public  checkin  ai_keys  code
    workplace  feed  finance  careers  gateway
dashboard/     React (Vite): src/lib, src/components, src/charts, src/pages, src/console
contract/      checkin.schema.json + sender_reference.py: what an XOS1 install sends, and how
data/          gitignored: codebase.db, installs.db, workplace.db, code/, backups/, logs/, secret.key
```

**Where the data lives.** People, sessions, tickets, notifications, products, announcements,
finance entries, job roles and the audit trail are in MongoDB Atlas (`MONGO_CLUSTER` in `.env`).
Three things live in local SQLite files instead, next to the app:

- **`data/codebase.db`** — the Codebase's records (repositories, grants, features, owners, change
  requests, reviews, comments, checkpoints). A page of the Codebase asks dozens of small
  questions, and a change request holds whole file texts.
- **`data/installs.db`** — every install and every one of its check-ins. The busiest data there is:
  one row per install per check-in, forever.
- **`data/workplace.db`** — leave, expenses, asset requests, helpdesk tickets, payslips and
  holidays. Relational and busy, with cascading deletes.

## Home

Where the console opens, and the same for everyone on the team.

- **Birthdays** — a small marquee of who's celebrating in the next two weeks, with their photo
  and how many days away. Worked out fresh from each person's date of birth, so there's no second
  copy of it to drift.
- **Activity Hub** — what's coming up, and how it went once it has. An event can have its result
  added afterwards.
- **News** — achievements, funding, announcements. Anyone with `feed.post` (VP, Director, HR,
  founder) can post; posts can be deleted.
- A slow marquee across the top carries the headlines of what's coming up.

## Quick Links

The things the team reaches for most, each a drawn scene rather than an icon: Leave, Helpdesk,
Expenses, Assets, Approvals, Payslips, Team Directory, Handbook. Each tile only appears for
someone whose level can actually use it — Approvals is nothing but a wall to someone with no
one reporting to them.

## Divisions

One card per division with its headcount and who's in it. Each opens a room with tabs for Chat,
Uploads and Checkpoints, and the division's people down the side.

## Workplace

What the team files against the company. Leave, expenses and asset requests are **one object** on
the server — someone files it, someone senior decides it — so there's one approval path, one
history, and one place to be sure nothing decides itself twice.

- **Leave** — a real calendar, not two date fields. Click a day to pick it, click again to drop
  it, so alternate days and split weeks work the way they actually happen. Weekends and holidays
  can't be picked. Colour carries the state: blue for what you're choosing, green approved, amber
  pending, purple holiday. Eight kinds: annual (21 days), sick (10), casual (7), maternity (182,
  per the Maternity Benefit Act), paternity (15), bereavement (5), comp-off and unpaid. Your
  balance counts pending requests too — you can't spend the same day twice.
- **Holidays** — an HR-managed list. The fixed national ones are seeded; festival dates move each
  year, so HR adds the real ones rather than the server guessing.
- **Expenses** — claim what you spent, by category, up to ₹2,00,000 a claim, within six months.
- **Assets** — new kit, or a replacement for something lost or damaged. A replacement can carry a
  fine, set by whoever approves it.
- **Approvals** — everything waiting on you, across all three kinds. You only see what your level
  can actually decide: the permission for that kind, *and* a level above whoever filed it.
- **Helpdesk** — raise a ticket with IT and follow the thread. Whoever works the queue
  (`helpdesk.work`) sees everyone's and can assign, re-prioritise and close.
- **Pay** — your payslips, month by month. Seeing anyone else's needs `pay.all` and a level above
  theirs.
- **Handbook** — how the company works, in short.

**The founder files nothing.** Nobody outranks them, so there's no one left to ask: their own
leave, expenses and asset requests are approved the moment they're filed.

## Finance

Per product, under Overview: revenue, cost, and the P&L between them — total, margin, a
month-by-month trend, and a breakdown by category. Entered by hand, the way a payslip is issued
by hand; there's no billing system plugged in yet. `finance.view` to see it, `finance.manage` to
log an entry.

## Careers

- **Public** (`/careers`, no sign-in): open roles grouped by team. A team with nothing open
  doesn't get a section — it says nothing rather than spending a page on saying so. Each role has
  its own page and an apply form. The applicant count appears **only once it's past ten**, so a
  role with three applicants doesn't advertise that.
- **In the console** (`careers.manage` — VP, Director, HR, founder): post a role and it's live
  immediately, edit it in place, close or reopen it, and see everyone who applied with their
  contact details, portfolio and note.
- Applying is rate-limited per address and has a honeypot field; the same email can't apply to
  the same role twice.

## People

- **Directory and org chart**, with photos. Everyone's profile holds what they filled in at
  sign-up.
- **Employee ID** — `XT-00042`, a formatted reading of the id each person already has, so there's
  nothing to backfill and no way for it to drift from the record.
- **Promotion history** — every level or title change, with the date and who made it, and the
  date of the last one.
- **Payroll** — PF number and UAN, kept on the record for HR.
- **Photos** — asked for at sign-up (required), cropped square and compressed in the browser
  before it's sent. They show everywhere a person appears.
- **No manager assigned** — when demo data is purged, real people who reported to a demo person
  lose their manager. Their profile says so and offers an **Assign** button, rather than leaving
  a silent gap.

## Codebase

The company's code behind scoped access. **GitHub stays the master copy; the Terminal is the gate
in front of it.** The founder connects the repository once (Codebase → Repositories); the server
keeps a clone that follows GitHub every `TC_CODE_SYNC_MIN` minutes.

- **What someone can be given**, in any mix: folders, files, anything with a name (functions,
  classes, prompt sections under a capitalised heading, module-level CONSTANT settings; found by
  name every time, so access follows the code when it moves), line ranges (moved along whenever the
  file changes), or a **feature**: a named bundle of all of those. Change a feature and everyone
  holding it gets the change. Each grant is read-only or read-and-edit, optionally until a date.
- **Who gives it:** owners give in what they own (read or edit); reviewers give read access to their
  own team; `code.grant_all` gives anywhere. Always to someone below your level. You can't give what
  you don't have.
- **Only what resolves reaches the browser.** Lines someone may not see arrive as a count ("lines
  1–280 aren't shared with you"), never as text, including inside the diff of their own change.
- **A change:** edit your lines → add them to a change → send for review → approved by whoever owns
  or reviews that code (interns need two approvals; you never approve your own) → an owner merges →
  committed under the author's name and pushed to GitHub. If GitHub moved under the same lines, it
  goes back to the author to redo.
- **Checks before review:** Python and JSON syntax, and no keys or passwords in added lines.
- **Code and text only.** Binary files, models, media, archives and programs are refused; 1 MB per
  file, 5 MB and 50 files per change (`TC_CODE_MAX_*`). Oversized requests are refused before
  they're read.
- **On the record:** every grant, owner change, review and merge, and who opened which file (once a
  day each).
- **Search** across everything you may see, as you type: code, file names, and which function or
  section each hit sits in. Lines you can't see are never searched for you.
- **Reviews:** comments on exact lines; a "look closely" list of added lines that start programs,
  run built code, talk to the network, delete files, carry encoded blobs or change dependencies
  (never blocking, just where a mistake or something slipped in would have to live). A reviewer
  sees a file's diff only if they could open that whole file.

### History, undo and backups

- **History** of every change, from here or pushed straight to GitHub, trimmed to what you may read;
  a file's history with every earlier version; "who changed this" beside every line.
- **Undo any change** and **restore a file** to any earlier version: each becomes a new change that
  goes through review. Undo is a three-way merge that keeps everything written since; if later work
  touched the same lines it stops and says so.
- **Checkpoints:** named points in the history, saved as git tags here and on GitHub. Compare
  anything with one.
- **Backups:** once a day the whole history goes into one `git bundle` file (`TC_CODE_BACKUP_DIR`,
  newest `TC_CODE_BACKUPS_KEEP` kept). `git clone <file>` restores it with GitHub gone.
- **The history guard:** each sync remembers what GitHub's branch contained. If GitHub stops
  containing it (a force-push), the Terminal does not follow: it pins the real history, stops merges,
  and asks the founder to either put the real history back on GitHub or follow the new one.

### Security

- **An authenticator for everyone who opens code.** Anyone can set one up from Account; sign-in then
  asks for the code, and code opens only in a session signed in with one (the founder can switch
  that requirement off in Repositories, and it's on the record). HR, or anyone above someone with
  `people.reset`, resets a lost one. Seeds are sealed with `TC_SECRET_KEY` (or `data/secret.key`).
- **Protected paths** (seeded on connect: the updater, signing, build and release scripts, the
  installer, dependency lists): only the founder reads them, gives access to them, owns them and
  merges changes to them. `code.read_all`, owners and folder grants stop at their edge.
- **The reading alarm:** one account opening `TC_CODE_ALERT_FILES_HOUR` different files (or running
  `TC_CODE_ALERT_SEARCHES_HOUR` searches) in an hour tells the founder; at the PAUSE numbers its code
  access pauses until the founder resumes it.
- **Git never sees a raw value from a browser:** every version name is checked (a commit id, HEAD or
  a checkpoint name) before it reaches git, so nothing can smuggle in an option like `--output`.
  The GitHub token travels in git's environment, never on a command line or disk.

Default powers per level (change them in Access):

| Level | Codebase |
|---|---|
| Founder | Everything, and connects repositories |
| Vice President | Reads all code, gives access anywhere, chooses owners, approves and merges anything |
| Director | Folder map; owns what they're made owner of (give access, approve, merge there) |
| HR | Who can access what (no code), and takes access away |
| Manager | Folder map; reviews what they're made reviewer of, gives their team read access there |
| Employee | Folder map; reads and edits what they were given; sends changes |
| Intern | Same as Employee; every change needs two approvals |

The server needs `git`, and for a private repository and pushing merges, `GITHUB_TOKEN` in `.env`: a
fine-grained token with **Contents: Read and write** on that one repository. On GitHub, protect the
branch too (Settings → Branches: block force-pushes and deletion), so even a stolen token can't
rewrite history there; the Terminal's history guard is the second lock.

### Connecting your first private repository (start to finish)

If you've never touched GitHub or its tokens, do this once per codebase you want in the Terminal.

1. **The code needs to already be on GitHub, as a private repository.** If it's only on your PC
   right now: create an empty private repo at [github.com/new](https://github.com/new) (don't add
   a README — leave it empty), then from your project's folder:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. **Make a token that can only touch this one repository.**
   - **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens →
     Generate new token**.
   - **Repository access:** *Only select repositories* → pick the one repo. Never *All repositories*.
   - **Permissions → Repository permissions → Contents:** **Read and write**. Everything else
     *No access*.
   - **Expiration:** pick a date and set a reminder — the Terminal simply stops being able to push
     until you make a new one; nothing breaks or is lost.
   - **Generate token**, and copy it immediately — GitHub shows it exactly once.
3. **Put the token in `.env`**, not in the Codebase page (the Terminal never asks for it through
   the browser): `GITHUB_TOKEN=<the token>`. Saving `.env` restarts the running Terminal within a
   second.
4. **Protect the branch on GitHub:** repo → Settings → Branches → Add branch ruleset for `main` →
   **Block force pushes** and **Restrict deletions**.
5. **Connect it:** sign in → **Codebase → Repositories → Connect a repository**. Name, branch
   (`main`), address. The Terminal clones it once and then follows GitHub by itself.

## AI keys and the model gateway

**No installed copy of XOS1 ever carries an API key.** The app asks the Terminal to make the
provider call on its behalf; the key is read from the vault, used, and dropped.

- **The vault** — provider keys are encrypted at rest with AES-256-GCM, a fresh nonce each, and
  authenticated, so a tampered value fails to open rather than decrypting to garbage. The master
  key is `TC_VAULT_KEY` in `.env` and is never written to the database: whoever holds the database
  alone holds nothing useful. Generate it with the line in `.env.example`.
- **The gateway** — `POST /api/v1/ai/{provider}`. XOS1 signs the request with the same Ed25519
  device key it checks in with. The guards run cheapest first, so a flood costs almost nothing:
  body size → signature (pure CPU, no database) → replay (a signed request works once) → **is this
  a machine we know**, matching hardware hash *and* public key → per-device rate limit
  (`TC_GATEWAY_PER_MIN`, 429 + Retry-After) → only then a provider call. The key is never in the
  response and never in a log line.
- **Replacing a key** needs your password again (and your authenticator code, if you have one),
  tests the key with the provider first (a refused key changes nothing), then stores it in the
  vault and, if Cloudflare is connected, pushes it there too.
- **Reading a key in full** (`keys.reveal` — VP, HR, founder by default) needs your password
  again, is rate-limited like a sign-in, is written to the audit log with your name on it, and
  tells the founder. The database otherwise keeps only who changed which key when, and its last
  four characters.

Cloudflare is optional now and kept for the Worker path: `CF_ACCOUNT_ID`, `CF_API_TOKEN`
(**Secrets Store Write** only) and `CF_SECRETS_STORE_ID`.

## Installs checking in

XOS1 installs `POST /api/v1/checkin`. The body is signed with the install's own Ed25519 key; the
machine is identified by a **hash** of its hardware id. A copied or edited id fails the signature;
a reinstall shows up as "re-linked", never as a silent overwrite. Name and age arrive only if the
user said yes at setup; withdrawing consent clears them on the next check-in.

**The server sets the schedule, not the app.** Every accepted check-in answers with
`next_after_s`: the base cadence (`TC_CHECKIN_EVERY_S`, 6 h) plus a spread derived from the
machine's own hash (`TC_CHECKIN_SPREAD_S`, 1 h). Each machine therefore sits in a fixed slot of the
window and stays there across restarts, instead of every install waking together after an outage.
Measured over 5,000 machines, the busiest single second holds six of them.

**Under load**, in order: past `TC_CHECKIN_QUEUE_MAX` already waiting, new check-ins are told to
try again shortly (503 + Retry-After) before anything is parsed; one machine checking in faster
than `TC_CHECKIN_MIN_INTERVAL_S` is turned away (429). Accepted ones are written by one background
batcher, not one at a time, so ten thousand PCs checking in together becomes a handful of SQLite
transactions.

**The app's half of the bargain** is [contract/sender_reference.py](contract/sender_reference.py) —
drop it in or port it. Three rules: spool every check-in locally and only delete it once the
server has acknowledged it; never send the whole spool at once (a week offline drains over
several wakes); and never decide your own schedule — use the server's `next_after_s`. Failures
back off exponentially **with jitter**, because without jitter every client that failed at the
same moment retries at the same moment, which is the stampede again with extra steps. Contract:
[contract/checkin.schema.json](contract/checkin.schema.json). The XOS1 side lives in **XOS1 V17**.

## Demo data

One switch, in **Account → Demo data**, fills every panel: installs and their whole check-in
history, a second demo product, a team with photos, customer tickets, leave and expenses and
asset requests and helpdesk tickets, payslips, holidays, the Home feed, finance for both products,
and open roles with applicants. Purging removes all of it and remembers that you did, so a restart
doesn't bring it back. Hiding it is a separate switch: with demo hidden, every query adds an
`is_demo: False` filter, so the rows stay and switching back is instant.

Everything demo-seeded is marked **DEMO** wherever it appears.

## Tests

```
python tests/test_codebase.py     # 35 tests; a local bare repo stands in for GitHub
python tests/test_ai_keys.py      # 9 tests; provider and Cloudflare calls faked
python tests/test_checkin.py      # 17 tests; signing, replay, consent, batching
```

All run on a throwaway database with test accounts; none read `.env` accounts or touch `data/`.

## Security, in one screen

- Passwords live only in `.env` (gitignored) and as scrypt hashes in the database.
- Sessions: random token in an HttpOnly, SameSite=Strict cookie; only its SHA-256 is stored.
- Every write to the console API must carry the `X-TC: 1` header (a cross-site form can't add it).
- Lockout after 5 failed sign-ins per account or 20 per address, for 15 minutes.
- Optional authenticator code for the founder: set `FOUNDER_TOTP_SECRET` before going online.
- Provider API keys are encrypted at rest; the master key never touches the database.
- Device-signed endpoints (check-in, gateway) verify Ed25519 signatures before any I/O, refuse
  replays, and require the machine to already be known.
- Rate limits on every public door: sign-in, join, email checks, ticket lookups, career
  applications, check-ins and the model gateway.
- Strict Content-Security-Policy, no frames, no referrer leaks, `no-store` on every API response.
- Everything sensitive is in the audit log, including who opened a customer's or employee's
  profile and who read an API key.

**One honest note.** Anything a browser renders — code, styles, images — is in the visitor's
hands by definition; blocking right-click or devtools is bypassed in seconds and buys nothing.
Security here is on the server: every endpoint authorises independently, the client is never
trusted, and no secret is ever shipped to it.

## Coming next

Not built yet — listed so nobody has to guess what's real:

- **Division rooms** — the tabs are there; chat, uploads and checkpoints inside them are not.
- **Performance reviews** — objectives, a senior's remarks, and a year-by-year record.
- **The codebase page as a proper editor** — closer to VS Code, with a dark theme.
- **Account photo editing** — photos are captured at sign-up; changing one later isn't wired yet.
- **Sitemap, link previews and the rest of the production web surface.**
- **A retractable sidebar**, custom scrollbars, and a consistent pass of motion across the app.
- **Legal and documentation pages**, and a shared footer across every public page.
