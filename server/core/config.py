"""Everything the server reads from .env, in one place.

Passwords live ONLY in .env (gitignored). The database stores a scrypt hash of
each, never the password itself; the founder's hash is re-synced from .env on
every start, so rotating the founder password is: edit .env, restart.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(_str(name) or default)
    except ValueError:
        return default


# ── Identity ──────────────────────────────────────────────────────────────────
APP_NAME = "XiteAI Terminal"
# Where this is served from, for sitemap and link-preview URLs.
PUBLIC_BASE_URL = _str("TC_PUBLIC_BASE_URL", "https://xtec.xiteai.com")
COMPANY = _str("TC_COMPANY", "XiteAI Technologies")
PRODUCT = _str("TC_PRODUCT", "XOS1")
PRODUCT_FULL = _str("TC_PRODUCT_FULL", "XiteAI OS1")
EMAIL_DOMAIN = _str("TC_EMAIL_DOMAIN", "xos1.com").lstrip("@").lower()

# ── Server ────────────────────────────────────────────────────────────────────
HOST = _str("TC_HOST", "127.0.0.1")
PORT = _int("TC_PORT", 8710)
DATA_DIR = ROOT / "data"                              # this app's own local files: secret.key, code, backups, logs
DASHBOARD_DIR = ROOT / "dashboard"
SESSION_HOURS = _int("TC_SESSION_HOURS", 12)
COOKIE_SECURE = _bool("TC_COOKIE_SECURE", False)      # true once served over HTTPS

# ── MongoDB Atlas: every table lives in one database on the shared cluster ──
MONGO_CLUSTER = _str("MONGO_CLUSTER")
MONGO_DB_PASSWORD = _str("MONGO_DB_PASSWORD")
MONGO_URI = _str("MONGO_URI")                          # a full URI wins over CLUSTER/PASSWORD (tests only)
MONGO_DB_NAME = _str("TC_MONGO_DB_NAME", "xiteai_terminal")   # tests point this at a throwaway name
MONGO_POOL_SIZE = _int("MONGO_POOL_SIZE", 20)
# Who answers "where is the cluster": the mongodb+srv:// lookup goes to these,
# not to whatever the network hands out. Measured on this PC's Wi-Fi, the ISP's
# DNS took up to 8.7 s and failed 1 lookup in 5; 1.1.1.1 / 8.8.8.8 took ~130 ms
# and never failed. Empty = use the system's DNS.
MONGO_DNS = [s.strip() for s in _str("MONGO_DNS", "1.1.1.1,8.8.8.8,1.0.0.1,8.8.4.4").split(",") if s.strip()]

# ── The founder (top of the hierarchy) ────────────────────────────────────────
FOUNDER_EMAIL_RAW = _str("FOUNDER_EMAIL")
FOUNDER_PASSWORD = os.getenv("FOUNDER_PASSWORD", "")
FOUNDER_DISPLAY_NAME = _str("FOUNDER_DISPLAY_NAME", "Founder")
FOUNDER_TITLE = _str("FOUNDER_TITLE", "Founder & CEO")
FOUNDER_TOTP_SECRET = _str("FOUNDER_TOTP_SECRET").replace(" ", "")   # empty = no second step
SEED_STAFF = _str("SEED_STAFF")     # level:email:password:Full Name[:Title]; several separated by ';'

# ── Protection ────────────────────────────────────────────────────────────────
LOCKOUT_FAILS_PER_USER = _int("TC_LOCKOUT_FAILS_PER_USER", 5)
LOCKOUT_FAILS_PER_IP = _int("TC_LOCKOUT_FAILS_PER_IP", 20)
LOCKOUT_WINDOW_MIN = _int("TC_LOCKOUT_WINDOW_MIN", 15)
JOIN_REQUESTS_PER_HOUR = _int("TC_JOIN_REQUESTS_PER_HOUR", 5)
PUBLIC_TICKETS_PER_HOUR = _int("TC_PUBLIC_TICKETS_PER_HOUR", 5)
CHECKIN_MAX_SKEW_MIN = _int("TC_CHECKIN_MAX_SKEW_MIN", 10)

# ── Installs and their check-ins: a local SQLite file on the server ─────────
# The busiest data there is (every install, every check-in), kept on the
# server's own disk rather than in Atlas's quota. See features/installs/store.py.
INSTALLS_DB_PATH = ROOT / _str("TC_INSTALLS_DB_PATH", "data/installs.db")
# Check-ins are written in batches by one writer: up to BATCH at a time, or
# whatever arrived within BATCH_MS of the first. Past QUEUE_MAX waiting, new
# ones are told to come back later (503 + Retry-After) instead of piling up.
CHECKIN_BATCH = _int("TC_CHECKIN_BATCH", 1000)
CHECKIN_BATCH_MS = _int("TC_CHECKIN_BATCH_MS", 200)
CHECKIN_QUEUE_MAX = _int("TC_CHECKIN_QUEUE_MAX", 50000)
# One machine (with one key) checking in more often than this is a client bug
# looping; it's answered 429 without touching the database.
CHECKIN_MIN_INTERVAL_S = _int("TC_CHECKIN_MIN_INTERVAL_S", 60)

# ── Clock the console shows (day buckets, heatmap) ───────────────────────────
DISPLAY_UTC_OFFSET = _str("TC_DISPLAY_UTC_OFFSET", "+05:30")
DISPLAY_TZ_LABEL = _str("TC_DISPLAY_TZ_LABEL", "IST")

# ── Demo data (marked in the UI; the founder removes it in one click) ─────────
DEMO_DATA = _bool("TC_DEMO_DATA", True)

# ── Product facts for the public customer page ───────────────────────────────
LATEST_VERSION = _str("XOS1_LATEST_VERSION", "1.0.17")
RELEASE_NOTES_DIR = _str("XOS1_RELEASE_NOTES_DIR")
DOWNLOAD_URL = _str("XOS1_DOWNLOAD_URL", "https://github.com/SURAj-Verma-ai/ella-zero-releases/releases/latest")
SUPPORT_EMAIL = _str("TC_SUPPORT_EMAIL")

# ── AI keys live in Cloudflare Secrets Store, never here ─────────────────────
# CF_API_TOKEN needs exactly one permission: Secrets Store Write. It can put a
# key in; it can't read one back or touch the Worker's code.
CF_ACCOUNT_ID = _str("CF_ACCOUNT_ID")
CF_API_TOKEN = _str("CF_API_TOKEN")
CF_SECRETS_STORE_ID = _str("CF_SECRETS_STORE_ID")

# ── The vault ─────────────────────────────────────────────────────────────────
# 32 bytes, base64. Encrypts provider API keys at rest so the app never carries
# one: XOS1 asks this server to make the call, the key stays here.
#   python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
VAULT_KEY = _str("TC_VAULT_KEY")
# The model gateway: what one machine may ask for, and how big an answer can be.
GATEWAY_PER_MIN = _int("TC_GATEWAY_PER_MIN", 20)         # requests per device per minute
GATEWAY_MAX_BODY_KB = _int("TC_GATEWAY_MAX_BODY_KB", 256)
GATEWAY_TIMEOUT_S = _int("TC_GATEWAY_TIMEOUT_S", 120)

# ── Check-in pacing ───────────────────────────────────────────────────────────
# The server tells each install when to come back, rather than every install
# deciding for itself: that's what stops ten thousand PCs arriving together
# after an outage. The spread is derived from the machine's own hash, so a
# given machine always lands in the same slot instead of jittering about.
CHECKIN_EVERY_S = _int("TC_CHECKIN_EVERY_S", 6 * 3600)
CHECKIN_SPREAD_S = _int("TC_CHECKIN_SPREAD_S", 3600)

# ── Codebase ──────────────────────────────────────────────────────────────────
# A fine-grained GitHub token with Contents: Read and write on the connected
# repository only. Sent as a header per git command; never written to disk.
GITHUB_TOKEN = _str("GITHUB_TOKEN")
CODE_DIR = ROOT / _str("TC_CODE_DIR", "data/code")
# The Codebase's records (repositories, grants, change requests, reviews): a
# local SQLite file, not MongoDB. See server/features/code/store.py for why.
CODE_DB_PATH = ROOT / _str("TC_CODE_DB_PATH", "data/codebase.db")
# Code and text only: anything bigger, or binary, is never opened or accepted.
CODE_MAX_FILE_KB = _int("TC_CODE_MAX_FILE_KB", 1024)
CODE_MAX_CHANGE_MB = _int("TC_CODE_MAX_CHANGE_MB", 5)
CODE_MAX_FILES = _int("TC_CODE_MAX_FILES", 50)
CODE_COMMITTER_NAME = _str("TC_CODE_COMMITTER_NAME", "XiteAI Terminal")
CODE_COMMITTER_EMAIL = _str("TC_CODE_COMMITTER_EMAIL", "terminal@xos1.com")
CODE_SYNC_MIN = _int("TC_CODE_SYNC_MIN", 5)            # follow GitHub this often; 0 = only on demand
# The reading alarm, per person per hour: tell the founder at ALERT, close the
# codebase to them at PAUSE until the founder resumes it. Distinct files opened,
# and searches run. The founder is never paused.
CODE_ALERT_FILES_HOUR = _int("TC_CODE_ALERT_FILES_HOUR", 40)
CODE_PAUSE_FILES_HOUR = _int("TC_CODE_PAUSE_FILES_HOUR", 120)
CODE_ALERT_SEARCHES_HOUR = _int("TC_CODE_ALERT_SEARCHES_HOUR", 150)
CODE_PAUSE_SEARCHES_HOUR = _int("TC_CODE_PAUSE_SEARCHES_HOUR", 400)
CODE_ALLOW_LOCAL = _bool("TC_CODE_ALLOW_LOCAL", False)  # accept a local path as the remote (tests only)
# A full offline copy of every repository's history, once a day, newest kept.
# Restores with `git clone <file>` even if GitHub is gone. 0 turns it off.
CODE_BACKUP_DIR = ROOT / _str("TC_CODE_BACKUP_DIR", "data/backups")
CODE_BACKUPS_KEEP = _int("TC_CODE_BACKUPS_KEEP", 3)

# ── Workplace ─────────────────────────────────────────────────────────────────
# What the team files against the company: leave, expenses, asset requests,
# helpdesk tickets and payslips. Relational and busy, so a local SQLite file
# rather than MongoDB. See server/features/workplace/store.py.
WORKPLACE_DB_PATH = ROOT / _str("TC_WORKPLACE_DB_PATH", "data/workplace.db")
# A year's leave, in days, before anyone files anything. Unpaid leave is uncapped.
LEAVE_DAYS_ANNUAL = _int("TC_LEAVE_DAYS_ANNUAL", 21)      # a competitive number for Indian tech, not the legal floor
LEAVE_DAYS_SICK = _int("TC_LEAVE_DAYS_SICK", 10)
LEAVE_DAYS_CASUAL = _int("TC_LEAVE_DAYS_CASUAL", 7)
LEAVE_DAYS_PATERNITY = _int("TC_LEAVE_DAYS_PATERNITY", 15)
LEAVE_DAYS_BEREAVEMENT = _int("TC_LEAVE_DAYS_BEREAVEMENT", 5)
# The most one expense claim may be for, in rupees.
EXPENSE_MAX_RUPEES = _int("TC_EXPENSE_MAX_RUPEES", 200000)


def work_email(value: str) -> str:
    """'suraj' or 'Suraj@XOS1.com' -> 'suraj@xos1.com'."""
    value = (value or "").strip().lower()
    return value if "@" in value else f"{value}@{EMAIL_DOMAIN}"


FOUNDER_EMAIL = work_email(FOUNDER_EMAIL_RAW) if FOUNDER_EMAIL_RAW else ""
