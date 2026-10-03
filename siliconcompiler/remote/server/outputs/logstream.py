'''
Tailing a node that is still running.

The bytes come off the shared filesystem, where the run already writes them:
the compute node holds no database connection, so the API host and the compute
node can be different machines.

A node stream's event ``id`` is the byte offset reached, so ``Last-Event-ID``
resumption is exact and the stream host remembers nothing about its callers.
What is streamed is ``sc_<step>_<index>.log``, the file the ``logs`` artifact
archives, so the tail and the download are the same bytes.
'''

import contextlib
import json
import logging
import struct
import threading
import time

from pathlib import Path
from typing import Dict, Iterator, Optional

from siliconcompiler.remote.server.outputs import confine
from siliconcompiler.remote.server.state.store import TERMINAL_NODE_STATES

try:
    import fcntl
except ImportError:                                 # Windows: one process only
    fcntl = None

__all__ = ["EventIndex", "events", "job_events", "resume_from", "resume_job",
           "POLL_SECONDS", "RETRY_MS"]


logger = logging.getLogger("sc-server")


POLL_SECONDS = 0.5

# The SSE `retry`: it paces a re-request of /logs, so a re-authorization.
RETRY_MS = 2000

# The largest event; a bigger burst becomes several.
MAX_CHUNK = 64 * 1024


def events(path: Path, step: str, index: str, node_state, start: int,
           deadline: float, keepalive: float, artifact_id=None, root=None,
           ended: bool = False) -> Iterator[bytes]:
    '''Yield SSE frames for one node's log until it ends or time runs out.

    ``node_state`` is a callable, since the state changes under a long stream.
    ``deadline`` is when this capability expires: the stream ends cleanly and
    the client re-requests ``/logs`` for a fresh authorization.
    '''
    offset = max(0, int(start))
    pending = b""
    last_sent = time.monotonic()

    yield f"retry: {RETRY_MS}\n\n".encode()

    # `/logs` is live output only: a node already over when `/logs` was
    # asked gets a stream that ends at once, naming its archived log. One that
    # finished between the `303` and the connect is drained below.
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
            # Start over rather than seek to the end, which would drop a log.
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
            # Drain the rest, a final line with no newline included.
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
            # The capability is over, not the log: the client resumes.
            yield _event("end", {"reason": "expired"})
            return

        if time.monotonic() - last_sent >= keepalive:
            yield b": keep-alive\n\n"
            last_sent = time.monotonic()

        time.sleep(POLL_SECONDS)


def job_events(nodes, path_of, node_states, job_over, start, deadline, keepalive: float,
               artifact_id, index, root=None) -> Iterator[bytes]:
    '''Yield SSE frames for every node of a job, merged, until it ends.

    ``nodes`` is in the store's fixed order, since an index entry names a node
    by its place in it. ``start`` is what :func:`resume_job` read.

    The id is job-wide and one number: how many entries of the job's
    :class:`EventIndex` this caller has been sent. Not a vector of per-node
    offsets, which could pass what proxies accept for one `Last-Event-ID` on a
    thousand-node flow.

    A job already over when the stream opens gets `end` at once, nothing
    replayed, the same as one ending between the `303` and the connect.
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

        # What the index holds, possibly put there by another reader.
        for number, slot, offset, length in index.entries(position):
            step, node_index = nodes[slot]
            chunk, _ = _read(path_of(step, node_index), offset, length, root)
            position = number + 1
            yield _log(step, node_index, _decode(chunk), f"{_JOB_ID_PREFIX}{position:x}")
            last_sent = time.monotonic()
            progressed = True
        if progressed:
            continue

        states = node_states()
        if index.extend(nodes, path_of, states, root):
            continue

        # A node is over only once everything it wrote has been sent, and
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

        # Checked on a busy pass too, or a never-quiet job outlives its capability.
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


# Marks a job stream's id, so a per-node hex offset is never read as one.
_JOB_ID_PREFIX = "e"


def resume_job(header: Optional[str], fallback, index: "EventIndex") -> int:
    '''How many of the index's entries the caller already has; 0 for an id not this job's.'''
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

    Append-only, by whichever reader finds a log has grown, so an entry's number
    means the same bytes to every reader. Fixed-width, so resuming is a seek.
    One instance per reader; its state is about the job, never the caller.
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
        '''Every entry from ``start`` on, as (number, slot, offset, length).'''
        number = start
        while True:
            batch = self._read(number)
            if not batch:
                return
            for slot, offset, length in batch:
                if slot < self.width:
                    yield number, slot, offset, length
                number += 1

    def extend(self, nodes, path_of, states, root=None) -> bool:
        '''Index what each node's log has gained; True if anything was.

        Whole lines only while a node runs, everything once it is over.
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
    '''How much of ``chunk`` ends on a line, or on a character for a line longer than it.'''
    cut = chunk.rfind(b"\n") + 1
    if cut or not full:
        return cut

    # Never split a UTF-8 character across two events.
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
    '''One appender at a time: a lock per path, plus `flock` across processes.'''
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
    '''Add `artifact_id` once there is one; a null would claim there never will be.'''
    if artifact:
        body["artifact_id"] = artifact
    return body


def _event(name: str, body: dict, identifier: Optional[str] = None) -> bytes:
    frame = f"event: {name}\n"
    if identifier is not None:
        # Only `log` events carry an id: an id on `end` would resume past it.
        frame += f"id: {identifier}\n"
    frame += f"data: {json.dumps(body, separators=(',', ':'))}\n\n"
    return frame.encode()


def _size(path: Path, root=None) -> int:
    '''The file's size, 0 where it is not written yet.

    Given ``root``, only a regular file reached through no link counts: a
    node can replace its log with a link to the host's files.
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
    '''Whole lines out of the buffer, and what is left over.'''
    if complete:
        return _decode(buffer), b""

    cut = buffer.rfind(b"\n")
    if cut < 0:
        return "", buffer
    return _decode(buffer[:cut + 1]), buffer[cut + 1:]


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _now() -> str:
    from siliconcompiler.remote.server.state.store import now

    return now()


def resume_from(header: Optional[str], fallback) -> int:
    '''Where to start, from `Last-Event-ID` or the query-parameter fallback.

    Anything unreadable starts from the beginning: replaying beats skipping.
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
    '''Enforces `concurrent_log_streams`, the published per-caller limit.

    It bounds a thread and an open file per stream: generous for a person, not
    for a client opening one per node of a wide flow.
    '''

    def __init__(self, ceiling: int):
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
                self._open.pop(user_id, None)

    def held(self, user_id: str) -> int:
        with self._lock:
            return self._open.get(user_id, 0)
