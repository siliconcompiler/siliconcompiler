'''
Read a node's log while it is still being written.

On reconnect the client re-requests ``/logs``, never reusing the target: the
capability URL has its own lifetime, so a long log is streams stitched by
``Last-Event-ID``, each re-authorized.

An expired capability or a dropped connection is ordinary, not a failure:
ask again with the last id.
'''

import codecs
import json
import logging
import re
import time

from typing import Optional

from siliconcompiler.remote.client.errors import ServerProblem, clean

__all__ = ["LogTail"]


logger = logging.getLogger(__name__)


# Used where the server's SSE `retry` field says nothing.
RECONNECT_SECONDS = 2

# What ends a line of an event stream: CRLF, LF or a lone CR.
_EOL = re.compile(r"\r\n|\r|\n")

# Before an archived log printed in full, where the live text could not be placed in it.
_IN_FULL = "(the live log could not be lined up with the archived one, so here is all of it)\n"


class LogTail:
    '''One node's log, or with no step and index the whole job's, followed to its end.

    A job stream's event id is only ever handed back, never interpreted.
    '''

    def __init__(self, client, job_id: str, step: Optional[str] = None,
                 index: Optional[str] = None):
        self.client = client
        self.job_id = job_id
        self.step = step
        self.index = index
        self.last_event_id: Optional[str] = None
        self.artifact_id: Optional[str] = None
        # Per tail, not per class: tails must not set each other's pace.
        self.retry: Optional[float] = None

    def follow(self, write=None) -> str:
        '''Read until the node, or the job, is done; returns everything emitted.

        Reconnects on any `end` but `terminal`, however long: a quiet node is
        not broken. A node's stream that ends at once replays nothing, so what
        it did not show comes from the archived log it names.
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

            if not _is_stream(response):
                # Anything but an event stream is a refusal, never log text.
                from siliconcompiler.remote.client.transport import _problem_body, _retry_after

                with response:
                    refusal = ServerProblem(_problem_body(response), response.status_code
                                            if response.status_code >= 400 else 502,
                                            retry_after=_retry_after(response))
                if refusal.status != 429 or not refusal.retry_after:
                    raise refusal
                # A slot frees as another stream closes: wait, then a fresh `/logs`.
                time.sleep(refusal.retry_after)
                continue

            with response:
                produced, finished = self._consume(response, emit)

            if finished:
                if not produced and self.step and self.artifact_id:
                    rest = self._unread("".join(collected))
                    if rest:
                        emit(rest)
                return "".join(collected)

            time.sleep(self.retry or RECONNECT_SECONDS)

    def _unread(self, shown: str) -> str:
        '''What of the node's archived log follows ``shown``, or all of it, said
        so, where what was read cannot be placed in it.'''
        archived = self.client.archived_log(self.job_id, self.step, self.index)
        # Nothing shown places nothing, unless nothing was read at all.
        if archived.startswith(shown) and (shown or self.last_event_id is None):
            return archived[len(shown):]
        return _IN_FULL + archived

    def _consume(self, response, emit):
        '''Read one stream to its end. Returns (produced anything, finished).'''
        produced = False

        try:
            for event, identifier, data in _frames(response, self):
                if identifier:
                    # Even for ignored events, so a reconnect never starts further back.
                    self.last_event_id = identifier

                if event == "log":
                    text = data.get("text")
                    if text:
                        emit(text)
                        produced = True

                elif event == "node_state":
                    # This node's archive only: a job stream names every node's.
                    node = (data.get("step"), data.get("index"))
                    if data.get("artifact_id") and None not in node and \
                            node == (self.step, self.index):
                        self.artifact_id = data["artifact_id"]

                elif event == "end":
                    self.artifact_id = data.get("artifact_id") or self.artifact_id
                    # Only `terminal` is over, possibly as the first event;
                    # any other reason is a reconnect.
                    return produced, data.get("reason") == "terminal"

        except (OSError, ValueError) as e:
            # Ordinary for a long tail; the recorded id recovers it.
            logger.debug(f"log stream interrupted: {e}")

        return produced, False


def _is_stream(response) -> bool:
    '''The ONLY test of a live tail: what was served, never a flag on the 303,
    which a node finishing in between makes stale.'''
    return response.headers.get("Content-Type", "").startswith("text/event-stream")


def _lines(chunks):
    '''An event stream's lines, decoded as UTF-8 whatever the header says. A
    CR last in a read is held: it ends a line alone or as half of a CRLF.'''
    decoder = codecs.getincrementaldecoder("utf-8-sig")(errors="replace")
    rest = ""
    for chunk in chunks:
        text = rest + decoder.decode(chunk)
        held = "\r" if text.endswith("\r") else ""
        *lines, rest = _EOL.split(text[:len(text) - len(held)])
        rest += held
        yield from lines

    *lines, last = _EOL.split(rest + decoder.decode(b"", final=True))
    yield from lines
    if last:
        yield last


def _frames(response, tail):
    '''Parse ``text/event-stream`` into (event, id, data); here, not a new dependency.'''
    event, identifier, payload = "message", None, []

    for line in _lines(response.iter_content(chunk_size=512)):
        if not line:
            if payload:
                yield event, identifier, _data("\n".join(payload))
            event, identifier, payload = "message", None, []
            continue

        if line.startswith(":"):
            # A keep-alive comment.
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
        # Drop one unreadable frame rather than end the tail.
        return {}
    return body if isinstance(body, dict) else {}
