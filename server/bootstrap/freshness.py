"""Why an update can look like it did nothing, and what closes each case.

1. A server from before the update is still running and holding the port. A
   new launch then can't bind, and the page quietly shows the OLD server (this
   happened: a `run.py` from the night before hid a whole day's work). Every
   server reports a BUILD id (a hash of its code and its UI build); a launch
   that finds another build on the port stops that server first. A server run
   by dev.py reports itself LIVE: it follows the code on its own, so it is left
   alone. Nothing binds beside a running server (serving.listen).
2. The UI build (dashboard/dist) is older than its source: rebuilt first,
   beside the live one, then swapped in (build_ui).
3. A page left open across an update: it notices the new UI build and offers a
   reload (dashboard/src/components/UpdateNotice.jsx).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..core import config

log = logging.getLogger("terminal.freshness")
ROOT = config.ROOT
DASH = config.DASHBOARD_DIR
DIST = DASH / "dist"
DIST_INDEX = DIST / "index.html"
LIVE = os.environ.get("TC_LIVE") == "1"          # set by dev.py for the server it runs
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OLD_ASSETS_KEEP_S = 3600                          # a page open from before may still load its chunks


def _code_files() -> list[Path]:
    return sorted(p for p in (ROOT / "server").rglob("*.py") if "__pycache__" not in p.parts)


def compute_build() -> str:
    """What this checkout would serve: every server file, and the UI build."""
    h = hashlib.sha1()
    for p in _code_files() + ([DIST_INDEX] if DIST_INDEX.exists() else []):
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


_BUILD: str | None = None


def build() -> str:
    """The build THIS server started with: pinned by startup.run(), reported by
    /api/public/status, compared by a launcher with compute_build() on disk.
    Pinned at start, so a server running for days can't pass for the new code."""
    global _BUILD
    if _BUILD is None:
        _BUILD = compute_build()
    return _BUILD


# ── 2. the UI build ───────────────────────────────────────────────────────────

def ui_sources() -> list[Path]:
    paths = [DASH / "index.html", DASH / "package.json", DASH / "vite.config.js"]
    paths += [p for p in (DASH / "src").rglob("*") if p.is_file()]
    paths += [p for p in (DASH / "public").rglob("*") if p.is_file()] if (DASH / "public").is_dir() else []
    return [p for p in paths if p.exists()]


def newest_source() -> float:
    return max((p.stat().st_mtime for p in ui_sources()), default=0.0)


def ui_is_stale() -> bool:
    return not DIST_INDEX.exists() or newest_source() > DIST_INDEX.stat().st_mtime


def ensure_ui() -> str:
    """Rebuild the UI if its source is newer than the build. Returns what happened."""
    return build_ui() if ui_is_stale() else "fresh"


def build_ui() -> str:
    """Build the screens into a folder beside dist/, then swap them in: a page
    loading mid-build never gets a half-written dist/, and a page already open
    can still load the chunks it was built with. 'rebuilt', or why not."""
    npm = shutil.which("npm")
    if not npm:
        return "stale (npm not found: install Node.js, then run `npm run build` in dashboard/)"
    if not (DASH / "node_modules").is_dir():
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=DASH, capture_output=True, timeout=900,
                       creationflags=NO_WINDOW)
    new = DASH / f".dist-next-{os.getpid()}"
    shutil.rmtree(new, ignore_errors=True)
    try:
        p = subprocess.run([npm, "run", "build", "--", "--outDir", new.name, "--emptyOutDir"], cwd=DASH,
                           capture_output=True, timeout=600, creationflags=NO_WINDOW)
        if p.returncode != 0 or not (new / "index.html").exists():
            out = (p.stderr or p.stdout).decode("utf-8", "replace").strip()
            return f"build failed: {out[-600:]}"
        _swap_in(new)
        return "rebuilt"
    finally:
        shutil.rmtree(new, ignore_errors=True)


def _replace(src: Path, dst: Path) -> None:
    for attempt in range(20):             # the server may have the file open for a moment (Windows)
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def _swap_in(new: Path) -> None:
    fresh = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
    for rel in sorted(fresh):
        if rel != Path("index.html"):     # new hashed files first: they don't collide with the live ones
            (DIST / rel).parent.mkdir(parents=True, exist_ok=True)
            _replace(new / rel, DIST / rel)
    _replace(new / "index.html", DIST_INDEX)  # the switch
    cutoff = time.time() - OLD_ASSETS_KEEP_S
    for old in (DIST / "assets").glob("*"):
        if old.is_file() and Path("assets", old.name) not in fresh and old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)


# ── 1. an old server on the port ──────────────────────────────────────────────

def running(url: str) -> dict | None:
    """What answers on `url`: a Terminal server's status, {} for something
    else, or None when nothing is listening."""
    try:
        with urllib.request.urlopen(f"{url}/api/public/status", timeout=3) as r:
            data = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError:
        return {}
    except OSError:
        return None
    except ValueError:
        return {}
    return data if isinstance(data, dict) and "product" in data else {}


def _listeners(port: int) -> list:
    import psutil

    found = []
    for c in psutil.net_connections(kind="tcp"):
        if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port and c.pid:
            try:
                found.append(psutil.Process(c.pid))
            except psutil.Error:
                pass
    return found


def stop_listener(port: int) -> list[int]:
    """Stop the process listening on `port` (only called after it answered as a
    Terminal server of another build). Returns the stopped PIDs."""
    import psutil

    stopped = []
    for proc in _listeners(port):
        try:
            log.warning("stopping an older Terminal server on port %s: pid %s (%s)", port, proc.pid,
                        " ".join(proc.cmdline())[:200])
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except psutil.TimeoutExpired:
                proc.kill()
            stopped.append(proc.pid)
        except psutil.Error:
            pass
    return stopped


def take_over(url: str, port: int, keep_same: bool = True) -> str:
    """Before starting a server on `port`:
    'free'     nothing is there: start it;
    'live'     dev.py is serving it, and it follows the code by itself;
    'same'     this build is already serving (unless keep_same=False: then it is replaced);
    'replaced' an older server was stopped."""
    found = running(url)
    if found is None:
        return "free"
    if not found:
        who = ", ".join(f"{p.name()} (pid {p.pid})" for p in _listeners(port)) or "another program"
        raise SystemExit(f"Port {port} is used by {who}, not by the Terminal. Close it, or set TC_PORT in .env.")
    if found.get("live"):
        return "live"
    if keep_same and found.get("build") == compute_build():
        return "same"
    stop_listener(port)
    for _ in range(40):
        if running(url) is None:
            return "replaced"
        time.sleep(0.25)
    raise SystemExit(f"An older server is still holding port {port} and wouldn't stop. Close it, or restart the PC.")


if __name__ == "__main__":                # python -m server.bootstrap.freshness: rebuild the screens safely
    print(build_ui())
