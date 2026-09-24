# Putting XiteAI Terminal online

Two jobs: keep the code on GitHub, and make `xos1dashboard.xiteai.com` reach the app.

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

## 2. The address: xos1dashboard.xiteai.com

### Option A (recommended now, ₹0): the Terminal on your PC + a Cloudflare Tunnel

The Terminal runs on your PC (`python dev.py --autostart on`: it starts with Windows and always
serves the newest code); the tunnel gives it the public address with HTTPS. Nothing to buy.
While your PC is off, the address shows as unreachable; installs keep their check-ins and send
them when it's back.

1. **Move xiteai.com's DNS to Cloudflare (free).** The website stays on Hostinger; only the
   phone book moves.
   - Sign up at cloudflare.com → **Add a site** → `xiteai.com` → Free plan.
   - Cloudflare copies your existing records. **Check the list** before continuing: the `@`
     record (the website), `chat`, `www`, and any `MX`/`TXT` email records must all be there,
     with the same values as in Hostinger's DNS zone.
   - In Hostinger hPanel → **Domains → xiteai.com → DNS / Nameservers → Change nameservers**,
     enter the two nameservers Cloudflare gave you. Takes minutes to a few hours.
2. **Create the tunnel** (on this PC):
   ```
   winget install --id Cloudflare.cloudflared
   cloudflared tunnel login
   cloudflared tunnel create xos1dashboard
   cloudflared tunnel route dns xos1dashboard xos1dashboard.xiteai.com
   ```
   Create `%USERPROFILE%\.cloudflared\config.yml`:
   ```yaml
   tunnel: xos1dashboard
   credentials-file: C:\Users\<you>\.cloudflared\<tunnel-id>.json
   ingress:
     - hostname: xos1dashboard.xiteai.com
       service: http://127.0.0.1:8710
     - service: http_status:404
   ```
   Run it with `cloudflared tunnel run xos1dashboard`, or install it to start with Windows:
   `cloudflared service install`.
3. **Before it's reachable, lock it down.** In `.env`:
   ```
   TC_COOKIE_SECURE=true
   FOUNDER_TOTP_SECRET=<base32 secret>
   ```
   Make the secret with
   `python -c "import base64,secrets;print(base64.b32encode(secrets.token_bytes(20)).decode())"`,
   add it to Google Authenticator (or any authenticator app) as a key. The server picks up the change by itself.
   From then on, signing in as founder also asks for the 6-digit code.
4. Open `https://xos1dashboard.xiteai.com`. The customer page is `/`, the team signs in at
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
xos1dashboard.xiteai.com {
    reverse_proxy 127.0.0.1:8710
}
```

In Hostinger (or Cloudflare) DNS, add an **A record**: name `xos1dashboard`, value = the
server's IP. Copy `data/terminal.db` across if you're moving from Option A.

## 3. Backups

Everything that isn't on GitHub lives in one file: `data/terminal.db` (grants, features, change
requests, the audit trail). Copy it somewhere safe regularly (while the server is stopped, or with
`sqlite3 data/terminal.db ".backup backup.db"` while it runs). `data/code/` is only a copy of
GitHub; if it's missing, the server copies it again from GitHub on its own. (A merge that never
reached GitHub, marked "failed" on its change, would need redoing.)
