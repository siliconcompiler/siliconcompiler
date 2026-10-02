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

from typing import Dict, Optional, Tuple

from siliconcompiler.remote.client.errors import ServerProblem, clean

__all__ = ["LogTail"]


logger = logging.getLogger(__name__)


# How long to wait before re-requesting after a stream ends without finishing.
# The server states its own preference in the SSE `retry` field and that wins;
# this is the floor for when it says nothing.
RECONNECT_SECONDS = 2


class LogTail:
    '''One node's log, or with no step and index the whole job's, followed to
    its end.

    ⚠️ **On a job stream the id is the job's, and is only ever handed back.**
    It names a position in the whole job, so this client keeps the last one and
    never reads meaning into it.
    '''

    def __init__(self, client, job_id: str, step: Optional[str] = None,
                 index: Optional[str] = None):
        self.client = client
        self.job_id = job_id
        self.step = step
        self.index = index
        self.last_event_id: Optional[str] = None
        self.artifact_id: Optional[str] = None
        # Every node's archived log, collected off `node_state` as each node
        # completes. On a job stream `end` names none -- there is no single
        # archive -- so by the time it arrives this already holds them all,
        # and no listing call is needed to find them.
        self.artifact_ids: Dict[Tuple[str, str], str] = {}
        # What the server asked us to wait before reconnecting, from the SSE
        # `retry` field. Per tail, not per class: two tails against different
        # servers must not set each other's pace.
        self.retry: Optional[float] = None

    def follow(self, write=None) -> str:
        '''Read until the node -- or the job -- is done. Returns everything it
        emitted.

        🔴 Reconnects on `expired` and on any `end` it does not know, for as
        long as it takes: a quiet node is not a broken one. A node already
        over answers with a stream that ends at once naming its archived log,
        which is then fetched as an artifact.
        '''
        collected = []

        def emit(text):
            text = clean(text)
            collected.append(text)
            if write:
                write(text)

        while True:
            response = self.client.follow_log(
                self.job_id, self.step, self.index,
                last_event_id=self.last_event_id)

            from siliconcompiler.remote.client import _is_stream

            if not _is_stream(response):
                # 🔴 After the `303` only an event stream is the log: anything
                # else is a refusal, such as the stream host's
                # `concurrent_log_streams`, and is never printed as log text.
                from siliconcompiler.remote.client.transport import _problem_body

                with response:
                    raise ServerProblem(_problem_body(response), response.status_code
                                        if response.status_code >= 400 else 502)

            with response:
                produced, finished = self._consume(response, emit)

            if finished:
                if not produced and self.step and self.artifact_id \
                        and self.last_event_id is None:
                    emit(self.client.archived_log(self.job_id, self.artifact_id,
                                                  self.step, self.index))
                return "".join(collected)

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
                    # Keyed by node: a job stream names every node's archive.
                    node = (data.get("step"), data.get("index"))
                    if data.get("artifact_id") and None not in node:
                        self.artifact_ids[node] = data["artifact_id"]
                        if node == (self.step, self.index):
                            self.artifact_id = data["artifact_id"]

                elif event == "end":
                    self.artifact_id = data.get("artifact_id") or self.artifact_id
                    # `terminal` is the node -- or the job -- being over, and
                    # ⚠️ it can be the first thing a stream says: a job that
                    # was already finished answers with a stream that ends at
                    # once. Anything else -- an expired capability, a restart
                    # -- is this connection being over, which is a reconnect
                    # rather than an end.
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
