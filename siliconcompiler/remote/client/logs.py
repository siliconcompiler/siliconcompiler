'''
Reading a node's log while it is still being written.

🔴 **On reconnect the client re-requests ``/logs``; it never reuses the
target.** The capability URL carries a lifetime of its own, independent of the
900-second access token, so a six-hour place-and-route log is a sequence of
capability-length streams stitched together by ``Last-Event-ID`` rather than one
connection outliving the credential that opened it. Re-requesting is also what
re-evaluates authorization, at the endpoint that takes a token and a proof.

⚠️ **A capability expiring is the ordinary way a long tail ends**, not a
failure, and neither is the connection being dropped by something in the middle.
Both are the same recovery: ask again, hand back the last id, carry on.
'''

import json
import logging
import time

from typing import Optional

from siliconcompiler.remote.client.errors import RemoteError, ServerProblem

__all__ = ["LogTail"]


logger = logging.getLogger(__name__)


# How long to wait before re-requesting after a stream ends without finishing.
# The server states its own preference in the SSE `retry` field and that wins;
# this is the floor for when it says nothing.
RECONNECT_SECONDS = 2

# A tail that reconnects this many times in a row without receiving a single
# byte has found something that is not going to start working.
MAX_EMPTY_RECONNECTS = 5


class LogTail:
    '''One node's log, followed to its end.'''

    def __init__(self, client, job_id: str, step: str, index: str):
        self.client = client
        self.job_id = job_id
        self.step = step
        self.index = index
        self.last_event_id: Optional[str] = None
        self.artifact_id: Optional[str] = None
        # What the server asked us to wait before reconnecting, from the SSE
        # `retry` field. Per tail, not per class: two tails against different
        # servers must not set each other's pace.
        self.retry: Optional[float] = None

    def follow(self, write=None) -> str:
        '''Read until the node is done. Returns everything it emitted.'''
        collected = []
        empty = 0

        def emit(text):
            collected.append(text)
            if write:
                write(text)

        while True:
            response = self.client.follow_log(
                self.job_id, self.step, self.index,
                last_event_id=self.last_event_id)

            from siliconcompiler.remote.client import _is_stream

            if not _is_stream(response):
                # It finished while we were asking. The archived file is the
                # same bytes the tail was reading, so what is left is the part
                # after the last id we saw -- but a file has no offset on the
                # wire, so the whole of it is served and only the tail from here
                # is new.
                with response:
                    emit(_text_from(response))
                return "".join(collected)

            with response:
                produced, finished = self._consume(response, emit)

            if finished:
                return "".join(collected)

            empty = 0 if produced else empty + 1
            if empty >= MAX_EMPTY_RECONNECTS:
                raise RemoteError(
                    f"the log for {self.step}/{self.index} reconnected "
                    f"{empty} times without producing anything")

            time.sleep(self.retry or RECONNECT_SECONDS)

    ######################################################################

    def _consume(self, response, emit):
        '''Read one stream to its end. Returns (produced anything, finished).'''
        produced = False

        try:
            for event, identifier, data in _frames(response, self):
                if identifier:
                    # Kept even for events this client ignores, so a reconnect
                    # never asks to start further back than it reached.
                    self.last_event_id = identifier

                if event == "log":
                    text = data.get("text")
                    if text:
                        emit(text)
                        produced = True

                elif event == "node_state":
                    self.artifact_id = data.get("artifact_id") or self.artifact_id

                elif event == "end":
                    self.artifact_id = data.get("artifact_id") or self.artifact_id
                    # `terminal` is the node being over; anything else -- an
                    # expired capability, a restart -- is this connection being
                    # over, which is a reconnect rather than an end.
                    return produced, data.get("reason") == "terminal"

        except (OSError, ValueError) as e:
            # The connection went away mid-stream. Ordinary for a long tail,
            # and the id already recorded is what makes it recoverable.
            logger.debug(f"log stream interrupted: {e}")

        return produced, False


def _frames(response, tail):
    '''Parse ``text/event-stream`` into (event, id, data) triples.

    Written here rather than taken from a dependency because it is twenty lines
    and the alternative is a runtime dependency on the client side of every
    SiliconCompiler install for one endpoint.
    '''
    event, identifier, payload = "message", None, []

    for raw in response.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.rstrip("\r")

        if not line:
            if payload:
                yield event, identifier, _data("\n".join(payload))
            event, identifier, payload = "message", None, []
            continue

        if line.startswith(":"):
            # A comment, which is how the server keeps a quiet connection
            # visibly alive.
            continue

        name, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value

        if name == "event":
            event = value
        elif name == "id":
            identifier = value
        elif name == "data":
            payload.append(value)
        elif name == "retry":
            try:
                tail.retry = max(1, int(value) / 1000)
            except ValueError:
                pass

    if payload:
        yield event, identifier, _data("\n".join(payload))


def _data(raw: str) -> dict:
    try:
        body = json.loads(raw)
    except ValueError:
        # A frame this client cannot read is one frame, and dropping it is
        # better than ending a tail that is otherwise working.
        return {}
    return body if isinstance(body, dict) else {}


def _text_from(response) -> str:
    try:
        return response.text
    except ServerProblem:                                       # pragma: no cover
        raise
    except Exception as e:                                      # noqa: BLE001
        logger.debug(f"could not read the archived log: {e}")
        return ""
