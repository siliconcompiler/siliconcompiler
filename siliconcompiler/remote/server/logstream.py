'''
Tailing a node that is still running.

The bytes come off the shared filesystem, because that is where the run is
already writing them: the compute node holds no database connection and makes no
HTTP request, so a log reaching a client is a file being read by whichever
process is serving the API. That is the same property the progress file rests
on, and it is what lets the two be different machines.

🔴 **The event ``id`` is the byte offset the reader reached**, which is what
makes ``Last-Event-ID`` resumption exact rather than approximate: a client that
reconnects hands back the offset it had, and the next read starts there. A
line-number or a timestamp would both need the server to remember something
about that client, and a stream host that remembers callers is one that cannot
be restarted.

⚠️ **Deliberately not a live tail of the *tool's* stdout.** What is streamed is
``sc_<step>_<index>.log``, the same file the archived ``logs`` artifact holds, so
the tail and the download are the same bytes. A client that tails to the end and
then fetches the artifact sees no seam.
'''

import json
import logging
import time

from pathlib import Path
from typing import Iterator, Optional

__all__ = ["events", "job_events", "resume_from", "resume_job",
           "TERMINAL_NODE_STATES", "POLL_SECONDS", "RETRY_MS"]


logger = logging.getLogger("sc-server")


# A node's closed set, repeated here rather than imported, because this module
# is about files and must not depend on the job model.
TERMINAL_NODE_STATES = frozenset(("completed", "failed", "skipped", "cancelled"))

# How often the file is looked at while it is quiet. Short enough that a tail
# feels live, long enough that a hundred idle streams are not a hundred stats a
# second.
POLL_SECONDS = 0.5

# What the client is told to wait before reconnecting, per the SSE `retry`
# field. The client re-requests /logs rather than reusing the target, so this
# paces a re-authorization rather than a bare reconnect.
RETRY_MS = 2000

# Never emit an event larger than this. A node that writes a megabyte in one
# burst becomes several events rather than one that no reader can buffer.
MAX_CHUNK = 64 * 1024

# Sent while the log is silent, so that a connection nothing is writing to is
# still visibly alive. A comment rather than an event: SSE ignores it, and it
# costs a client nothing to receive.
HEARTBEAT_SECONDS = 15


def events(path: Path, step: str, index: str, node_state, start: int,
           deadline: float, artifact_id=None) -> Iterator[bytes]:
    '''Yield SSE frames for one node's log until it ends or time runs out.

    ``node_state`` is called to ask what the node is doing now -- a callable
    rather than a value, because the answer changes underneath a stream that may
    run for hours. ``deadline`` is when this capability expires; reaching it
    ends the stream cleanly so the client re-requests ``/logs`` and gets a fresh
    authorization, which is the whole reason the URL has its own lifetime.
    '''
    offset = max(0, int(start))
    pending = b""
    last_sent = time.monotonic()

    yield f"retry: {RETRY_MS}\n\n".encode()

    while True:
        size = _size(path)

        if size < offset:
            # The file got smaller, so the offset a client handed back points
            # at bytes that are no longer there. Starting over is the only
            # honest answer; silently seeking to the end would drop a log.
            logger.warning(f"{path} shrank under a reader; restarting the tail")
            offset, pending = 0, b""

        if size > offset:
            chunk, offset = _read(path, offset, MAX_CHUNK)
            pending += chunk

            text, pending = _split(pending, complete=False)
            if text:
                yield _event("log", {
                    "step": step, "index": index, "stream": "stdout",
                    "ts": _now(), "text": text,
                }, identifier=format(offset - len(pending), "x"))
                last_sent = time.monotonic()
            continue

        state = node_state()

        if state in TERMINAL_NODE_STATES:
            # Drain whatever is left, including a final line with no newline on
            # it: the run is over, so there is nothing more coming to complete
            # it.
            text, pending = _split(pending, complete=True)
            if text:
                yield _event("log", {
                    "step": step, "index": index, "stream": "stdout",
                    "ts": _now(), "text": text,
                }, identifier=format(offset, "x"))

            yield _event("node_state", _with_artifact(
                {"step": step, "index": index, "state": state}, artifact_id()))
            yield _event("end", _with_artifact(
                {"reason": "terminal"}, artifact_id()))
            return

        if time.monotonic() >= deadline:
            # Not an error and not the end of the log: this capability is over.
            # The client re-requests /logs and resumes from its last id.
            yield _event("end", {"reason": "expired"})
            return

        if time.monotonic() - last_sent >= HEARTBEAT_SECONDS:
            yield b": keep-alive\n\n"
            last_sent = time.monotonic()

        time.sleep(POLL_SECONDS)


def job_events(nodes, path_of, node_states, job_over, start, deadline,
               artifact_id) -> Iterator[bytes]:
    '''Yield SSE frames for every node of a job, merged, until it ends.

    ``nodes`` is the job's node list in a fixed order -- the store's -- because
    the event id is a vector over it. ``path_of(step, index)`` is where a node's
    log is, ``node_states()`` what every node is doing now, ``job_over()``
    whether the job is terminal, and ``artifact_id(step, index)`` a node's
    archived log once there is one.

    🔴 **The id is job-wide, and that is the rule a merge gets wrong.** A
    per-node id is a byte offset in ONE file, and resuming a merged stream from
    one of those would start every other node at a position that is not its
    own. So the id carries every node's position, led by the total delivered,
    which strictly increases with every `log` event: it is a position in the
    job, it is monotonic, and handing it back needs this server to remember
    nothing about the caller.

    ⚠️ **Sparse** (D108): `<total>-<slot>:<offset>.<slot>:<offset>...` in hex,
    naming only the nodes that have emitted something, by their place in the
    job's fixed node order. `Last-Event-ID` travels as a request header, and a
    dense vector over `max_job_nodes` of them can pass what common proxies
    accept for one.

    Ordering is kept within a node and is arrival order across them: each pass
    takes what every node has written since the last, node by node.

    ⚠️ **A job already over when the stream opens gets `end` at once**, with
    nothing replayed. It is the same answer as a job that ends between the
    `303` and the connect, so the late request and the race are one path, and
    the client reads the listing for `kind=logs`. `end` names no artifact on a
    job stream: there is no single archive, and each node's `node_state`
    already named its own.
    '''
    count = len(nodes)
    offsets = list(start) if len(start) == count else [0] * count
    pending = [b""] * count
    reported = [False] * count
    last_sent = time.monotonic()

    yield f"retry: {RETRY_MS}\n\n".encode()

    if job_over():
        yield _event("end", {"reason": "terminal"})
        return

    while True:
        progressed = False
        states = node_states()

        for slot, (step, index) in enumerate(nodes):
            if reported[slot]:
                continue

            path = path_of(step, index)
            size = _size(path)

            if size < offsets[slot]:
                logger.warning(f"{path} shrank under a reader; restarting its tail")
                offsets[slot], pending[slot] = 0, b""

            if size > offsets[slot]:
                chunk, offsets[slot] = _read(path, offsets[slot], MAX_CHUNK)
                pending[slot] += chunk
                text, pending[slot] = _split(pending[slot], complete=False)
                if text:
                    yield _log(step, index, text, _job_id(offsets, pending))
                    last_sent = time.monotonic()
                progressed = True
                continue

            state = states.get((step, index))
            if state in TERMINAL_NODE_STATES:
                text, pending[slot] = _split(pending[slot], complete=True)
                if text:
                    yield _log(step, index, text, _job_id(offsets, pending))

                yield _event("node_state", _with_artifact(
                    {"step": step, "index": index, "state": state},
                    artifact_id(step, index)))
                reported[slot] = True
                progressed = True

        if all(reported) or (not progressed and job_over()):
            yield _event("end", {"reason": "terminal"})
            return

        # Checked on a busy pass too: a job whose nodes never go quiet would
        # otherwise hold a capability past its lifetime. The client resumes
        # from the last id either way.
        if time.monotonic() >= deadline:
            yield _event("end", {"reason": "expired"})
            return

        if progressed:
            continue

        if time.monotonic() - last_sent >= HEARTBEAT_SECONDS:
            yield b": keep-alive\n\n"
            last_sent = time.monotonic()

        time.sleep(POLL_SECONDS)


def _log(step: str, index: str, text: str, identifier: str) -> bytes:
    return _event("log", {"step": step, "index": index, "stream": "stdout",
                          "ts": _now(), "text": text}, identifier=identifier)


def _job_id(offsets, pending) -> str:
    '''Where every node that has said anything has been delivered up to, led
    by the total -- sparse, so the header stays short on a wide flow.'''
    delivered = [offset - len(held) for offset, held in zip(offsets, pending)]
    return f"{sum(delivered):x}-" + ".".join(
        f"{slot:x}:{at:x}" for slot, at in enumerate(delivered) if at)


def resume_job(header: Optional[str], fallback, count: int):
    '''Every node's offset out of a job stream's id, or all zeros.

    ⚠️ An id with the wrong number of nodes, or a per-node id handed to the job
    stream, starts from the beginning: it is not a position in THIS job, and a
    stream that replays is a nuisance where one that skips is a lost log.
    '''
    for candidate in (header, fallback):
        if not candidate:
            continue
        total, dash, vector = str(candidate).partition("-")
        offsets = [0] * count
        try:
            if not dash:
                raise ValueError("no position")
            for pair in (vector.split(".") if vector else []):
                slot, colon, at = pair.partition(":")
                if not colon:
                    raise ValueError("not a slot:offset pair")
                slot, at = int(slot, 16), int(at, 16)
                if not 0 <= slot < count or at < 0 or offsets[slot]:
                    raise ValueError("not a slot of this job")
                offsets[slot] = at
            if sum(offsets) == int(total, 16):
                return offsets
        except ValueError:
            pass
        logger.debug(f"ignoring a Last-Event-ID that is not this job's: {candidate!r}")
    return [0] * count


def _with_artifact(body: dict, artifact) -> dict:
    '''`artifact_id` is present once there is one to name.

    A node can be terminal a moment before its log has been indexed, and an
    explicit null would claim there will never be one.
    '''
    if artifact:
        body["artifact_id"] = artifact
    return body


def _event(name: str, body: dict, identifier: Optional[str] = None) -> bytes:
    frame = f"event: {name}\n"
    if identifier is not None:
        # 🔴 Only `log` events carry an id, because only they are a position a
        # client can resume from. An id on `end` would have a reconnect ask to
        # continue from the end of the stream.
        frame += f"id: {identifier}\n"
    frame += f"data: {json.dumps(body, separators=(',', ':'))}\n\n"
    return frame.encode()


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        # Not written yet. A node can be dispatched before it opens its log,
        # and waiting is the right answer rather than ending the stream.
        return 0


def _read(path: Path, offset: int, limit: int):
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(limit)
    except OSError as e:
        logger.debug(f"could not read {path}: {e}")
        return b"", offset
    return data, offset + len(data)


def _split(buffer: bytes, complete: bool):
    '''Whole lines out of the buffer, and what is left over.

    An event never carries half a line while more is coming: a reader that
    prints what it is given would otherwise show a line in two pieces, and a
    line is the unit a person reads a log in.
    '''
    if complete:
        return _decode(buffer), b""

    cut = buffer.rfind(b"\n")
    if cut < 0:
        return "", buffer
    return _decode(buffer[:cut + 1]), buffer[cut + 1:]


def _decode(raw: bytes) -> str:
    # A tool's output is whatever the tool wrote, which is not always UTF-8 and
    # is never worth failing a stream over.
    return raw.decode("utf-8", errors="replace")


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def resume_from(header: Optional[str], fallback) -> int:
    '''Where to start, given what the client handed back.

    `Last-Event-ID` is the SSE mechanism and a query parameter is the fallback,
    because a browser's EventSource sends the header and a plain fetch cannot
    always set one. Anything unreadable starts from the beginning: a stream that
    replays is a nuisance, and one that silently skips is a lost log.
    '''
    for candidate in (header, fallback):
        if not candidate:
            continue
        try:
            return max(0, int(str(candidate), 16))
        except ValueError:
            logger.debug(f"ignoring an unreadable Last-Event-ID: {candidate!r}")
    return 0


class StreamLimiter:
    '''How many logs one caller may hold open at once.

    🔴 `concurrent_log_streams` is published in `GET /v1`'s limits, and a
    published number that nothing enforces is a promise rather than a limit.
    This is what makes it real.

    The cost it bounds is a worker thread and an open file for as long as the
    stream lives, which here is up to `max_log_stream_seconds`. Under a threaded
    WSGI server there is no fixed pool to exhaust, so what runs out is memory
    and file descriptors rather than capacity -- which is why the number is
    generous for a person (nobody reads eight logs at once) and deliberately not
    generous enough for a client that would open one per node of a wide flow.
    Poll the job for that; tail the nodes you are actually watching.
    '''

    def __init__(self, ceiling: int):
        import threading

        self._ceiling = ceiling
        self._open: dict = {}
        self._lock = threading.Lock()

    def acquire(self, user_id: str) -> bool:
        with self._lock:
            held = self._open.get(user_id, 0)
            if held >= self._ceiling:
                return False
            self._open[user_id] = held + 1
            return True

    def release(self, user_id: str) -> None:
        with self._lock:
            held = self._open.get(user_id, 0) - 1
            if held > 0:
                self._open[user_id] = held
            else:
                # Removed rather than left at zero, so the map is bounded by
                # who is streaming now rather than by who ever has.
                self._open.pop(user_id, None)

    def held(self, user_id: str) -> int:
        with self._lock:
            return self._open.get(user_id, 0)
