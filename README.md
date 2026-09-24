# XiteAI Terminal

The XiteAI company console — every product, not just XOS1. One app, three doors:

| Door | Who | What |
|---|---|---|
| `/` | Customers, no sign-in | XOS1 status, what's new, send a request, check a request, what data we keep |
| `/join` | New team members | Sign up with a `name@xos1.com` email; the request waits for someone above them |
| `/console` | The team | Overview, installs, releases, support, people, codebase, AI keys, access, audit, account |

It's a website. On your PC it lives at **http://localhost:8710/console**, and that link always
shows the newest code. To put it online at `xos1dashboard.xiteai.com`, follow [DEPLOY.md](DEPLOY.md).

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
Demo data (marked **DEMO** everywhere) fills every panel; remove it from **Account → Demo data**
before real installs start checking in.

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
  core/        config (.env), db, schema, clock, audit trail, notifications
  security/    passwords (scrypt), sessions (hashed tokens), authenticator codes, lockout
  access/      levels, permission catalogue + defaults, effective permissions, data shaping
  web/         who's asking (deps), security headers + cross-site guard, page routes
  bootstrap/   start-up (schema, .env accounts, demo data), holding the port, keeping the build fresh
  features/    one folder per feature: routes.py (+ service.py where there's real logic)
    auth  join  people  requests  access_grid  notifications  overview  installs
    releases  support  audit_log  account  demo  public  checkin
dashboard/     React (Vite): src/lib, src/components, src/charts, src/pages, src/console
contract/      checkin.schema.json: what an XOS1 install sends
data/          terminal.db (gitignored: it holds real people's details)
```

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
   (`git remote add` uses the address GitHub shows you on the empty repo's page, under **…or push
   an existing repository from the command line**.)
2. **Make a token that can only touch this one repository.**
   - Go to **GitHub → your profile photo → Settings → Developer settings → Personal access tokens
     → Fine-grained tokens → Generate new token**.
   - **Repository access:** *Only select repositories* → pick the one repo. Never *All repositories*.
   - **Permissions → Repository permissions → Contents:** set to **Read and write**. Leave
     everything else as *No access*.
   - **Expiration:** pick a date (GitHub won't let a fine-grained token last forever); put a
     reminder to make a new one before it expires — the Terminal will simply stop being able to
     push until you do, nothing breaks or is lost.
   - Click **Generate token**, and copy it immediately — GitHub shows it exactly once.
3. **Put the token in the Terminal's `.env`**, not in the Codebase page (the Terminal never asks
   for it through the browser):
   ```
   GITHUB_TOKEN=<the token you just copied>
   ```
   Then restart: `python dev.py --autostart on` if you're not already running it, or just save
   `.env` — the running Terminal restarts itself within a second and picks it up.
4. **Protect the branch on GitHub itself**, so nobody (not even with the token) can force-history
   away: **repo → Settings → Branches → Add branch ruleset** (or *classic* Branch protection rules)
   for `main` → turn on **Block force pushes** and **Restrict deletions**.
5. **Connect it in the Terminal:** sign in → **Codebase → Repositories → Connect a repository**.
   Give it a name, the branch (`main`), and the GitHub address
   (`https://github.com/<you>/<repo>.git`). The Terminal clones it once and then follows GitHub by
   itself. From here, everything — who sees what, who approves what, what gets pushed back — is
   set up on the **Codebase** and **Access** pages, not on GitHub.

If the repository is already private and already has people pushing to it directly, nothing above
changes that: the token only lets the Terminal read it and push changes it approved. Nobody has to
stop using `git push` themselves if they still want to — the Terminal just becomes the other,
supervised door into the same repository.

## AI keys

The keys every XOS1 install uses live in **Cloudflare Secrets Store**, not in the app. The AI keys
page can replace a key and never show one: it needs your password again (and your authenticator
code, if you have one), tests the key with the provider first (a refused key changes nothing), then
hands it to Cloudflare. The database keeps only who changed which key when, and its last four
characters. Needs `CF_ACCOUNT_ID`, `CF_API_TOKEN` (permission **Secrets Store Write** only) and
`CF_SECRETS_STORE_ID` in `.env`. `keys.view` / `keys.replace` in the Access grid decide who.

## Tests

```
python tests/test_codebase.py     # 35 tests; a local bare repo stands in for GitHub
python tests/test_ai_keys.py      # 9 tests; provider and Cloudflare calls faked
```

Both run on a throwaway database with test accounts; neither reads `.env` accounts or touches `data/`.

## Installs checking in

XOS1 installs will `POST /api/v1/checkin` every time the updater checks for a new version
(every 6 h). The body is signed with the install's own Ed25519 key; the machine is identified by
a **hash** of its hardware id. A copied or edited id fails the signature; a reinstall shows up as
"re-linked", never as a silent overwrite. Name and age arrive only if the user said yes at setup;
withdrawing consent clears them on the next check-in. Contract: [contract/checkin.schema.json](contract/checkin.schema.json).
The XOS1 side of this (key pair, signed check-in on the update timer, the consent switch) is the
next thing to build in the app.

## Security, in one screen

- Passwords live only in `.env` (gitignored) and as scrypt hashes in the database.
- Sessions: random token in an HttpOnly, SameSite=Strict cookie; only its SHA-256 is stored.
- Every write to the console API must carry the `X-TC: 1` header (a cross-site form can't add it).
- Lockout after 5 failed sign-ins per account or 20 per address, for 15 minutes.
- Optional authenticator code for the founder: set `FOUNDER_TOTP_SECRET` before going online.
- Strict Content-Security-Policy, no frames, no referrer leaks, `no-store` on every API response.
- Everything sensitive is in the audit log, including who opened a customer's or employee's profile.
