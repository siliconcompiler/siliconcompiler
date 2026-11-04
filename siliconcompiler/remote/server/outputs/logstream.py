'''
Tailing a node that is still running.

The bytes come off the shared filesystem, where the run already writes them.
An event's ``id`` is the byte offset reached, so ``Last-Event-ID`` resumes
exactly and the server remembers nothing about its callers. What is streamed
is ``sc_<step>_<index>.log``, the file the node's `logs` artifact archives.
'''

import json
import logging
import time

from pathlib import Path
from typing import Iterator, Optional

from siliconcompiler.remote.server.jobs import NODE_TERMINAL
from siliconcompiler.remote.server.outputs import confine
from siliconcompiler.remote.server.state.store import iso

__all__ = ["resume_from", "events"]


logger = logging.getLogger("sc-server")

POLL_SECONDS = 0.25
# How often the node's state is asked for: each ask reconciles the job.
STATE_SECONDS = 2
KEEPALIVE_SECONDS = 15

# The SSE `retry`: it paces a re-request of /logs, so a re-authorization.
RETRY_MS = 2000

# The largest event; a bigger burst becomes several.
MAX_CHUNK = 64 * 1024


def resume_from(header: Optional[str]) -> int:
    '''Where to start, from `Last-Event-ID`; anything unreadable starts over, since
    replaying a log beats skipping some of it.'''
    try:
        return max(0, int(header or "", 16))
    except ValueError:
        return 0


def events(tree: Path, path: Path, step: str, index: str, node_state, artifact_id,
           start: int, deadline: float) -> Iterator[bytes]:
    '''SSE frames for one node's log, until the node is over and its log sent,
    or the capability expires at ``deadline`` (``time.time()``) and the client
    asks `/logs` again.

    ``node_state`` and ``artifact_id`` are callables: they change under a long stream.
    '''
    sent = start
    last = time.monotonic()
    asked = None

    yield f"retry: {RETRY_MS}\n\n".encode()

    while True:
        # Before reading, so a node that ends meanwhile is drained by the next pass.
        if asked is None or time.monotonic() - asked >= STATE_SECONDS:
            state, asked = node_state(), time.monotonic()
        over = state in NODE_TERMINAL
        data = _read(tree, path, sent)
        # A node that is over sends its last unterminated line, but not half a character.
        if not over or len(data) == MAX_CHUNK:
            data = data[:_whole(data)]

        if data:
            sent += len(data)
            yield _event("log", {"step": step, "index": index, "stream": "stdout",
                                 "logged_at": iso(time.time()),
                                 "text": data.decode("utf-8", errors="replace")},
                         identifier=format(sent, "x"))
            last = time.monotonic()
            continue

        if over:
            artifact = artifact_id()
            named = {"artifact_id": artifact} if artifact else {}
            yield _event("node_state", {"step": step, "index": index, "state": state,
                                        "terminal": True, **named})
            yield _event("end", {"reason": "terminal", **named})
            return

        if time.time() >= deadline:
            yield _event("end", {"reason": "expired"})
            return

        if time.monotonic() - last >= KEEPALIVE_SECONDS:
            yield b": keep-alive\n\n"
            last = time.monotonic()
        time.sleep(POLL_SECONDS)


def _read(tree: Path, path: Path, offset: int) -> bytes:
    try:
        with confine.open_inside(tree, path) as f:
            f.seek(offset)
            return f.read(MAX_CHUNK)
    except OSError as e:
        logger.debug(f"could not read {path}: {e}")
        return b""


def _whole(chunk: bytes) -> int:
    '''How much of ``chunk`` ends on a line, or on a character for a line longer than it.'''
    cut = chunk.rfind(b"\n") + 1
    if cut or len(chunk) < MAX_CHUNK:
        return cut

    # Never split a UTF-8 character across two events.
    for size in range(len(chunk), len(chunk) - 4, -1):
        try:
            chunk[:size].decode()
            return size
        except UnicodeDecodeError:
            pass
    return len(chunk)


def _event(name: str, body: dict, identifier: Optional[str] = None) -> bytes:
    frame = f"event: {name}\n"
    if identifier is not None:
        # Only `log` events carry an id: an id on `end` would resume past it.
        frame += f"id: {identifier}\n"
    return (frame + f"data: {json.dumps(body, separators=(',', ':'))}\n\n").encode()
