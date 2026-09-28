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

import contextlib
import json
import logging
import struct
import threading
import time

from pathlib import Path
from typing import Dict, Iterator, Optional

from siliconcompiler.remote.server import confine

try:
    import fcntl
except ImportError:                                 # Windows: one process only
    fcntl = None

__all__ = ["EventIndex", "events", "job_events", "resume_from", "resume_job",
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
           deadline: float, artifact_id=None, root=None,
           keepalive: float = HEARTBEAT_SECONDS, ended: bool = False) -> Iterator[bytes]:
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

    # 🔴 `/logs` is live output only: a node already over when `/logs` was
    # asked gets a stream that ends at once, naming its archived log. One that
    # finished between the `303` and the connect is drained below as before.
    state = node_state()
    if ended and state in TERMINAL_NODE_STATES:
        yield _event("node_state", _with_artifact(
            {"step": step, "index": index, "state": state, "terminal": True},
            artifact_id()))
        yield _event("end", _with_artifact({"reason": "terminal"}, artifact_id()))
        return

    while True:
        size = _size(path, root)

        if size < offset:
            # The file got smaller, so the offset a client handed back points
            # at bytes that are no longer there. Starting over is the only
            # honest answer; silently seeking to the end would drop a log.
            logger.warning(f"{path} shrank under a reader; restarting the tail")
            offset, pending = 0, b""

        if size > offset:
            chunk, offset = _read(path, offset, MAX_CHUNK, root)
            pending += chunk

            text, pending = _split(pending, complete=False)
            if text:
                yield _event("log", {
                    "step": step, "index": index, "stream": "stdout",
                    "logged_at": _now(), "text": text,
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
                    "logged_at": _now(), "text": text,
                }, identifier=format(offset, "x"))

            yield _event("node_state", _with_artifact(
                {"step": step, "index": index, "state": state, "terminal": True},
                artifact_id()))
            yield _event("end", _with_artifact(
                {"reason": "terminal"}, artifact_id()))
            return

        if time.monotonic() >= deadline:
            # Not an error and not the end of the log: this capability is over.
            # The client re-requests /logs and resumes from its last id.
            yield _event("end", {"reason": "expired"})
            return

        if time.monotonic() - last_sent >= keepalive:
            yield b": keep-alive\n\n"
            last_sent = time.monotonic()

        time.sleep(POLL_SECONDS)


def job_events(nodes, path_of, node_states, job_over, start, deadline,
               artifact_id, index, root=None,
               keepalive: float = HEARTBEAT_SECONDS) -> Iterator[bytes]:
    '''Yield SSE frames for every node of a job, merged, until it ends.

    ``nodes`` is the job's node list in a fixed order -- the store's -- because
    an index entry names a node by its place in it. ``path_of(step, index)`` is
    where a node's log is, ``node_states()`` what every node is doing now,
    ``job_over()`` whether the job is terminal, ``artifact_id(step, index)`` a
    node's archived log once there is one, and ``index`` the job's
    :class:`EventIndex`. ``start`` is what :func:`resume_job` read.

    🔴 **The id is job-wide, and that is the rule a merge gets wrong.** A
    per-node id is a byte offset in ONE file, and resuming a merged stream from
    one of those would start every other node at a position that is not its
    own.

    🔴 **And it is one number, whatever the node count** (D121): the count of
    entries in the job's event index that this caller has been sent. The index
    records every `log` event the job's stream has ever carried -- which node,
    where in its log, how long -- so every reader of the job is sent the same
    events under the same ids, and resuming is one seek. ⚠️ It replaces a
    vector of per-node offsets, which even sparse could pass what common
    proxies accept for one `Last-Event-ID` header on a thousand-node flow. The
    index is state about the JOB; this host still keeps none about its callers.

    Ordering is kept within a node and is arrival order across them: an entry
    is appended when a reader finds a node's log has grown, node by node.

    ⚠️ **A job already over when the stream opens gets `end` at once**, with
    nothing replayed. It is the same answer as a job that ends between the
    `303` and the connect, so the late request and the race are one path, and
    the client reads the listing for `kind=logs`. `end` names no artifact on a
    job stream: there is no single archive, and each node's `node_state`
    already named its own.
    '''
    position = start
    reported = [False] * len(nodes)
    last_sent = time.monotonic()

    yield f"retry: {RETRY_MS}\n\n".encode()

    if job_over():
        yield _event("end", {"reason": "terminal"})
        return

    while True:
        progressed = False

        # What the index already holds, which another reader may have put
        # there: the same events under the same ids for everyone.
        for number, slot, offset, length in index.entries(position):
            step, node_index = nodes[slot]
            chunk, _ = _read(path_of(step, node_index), offset, length, root)
            position = number + 1
            yield _log(step, node_index, _decode(chunk), _job_id(position))
            last_sent = time.monotonic()
            progressed = True
        if progressed:
            continue

        # Caught up: whatever the logs gained since becomes the next entries.
        states = node_states()
        if index.extend(nodes, path_of, states, root):
            continue

        # 🔴 A node is over only once everything it wrote has been sent, and
        # another reader may have indexed more of it since the loop above.
        if index.count() > position:
            continue
        for slot, (step, node_index) in enumerate(nodes):
            state = states.get((step, node_index))
            if reported[slot] or state not in TERMINAL_NODE_STATES:
                continue
            yield _event("node_state", _with_artifact(
                {"step": step, "index": node_index, "state": state, "terminal": True},
                artifact_id(step, node_index)))
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

        if time.monotonic() - last_sent >= keepalive:
            yield b": keep-alive\n\n"
            last_sent = time.monotonic()

        time.sleep(POLL_SECONDS)


def _log(step: str, index: str, text: str, identifier: str) -> bytes:
    return _event("log", {"step": step, "index": index, "stream": "stdout",
                          "logged_at": _now(), "text": text}, identifier=identifier)


# What marks a job stream's id, so a per-node one -- a bare hex offset -- is
# never read as a position in the index.
_JOB_ID_PREFIX = "e"


def _job_id(position: int) -> str:
    return f"{_JOB_ID_PREFIX}{position:x}"


def resume_job(header: Optional[str], fallback, index: "EventIndex") -> int:
    '''How many of the index's entries the caller already has, or 0.

    ⚠️ An id that does not fit the job -- a per-node id, the vector this used
    to emit, or a position past the end of this job's index -- starts from the
    beginning: a stream that replays is a nuisance, one that skips is a lost
    log.
    '''
    for candidate in (header, fallback):
        if not candidate:
            continue
        text = str(candidate)
        try:
            if not text.startswith(_JOB_ID_PREFIX):
                raise ValueError("not a job stream's id")
            position = int(text[len(_JOB_ID_PREFIX):], 16)
            if 0 <= position <= index.count():
                return position
        except ValueError:
            pass
        logger.debug(f"ignoring a Last-Event-ID that is not this job's: {candidate!r}")
    return 0


class EventIndex:
    '''Every `log` event a job's stream has carried: node, offset, length.

    Appended as the job runs, by whichever reader finds a node's log has grown,
    and never rewritten -- so an entry's number is an id that means the same
    bytes to every reader, and resuming is a seek to it. Fixed-width entries,
    so the seek is arithmetic.

    One instance per reader. It remembers how far it has scanned and where each
    node's indexed bytes end, which is state about the job read back from the
    file, never about the caller.
    '''

    ENTRY = struct.Struct(">IQI")           # slot, byte offset, length
    _BATCH = 4096

    def __init__(self, path: Path, width: int):
        self.path = Path(path)
        self.width = width
        self._scanned = 0
        self._ends = [0] * width

    def count(self) -> int:
        return _size(self.path) // self.ENTRY.size

    def entries(self, start: int):
        '''Every entry from number ``start`` on, as (number, slot, offset,
        length).'''
        number = start
        while True:
            batch = self._read(number)
            if not batch:
                return
            for slot, offset, length in batch:
                # A node this job has not got: not an entry of this job's.
                if slot < self.width:
                    yield number, slot, offset, length
                number += 1

    def extend(self, nodes, path_of, states, root=None) -> bool:
        '''Index what each node's log has gained. True if anything was.

        Whole lines only while a node runs -- a reader that prints what it is
        given would otherwise show a line in two pieces -- and everything once
        it is over, since nothing more is coming to finish the last line.
        '''
        with _locked(self.path):
            self._catch_up()
            new = []
            for slot, (step, index) in enumerate(nodes):
                path = path_of(step, index)
                size, end = _size(path, root), self._ends[slot]
                if size < end:
                    logger.warning(f"{path} shrank under a reader; restarting its tail")
                    end = 0
                if size <= end:
                    continue

                length = min(size - end, MAX_CHUNK)
                if not (states.get((step, index)) in TERMINAL_NODE_STATES
                        and end + length == size):
                    chunk, _ = _read(path, end, length, root)
                    length = _whole_lines(chunk, full=len(chunk) == MAX_CHUNK)
                    if not length:
                        continue
                new.append((slot, end, length))
                self._ends[slot] = end + length

            if new:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "ab") as f:
                    f.write(b"".join(self.ENTRY.pack(*entry) for entry in new))
                self._scanned += len(new)
            return bool(new)

    def _catch_up(self) -> None:
        while True:
            batch = self._read(self._scanned)
            if not batch:
                return
            for slot, offset, length in batch:
                if slot < self.width:
                    self._ends[slot] = offset + length
            self._scanned += len(batch)

    def _read(self, start: int):
        size = self.ENTRY.size
        try:
            with open(self.path, "rb") as f:
                f.seek(start * size)
                data = f.read(self._BATCH * size)
        except OSError:
            return []
        return [self.ENTRY.unpack_from(data, at)
                for at in range(0, len(data) - len(data) % size, size)]


def _whole_lines(chunk: bytes, full: bool) -> int:
    '''How much of ``chunk`` ends on a line, or -- where a line is longer
    than a whole chunk -- on a character.'''
    cut = chunk.rfind(b"\n") + 1
    if cut or not full:
        return cut

    # A line longer than a chunk becomes several events; never split a UTF-8
    # character across two of them.
    at = len(chunk) - 1
    while at > len(chunk) - 4 and at > 0 and chunk[at] & 0xC0 == 0x80:
        at -= 1
    lead = chunk[at]
    need = 4 if lead >= 0xF0 else 3 if lead >= 0xE0 else 2 if lead >= 0xC0 else 1
    return at if len(chunk) - at < need else len(chunk)


_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


@contextlib.contextmanager
def _locked(path: Path):
    '''One appender at a time: per path in this process, and by `flock`
    across processes where there is one.'''
    with _LOCKS_LOCK:
        lock = _LOCKS.setdefault(str(path), threading.Lock())
    with lock:
        if fcntl is None:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(f"{path}.lock", "ab") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


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


def _size(path: Path, root=None) -> int:
    '''How much of the file there is: 0 where it is not written yet -- a node
    can be dispatched before it opens its log, and waiting is the right answer
    rather than ending the stream.

    🔴 Given the job's ``root``, only a regular file reached through no link
    counts: a node's code can replace its own log with a link to anything, and
    a tail that followed it would stream the host's files to the caller.
    '''
    if root is not None:
        return confine.size_inside(root, path)
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _read(path: Path, offset: int, limit: int, root=None):
    try:
        opened = confine.open_inside(root, path) if root is not None else open(path, "rb")
        with opened as f:
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
    stream lives, which is no longer than the token that obtained it. Under a threaded
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
