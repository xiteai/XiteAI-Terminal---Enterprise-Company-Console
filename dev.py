"""The local link that always shows the newest code:

    http://localhost:8710/console

It starts with Windows, so the link just works. By hand:

    python dev.py                  run it here (if it's already running, it says so and exits)
    python dev.py --autostart on   start it with Windows, and start it now
    python dev.py --autostart off  stop starting it with Windows, and stop it now

Nothing to restart or rebuild by hand. It holds the port and keeps it current:
- server code (server/**/*.py) or .env changes: the server restarts on the same
  socket; a request made during the restart waits a moment, it doesn't fail;
- the screens (dashboard/) change: they're rebuilt beside the live ones and
  swapped in, and a page left open offers Reload;
- the server crashes: it starts again (a broken edit waits for the next save);
- this file, serving.py or freshness.py change: it restarts itself.
One copy runs at a time, an older server on the port is replaced, and if this
process dies its server stops too, so the link is never served by code that
nobody is watching. What it does goes to data/logs/dev.log (the server's own
output to data/logs/dev-server.log).
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from server.bootstrap import freshness, serving  # noqa: E402
from server.core import config  # noqa: E402

URL = f"http://{config.HOST}:{config.PORT}"
LINK = f"http://localhost:{config.PORT}/console"
LOGS = ROOT / "data" / "logs"
SHORTCUT = (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            / "XOS1 Terminal (local).lnk")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
SELF = [ROOT / "dev.py", ROOT / "server" / "bootstrap" / "serving.py", ROOT / "server" / "bootstrap" / "freshness.py"]
log = logging.getLogger("dev")


def _setup_logging() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S")
    handlers: list[logging.Handler] = [RotatingFileHandler(LOGS / "dev.log", maxBytes=1_000_000, backupCount=1,
                                                           encoding="utf-8")]
    if sys.stdout is not None:                     # run by hand: show it here too
        handlers.append(logging.StreamHandler(sys.stdout))
    for h in handlers:
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def _code() -> dict[Path, int]:
    """What the server runs: a change to any of these restarts it."""
    files = [p for p in (ROOT / "server").rglob("*.py") if "__pycache__" not in p.parts] + [ROOT / ".env"]
    return {p: p.stat().st_mtime_ns for p in files if p.exists()}


def _python() -> str:
    """The console build of Python, run without a window, so the server's output reaches its log."""
    console = Path(sys.executable).with_name("python.exe")
    return str(console) if console.exists() else sys.executable


class Server:
    """The server process, serving on the socket this process holds."""

    def __init__(self, sock) -> None:
        self.sock, self.proc, self.started, self.crashes, self.retry_at = sock, None, 0.0, 0, 0.0

    def start(self) -> None:
        out_path = LOGS / "dev-server.log"
        if out_path.exists() and out_path.stat().st_size > 2_000_000:
            os.replace(out_path, out_path.with_suffix(".log.1"))
        extra = {} if hasattr(self.sock, "share") else {"pass_fds": (self.sock.fileno(),)}
        with open(out_path, "ab") as out:
            self.proc = subprocess.Popen([_python(), "-m", "server.bootstrap.serving"], cwd=ROOT,
                                         env=dict(os.environ, TC_LIVE="1", PYTHONUNBUFFERED="1"),
                                         stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                         creationflags=NO_WINDOW, **extra)
        self.proc.stdin.write(serving.handoff(self.sock, self.proc.pid))
        self.proc.stdin.flush()
        self.started = time.time()
        log.info("server started (pid %s)", self.proc.pid)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()            # its cue to finish what it's doing and exit
            except OSError:
                pass
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None

    def check(self) -> None:
        """Start it again if it died on its own, backing off while it keeps dying."""
        if self.proc is None or self.proc.poll() is None:
            if self.proc is None and self.retry_at and time.time() >= self.retry_at:
                self.retry_at = 0.0
                self.start()
            return
        lived = time.time() - self.started
        self.crashes = 1 if lived > 60 else self.crashes + 1
        wait = min(2 ** self.crashes, 60)
        log.error("server stopped by itself (exit %s after %.0f s); starting again in %s s (log: %s)",
                  self.proc.returncode, lived, wait, LOGS / "dev-server.log")
        self.proc, self.retry_at = None, time.time() + wait

    def restart(self) -> None:
        self.stop()
        self.crashes, self.retry_at = 0, 0.0
        self.start()


def _build_ui() -> bool:
    log.info("screens changed: rebuilding them")
    result = freshness.build_ui()
    (log.info if result == "rebuilt" else log.error)("screens: %s", result)
    return result == "rebuilt"


def _bind():
    for attempt in range(40):                      # a server that just stopped may take a moment to let go
        try:
            return serving.listen(config.HOST, config.PORT)
        except OSError:
            if attempt == 39:
                raise
            time.sleep(0.5)


def _restart_self(server: Server, sock) -> None:
    log.info("dev.py itself changed: restarting it")
    server.stop()
    sock.close()
    subprocess.Popen([sys.executable, str(ROOT / "dev.py")], cwd=ROOT, creationflags=DETACHED, close_fds=True)


def run() -> int:
    try:
        state = freshness.take_over(URL, config.PORT, keep_same=False)
    except SystemExit as e:
        log.error("%s", e)
        return 1
    if state == "live":
        log.info("already running: %s", LINK)
        return 0
    if state == "replaced":
        log.info("stopped an older server that was holding port %s", config.PORT)
    try:
        sock = _bind()
    except OSError as e:
        if (freshness.running(URL) or {}).get("live"):
            log.info("already running: %s", LINK)   # another copy started at the same moment
            return 0
        log.error("couldn't take port %s: %s", config.PORT, e)
        return 1

    # The port is ours and queueing: a page opened now waits for the newest screens, never the old ones.
    if freshness.ui_is_stale():
        _build_ui()
    server = Server(sock)
    server.start()
    log.info("serving the newest code at %s", LINK)

    seen, own = _code(), {p: p.stat().st_mtime_ns for p in SELF}
    failed_ui = None
    try:
        while True:
            time.sleep(1)
            if {p: p.stat().st_mtime_ns for p in SELF if p.exists()} != own:
                time.sleep(0.5)
                _restart_self(server, sock)
                return 0
            now = _code()
            if now != seen:
                time.sleep(0.5)                    # let a burst of saves land, then restart once
                now = _code()
                changed = sorted(str(p.relative_to(ROOT)) for p in set(now) | set(seen) if now.get(p) != seen.get(p))
                seen = now
                log.info("code changed (%s): restarting the server", ", ".join(changed[:4]))
                server.restart()
                continue
            server.check()
            if freshness.ui_is_stale():
                newest = freshness.newest_source()
                if newest != failed_ui and time.time() - newest > 1:
                    failed_ui = None if _build_ui() else newest   # a broken build waits for the next save
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        server.stop()
        sock.close()
    return 0


# ── starting with Windows ─────────────────────────────────────────────────────

def _stop_running() -> list[int]:
    stopped = []
    for proc in freshness._listeners(config.PORT):
        try:
            if "dev.py" in " ".join(proc.cmdline()):
                proc.terminate()                   # its server stops with it
                proc.wait(timeout=10)
                stopped.append(proc.pid)
        except Exception:
            pass
    return stopped


def autostart(on: bool) -> int:
    if sys.platform != "win32":
        print("Starting with the system is set up for Windows only. Run `python dev.py` instead.")
        return 1
    if not on:
        SHORTCUT.unlink(missing_ok=True)
        stopped = _stop_running()
        print("It won't start with Windows any more" + (", and it's stopped now." if stopped else "."))
        return 0
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    script = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:TC_LNK); "
              "$s.TargetPath = $env:TC_TARGET; $s.Arguments = $env:TC_ARGS; $s.WorkingDirectory = $env:TC_DIR; "
              "$s.Description = 'Keeps the XOS1 Terminal link serving the newest code'; $s.Save()")
    SHORTCUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], check=True,
                   capture_output=True, creationflags=NO_WINDOW,
                   env=dict(os.environ, TC_LNK=str(SHORTCUT), TC_DIR=str(ROOT), TC_ARGS=f'"{ROOT / "dev.py"}"',
                            TC_TARGET=str(pythonw if pythonw.exists() else sys.executable)))
    os.startfile(SHORTCUT)                         # and start it now, exactly as Windows will
    for _ in range(120):
        if (freshness.running(URL) or {}).get("live"):
            print(f"Running, and it starts with Windows from now on: {LINK}")
            return 0
        time.sleep(0.5)
    print(f"It starts with Windows now, but didn't answer yet. See {LOGS / 'dev.log'}")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The local XOS1 Terminal link that always shows the newest code.")
    ap.add_argument("--autostart", choices=["on", "off"], help="start with Windows (and now), or stop that")
    args = ap.parse_args()
    if args.autostart:
        raise SystemExit(autostart(args.autostart == "on"))
    _setup_logging()
    raise SystemExit(run())
