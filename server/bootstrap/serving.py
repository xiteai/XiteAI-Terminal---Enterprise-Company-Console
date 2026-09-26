"""Holding the port, and serving on it.

Whoever holds the port holds it alone. Windows lets a second socket bind a
port that is already taken unless the first one asked to be exclusive, and
then two servers answer the same link, old code and new at random.

- `python run.py` binds the port itself and serves.
- `python dev.py` holds the port for as long as it runs and serves through a
  child process it restarts on every code change. It hands each child the same
  socket, so a request that arrives mid-restart waits a moment in the queue
  instead of failing. The child stops when dev.py closes its stdin, or when
  dev.py dies (the pipe closes with it), so no server outlives the process
  watching its code.
"""
from __future__ import annotations

import asyncio
import io
import os
import socket
import sys
import threading

import uvicorn

APP = "server.app:app"


def listen(host: str, port: int) -> socket.socket:
    """Bind `port` for this process alone and start queueing connections."""
    sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):       # Windows: nobody binds beside us
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:                                            # POSIX: a restart may rebind past TIME_WAIT
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        sock.close()
        raise
    sock.listen(128)
    return sock


def serve(sock: socket.socket, stop: threading.Event | None = None, shared: bool = False,
          log_level: str = "info") -> None:
    """Serve the app on `sock` until the process is stopped or `stop` is set."""
    server = uvicorn.Server(uvicorn.Config(APP, proxy_headers=True, forwarded_allow_ips="127.0.0.1",
                                           log_level=log_level, timeout_graceful_shutdown=5))
    if stop is not None:
        def _watch() -> None:
            stop.wait()
            server.should_exit = True
        threading.Thread(target=_watch, daemon=True, name="stop-watch").start()
    # A socket handed over from another process can't go through the Proactor loop on Windows.
    factory = asyncio.SelectorEventLoop if shared and sys.platform == "win32" else server.config.get_loop_factory()
    asyncio.run(server.serve(sockets=[sock]), loop_factory=factory)


# ── dev.py's side and the child's side of the handover ────────────────────────

def handoff(sock: socket.socket, pid: int) -> bytes:
    """The line dev.py writes to a child's stdin so it can serve on `sock`."""
    if hasattr(sock, "share"):                       # Windows
        return b"share:" + sock.share(pid).hex().encode() + b"\n"
    return b"fd:%d\n" % sock.fileno()                # POSIX: passed with pass_fds


def _received(line: bytes) -> socket.socket:
    kind, _, value = line.strip().partition(b":")
    if kind == b"share":
        return socket.fromshare(bytes.fromhex(value.decode()))
    if kind == b"fd":
        return socket.socket(fileno=int(value))
    raise SystemExit("serving: expected a socket from dev.py on stdin")


def _take_stdin() -> "io.RawIOBase":
    """The pipe from dev.py becomes this process's private handle, and its
    standard input becomes NUL. The watcher below blocks reading that pipe for
    as long as the server runs, and on Windows any process holding a handle to
    a pipe with a read pending hangs the moment it touches it — every git
    command the server started inherited it and froze. After this, nothing
    the server launches can inherit it: the private copy is non-inheritable
    (PEP 446) and the inheritable original is closed."""
    private = os.fdopen(os.dup(0), "rb", buffering=0)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)                                  # closes the original pipe handle behind fd 0
    os.close(null)
    if sys.platform == "win32":
        import ctypes
        import msvcrt
        ctypes.windll.kernel32.SetStdHandle(-10, msvcrt.get_osfhandle(0))   # STD_INPUT_HANDLE -> NUL
    sys.stdin = open(0, closefd=False)
    return private


def child() -> None:
    """`python -m server.bootstrap.serving`: dev.py's server process."""
    sock = _received(sys.stdin.buffer.readline())
    pipe = _take_stdin()
    stop = threading.Event()

    def _until_stdin_closes() -> None:
        while pipe.read(4096):                       # returns b"" when dev.py closes the pipe, or dies
            pass
        stop.set()
    threading.Thread(target=_until_stdin_closes, daemon=True, name="parent-watch").start()
    serve(sock, stop=stop, shared=True, log_level="warning")


if __name__ == "__main__":
    child()
