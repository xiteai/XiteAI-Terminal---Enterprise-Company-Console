# Putting XiteAI Terminal online

Two jobs: keep the code on GitHub, and make `xtec.xiteai.com` reach the app.

## 1. GitHub: where the repo lives

**Green squares come from who commits, not where the repo is.** Every commit authored as
`sv9052788@gmail.com` counts on your personal profile, in your own repos or in a company
organization you belong to. For a private repo, turn on **Settings → Public profile →
"Include private contributions on my profile"** so they show.

Recommended setup:

1. `github.com/xiteai` is a *personal user account* today, not an organization. Turn it into
   one: sign in as `xiteai` → **Settings → Organizations → Turn into an organization**, and make
   `SURAj-Verma-ai` its owner. (After that you sign in as yourself, never as `xiteai`.)
   If you'd rather keep that account, create a new organization instead (e.g. `xiteai-tech`).
2. Create a **private** repo in it: `xiteai/xos1-terminal-control`. It's the admin panel over
   users' data, so it stays private. Open-source something safe later (the check-in SDK) if you
   want outside contributions.
3. Push, from this folder:

```
git init -b main
git add .
git commit -m "XiteAI Terminal: company console"
git remote add origin https://github.com/xiteai/xos1-terminal-control.git
git push -u origin main
```

`.env`, `data/`, `node_modules/` and `dist/` are gitignored: passwords and user data never leave
this PC. Check with `git status` before the first push.

Don't mirror the same repo in two places: issues, stars and pull requests split, and nobody knows
where to contribute.

## 2. The address: xtec.xiteai.com

### Option A (recommended now, ₹0): the Terminal on a PC you keep on + a Cloudflare Tunnel

The Terminal runs on a PC that stays on (a spare one is ideal — `python dev.py --autostart on`:
it starts with Windows and always serves the newest code); the tunnel gives it the public address
with HTTPS, without opening any port on the router. Nothing to buy. While that PC is off, the
address shows as unreachable; installs keep their check-ins and send them when it's back.

**Setting up the PC that will run it** (skip if it's already set up, e.g. this one):
```
git clone https://github.com/xiteai/xos1-terminal-control.git   # the Terminal's own repo
cd xos1-terminal-control
# copy .env from a working install — it's gitignored, it never comes with git clone
pip install -r requirements.txt
cd dashboard && npm ci && npm run build && cd ..
python dev.py --autostart on
```
(You never clone your product's own code anywhere by hand — the Codebase feature clones it into
`data/code` on its own, once `GITHUB_TOKEN` is set in `.env`.)

**Then, all from the Cloudflare dashboard (dash.cloudflare.com):**

1. **Move xiteai.com's DNS to Cloudflare (free).** The website stays on Hostinger; only the
   phone book moves.
   - **Add a site** → `xiteai.com` → Free plan.
   - Cloudflare copies your existing records. **Check the list** before continuing: the `@`
     record (the website), `chat`, `www`, and any `MX`/`TXT` email records must all be there,
     with the same values as in Hostinger's DNS zone.
   - In Hostinger hPanel → **Domains → xiteai.com → DNS / Nameservers → Change nameservers**,
     enter the two nameservers Cloudflare gave you. Takes minutes to a few hours; Cloudflare
     emails you once the domain shows **Active**.
2. **Create the tunnel.** Left sidebar → **Zero Trust** (first time, it asks for a team name —
   anything works, free up to 50 users) → **Networks → Tunnels → Create a tunnel → Cloudflared**
   → name it `xtec` → Save. It shows an install command for Windows: run that in
   **PowerShell as Administrator** on the PC from the step above. The tunnel shows **Connected**
   within a few seconds.
3. **Point it at the app.** Same tunnel → **Public Hostname** tab → **Add a public hostname**:
   subdomain `xtec`, domain `xiteai.com`, Service Type `HTTP`, URL `localhost:8710` → Save.
4. **Before it's reachable, lock it down.** In `.env`:
   ```
   TC_COOKIE_SECURE=true
   FOUNDER_TOTP_SECRET=<base32 secret>
   ```
   Make the secret with
   `python -c "import base64,secrets;print(base64.b32encode(secrets.token_bytes(20)).decode())"`,
   add it to Google Authenticator (or any authenticator app) as a key. The server picks up the change by itself.
   From then on, signing in as founder also asks for the 6-digit code.
5. Open `https://xtec.xiteai.com`. The customer page is `/`, the team signs in at
   `/login`, new members join at `/join`.

### Option B (always on, ₹0): Oracle Cloud "Always Free" server
### Option C (always on, ~₹500/month): Hostinger VPS

Same code, no changes. On an Ubuntu server:

```
sudo apt install -y python3-venv nodejs npm caddy git
git clone https://github.com/xiteai/xos1-terminal-control.git && cd xos1-terminal-control
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd dashboard && npm ci && npm run build && cd ..
cp .env.example .env   # fill it in; TC_COOKIE_SECURE=true, FOUNDER_TOTP_SECRET set
```

A public website must have, in `.env`: `TC_COOKIE_SECURE=true`, `FOUNDER_TOTP_SECRET` set (or the
founder sets one up from Account), `TC_SECRET_KEY` (seals everyone's authenticator seeds; make it
with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
and keep a copy somewhere safe, since losing it means everyone sets their authenticator up again),
and for the Codebase `GITHUB_TOKEN` (fine-grained, Contents read and write, the one repository), for
AI keys `CF_ACCOUNT_ID`, `CF_API_TOKEN` (Secrets Store Write only) and `CF_SECRETS_STORE_ID`.

On GitHub, protect the branch the Codebase follows: Settings → Branches → add a rule for `main`
with **force pushes and deletion blocked**. Then even a stolen token or laptop can't rewrite the
history; the Terminal's history guard is the second lock behind that one.

Run `python run.py` as a systemd service, and put Caddy in front (automatic HTTPS):

```
xtec.xiteai.com {
    reverse_proxy 127.0.0.1:8710
}
```

In Hostinger (or Cloudflare) DNS, add an **A record**: name `xtec`, value = the
server's IP. If you're moving from Option A, copy `data/codebase.db`, `data/installs.db` and
`data/secret.key` across (or set `TC_SECRET_KEY`); everything else is in MongoDB Atlas already.

## 3. Backups

- **MongoDB Atlas** holds people, sessions, tickets, notifications and the audit trail. The free
  tier has no automatic backups: export it now and then (`mongodump` with the connection string,
  or Atlas → Browse Collections → Export).
- **`data/codebase.db`** holds the Codebase's records: grants, features, owners, change requests,
  reviews, comments, checkpoints. Copy it somewhere safe regularly (while the server is stopped,
  or with `sqlite3 data/codebase.db ".backup codebase-backup.db"` while it runs).
- **`data/installs.db`** holds every install and every check-in — the biggest file here, and the
  one that grows fastest. Same backup approach: `sqlite3 data/installs.db ".backup installs-backup.db"`.
- **`data/secret.key`** (unless `TC_SECRET_KEY` is set) unlocks everyone's authenticator. Without
  it, everyone sets their authenticator up again.
- **`data/code/`** is only a copy of GitHub. If it's missing, the server copies it from GitHub
  again on its own. (A merge that never reached GitHub, marked "failed" on its change, would need
  redoing.)
