"""Turns a stream of individual check-ins into batches, so ten thousand PCs
checking in doesn't mean ten thousand SQLite transactions. One background
thread owns the write path; every request only ever enqueues and waits.

    fut = batcher.submit(payload, public_key_b64, product_id, ip)
    answer = await asyncio.wrap_future(fut)          # raises CheckinError on a bad check-in

A flush happens at CHECKIN_BATCH items, or CHECKIN_BATCH_MS after the first
item in an empty batch arrives — whichever comes first, so one lone check-in
still lands quickly rather than waiting for company. Past CHECKIN_QUEUE_MAX
already waiting, submit() refuses at once (QueueFull, answered 503 upstream):
a flood is turned away before it touches anything, not queued to fail later."""
from __future__ import annotations

import logging
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field

from ...core import audit, config, db
from . import ingest

log = logging.getLogger("terminal.checkin")


@dataclass
class Job:
    payload: dict
    public_key: str
    product_id: int
    ip: str
    at: str
    future: Future = field(default_factory=Future)


class QueueFull(Exception):
    """Too many check-ins are already waiting to be written."""


_q: "queue.Queue[Job]" = queue.Queue()
_started = False
_started_lock = threading.Lock()


def queue_depth() -> int:
    return _q.qsize()


def submit(payload: dict, public_key: str, product_id: int, ip: str) -> Future:
    if _q.qsize() >= config.CHECKIN_QUEUE_MAX:
        raise QueueFull()
    job = Job(payload, public_key, product_id, ip, db.now_iso())
    _q.put(job)
    return job.future


def _collect() -> list[Job]:
    first = _q.get()
    batch = [first]
    deadline = time.monotonic() + config.CHECKIN_BATCH_MS / 1000
    while len(batch) < config.CHECKIN_BATCH:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            batch.append(_q.get(timeout=remaining))
        except queue.Empty:
            break
    return batch


def _run() -> None:
    while True:
        batch = _collect()
        try:
            answers, events = ingest.write([
                {"payload": j.payload, "public_key": j.public_key, "product_id": j.product_id, "ip": j.ip, "at": j.at}
                for j in batch])
        except Exception as e:                        # noqa: BLE001 — the whole batch must not wedge this thread
            log.exception("writing a batch of %d check-ins", len(batch))
            for j in batch:
                if not j.future.done():
                    j.future.set_exception(e)
            continue
        for j, answer in zip(batch, answers):
            if isinstance(answer, Exception):
                j.future.set_exception(answer)
            else:
                j.future.set_result(answer)
        if events:
            try:
                with db.connect() as conn:
                    for action, target, detail, ip in events:
                        audit.record(conn, None, action, target, detail, ip)
            except Exception:                          # noqa: BLE001 — the check-ins themselves are already answered
                log.exception("recording %d check-in audit events", len(events))


def start() -> None:
    global _started
    if _started:
        return
    with _started_lock:
        if _started:
            return
        threading.Thread(target=_run, daemon=True, name="checkin-batcher").start()
        _started = True
