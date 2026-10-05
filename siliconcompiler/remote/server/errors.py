'''
Every way this API says no: the ``type`` registry, frozen at v1.

The namespace is SiliconCompiler's, not a deployment's, so every implementation
returns the same URI. A slug names a kind of failure; the discriminator is an
extension member (``limit``, ``reason``), since a member's value can be added
after the freeze and a slug cannot. Rows are registered even where nothing
raises them: a missing row costs a major version.
'''

import re

from typing import Any, Dict, NamedTuple, Optional

__all__ = ["DETAIL_MAX", "ERRORS", "TYPE_BASE", "OAuthError", "ProblemError",
           "bound", "problem", "set_detail_max"]


# Fixed by the v1 API and identical on every deployment.
TYPE_BASE = "https://siliconcompiler.com/server-errors"


class _Error(NamedTuple):
    '''One row of the registry. ``status`` is None for a slug that is only a
    ``type`` on a job's or a node's ``error`` object, never an HTTP response.'''
    slug: str
    status: Optional[int]
    title: str
    members: tuple = ()

    @property
    def uri(self) -> str:
        return f"{TYPE_BASE}/{self.slug}"


# `title` is fixed here so every occurrence of a slug is identical.
ERRORS: Dict[str, _Error] = {err.slug: err for err in (
    _Error("limit-exceeded", 429, "Limit exceeded", ("limit",)),
    # `limit` only over max_upload_bytes; a body over its endpoint's cap has none.
    _Error("upload-too-large", 413, "Upload too large"),
    _Error("node-limit-exceeded", 403, "Too many nodes in this flow", ("limit",)),
    # Over `max_download_bytes`, which never refills -- so not
    # `limit-exceeded`, whose `Retry-After` a client would obey for ever.
    _Error("download-too-large", 403, "Download too large", ("limit",)),
    _Error("rate-limited", 429, "Too many requests"),

    _Error("entitlement-denied", 403, "Not entitled to this resource",
           ("resource_kind", "resource")),
    _Error("resource-unresolved", 422, "Could not resolve what this flow needs",
           ("resource_kind",)),
    # No live image satisfies the job's software requirements;
    # `reason` is "unavailable" or "combination".
    _Error("software-unavailable", 422, "No image provides that software",
           ("reason", "unresolved")),
    # A resource of any kind this deployment neither holds nor can supply;
    # `resource-unresolved` is not knowing WHICH. `resource_kind` and `keypath`
    # are optional, so not listed.
    _Error("resource-unavailable", 422, "This server does not hold that resource",
           ("resource",)),
    # For restricted material found while staging. The API defines it; this
    # profile allows every upload and never raises it.
    _Error("upload-forbidden", 422, "Upload of that resource is not allowed",
           ("resource_kind", "detected", "member")),
    _Error("terms-not-accepted", 403, "Terms not accepted", ("blocked_by",)),
    _Error("artifact-not-approved", 403, "Artifact not approved"),

    _Error("declared-mismatch", 422, "The manifest contradicts the descriptor"),
    _Error("upload-digest-mismatch", 422, "Upload digest does not match"),
    _Error("archive-rejected", 422, "Archive rejected", ("reason",)),
    _Error("idempotency-key-reuse", 422, "Idempotency key reused with a different request"),
    _Error("invalid-cursor", 400, "Invalid cursor"),
    _Error("invalid-request", 400, "Invalid request"),
    _Error("method-not-allowed", 405, "Method not allowed"),
    _Error("unsupported-media-type", 415, "Unsupported media type"),
    _Error("not-acceptable", 406, "Not acceptable"),

    _Error("job-state-conflict", 409, "The job is not in a state that allows this"),
    # A write on a job the caller can read and may not act on, and a create
    # naming an archived project.
    _Error("not-permitted", 403, "Not permitted on this job"),
    _Error("not-found", 404, "Not found"),
    _Error("not-ready", 409, "Not ready yet", ("artifact_kind",)),
    _Error("feature-unsupported", 501, "This deployment does not support that", ("feature",)),

    _Error("invalid-token", 401, "Invalid access token"),
    _Error("invalid-dpop-proof", 401, "Invalid DPoP proof"),
    _Error("dpop-nonce-required", 401, "DPoP nonce required"),
    _Error("insufficient-scope", 403, "Insufficient scope"),
    _Error("session-ended", 401, "Session ended", ("reason",)),
    _Error("insecure-transport", 426, "Upgrade required"),

    # The environment ended the run: lost by the scheduler, preempted, a failed
    # compute node, an image that could not be pulled.
    _Error("run-interrupted", None, "The run was interrupted"),
    # A `continues_from` entry whose results cannot be used.
    _Error("prior-results-unavailable", 422, "Those earlier results cannot be used",
           ("step", "index", "job_id", "reason")),
    # This profile provisions on first contact and never raises it.
    _Error("account-not-provisioned", 403, "Your account is not set up on this deployment"),
    # A job-level type: staging the server could not complete for its own
    # reasons, after retrying.
    _Error("staging-failed", None, "The server could not get this job ready"),
    # The job's own limit, not the server's failure.
    _Error("staging-timed-out", None, "The job took too long to get ready", ("limit",)),
    _Error("run-failed", None, "The run failed"),
)}


# A `feature` value holds only registered `features` strings.
FEATURES = ("logs.stream", "logs.stream.job", "projects", "python.env",
            "jobs.reuse")

# Which archive rule was broken: `archive-rejected`'s `reason`.
ARCHIVE_VIOLATIONS = ("member_count", "expanded_bytes", "ratio",
                      "link_member", "device_member", "traversal",
                      # No manifest at the root, or one that cannot be read.
                      "missing_manifest", "invalid_manifest",
                      # A dataroot path carrying userinfo.
                      "credential",
                      # A follow-up archive carrying what was not asked for.
                      "unrequested_member",
                      # A value the flow reads that the client should have sent.
                      "missing_member",
                      # An impure, malformed or overlapping wheel, or any wheel
                      # without `python.env`.
                      "python_package",
                      # This profile never raises it.
                      "extension",
                      # A job that would wait for a person nobody is at.
                      "breakpoint", "interactive_task")


class OAuthError(Exception):
    '''A refusal from OAuth processing at `/v1/auth/token` or `/v1/auth/device`,
    in RFC 6749 section 5.2's shape. Transport refusals raised before it (405, 415,
    426, 429) stay `ProblemError`.'''

    # The codes a client branches on, and nothing else is ever sent.
    CODES = ("invalid_request", "invalid_client", "invalid_grant",
             "unsupported_grant_type", "invalid_scope", "access_denied",
             "use_dpop_nonce", "invalid_dpop_proof")

    def __init__(self, error: str, description: Optional[str] = None,
                 reason: Optional[str] = None, status: int = 400,
                 headers: Optional[dict] = None):
        if error not in self.CODES:
            raise KeyError(f"{error} is not an OAuth error code this server sends")
        self.error = error
        self.description = description
        self.reason = reason
        self.status = status
        self.headers = headers or {}
        super().__init__(description or error)

    def body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"error": self.error}
        if self.description:
            body["error_description"] = bound(self.description)
        if self.reason:
            body["reason"] = self.reason
        return body


class ProblemError(Exception):
    '''A refusal, raised where it is decided and rendered at the edge.'''

    def __init__(self, slug: str, detail: Optional[str] = None,
                 status: Optional[int] = None, headers: Optional[dict] = None,
                 **members):
        if slug not in ERRORS:
            raise KeyError(f"{slug} is not in the frozen error registry")

        self.error = ERRORS[slug]
        self.detail = detail
        self.headers = headers or {}
        self.members = members

        registered = self.error.status
        if registered is None and status is None:
            raise ValueError(
                f"{slug} is never an HTTP response; it is a type on an error object")
        self.status = status or registered

        super().__init__(detail or self.error.title)

    def body(self) -> Dict[str, Any]:
        return problem(self.error.slug, detail=self.detail,
                       status=self.status, **self.members)


# How much of a `detail` reaches a caller.
# Some details carry text this server did not write -- a tool's exception, a
# member's name -- with a path the CLIENT chose, and `detail` is published to
# anyone who can read the job. Bounded once, in `problem()`, for every refusal;
# the full text still reaches the log.
# Characters, not bytes: cutting UTF-8 by bytes splits a codepoint.
# A module-level default that `limits.max_detail_chars` replaces at startup, so
# no call site has a way around it.
DETAIL_MAX = 300


def set_detail_max(characters: int) -> None:
    """Adopt the deployment's bound. Called once, at startup."""
    global DETAIL_MAX
    DETAIL_MAX = int(characters)


# This server's internals, which a `detail` must never carry: its data and
# mount paths, and its host names.
_INTERNAL_PATHS: list = []
_INTERNAL_NAMES: list = []


def set_internals(paths=(), names=()) -> None:
    """What `scrub` takes out of every `detail`. Called once, at startup."""
    # Stripped before the empty ones are dropped: `/` would otherwise become
    # the empty string, which `replace` finds between every two characters.
    _INTERNAL_PATHS[:] = sorted({str(path).rstrip("/") for path in paths if path}
                                - {""}, key=len, reverse=True)
    _INTERNAL_NAMES[:] = sorted({str(name) for name in names if name and len(name) > 2},
                                key=len, reverse=True)


# Credential-shaped: `token=...`, `password: ...`, a bearer header, a URL's
# `user:secret@`, and the long opaque strings API keys are made of.
_CREDENTIALS = (
    # The header with its scheme, then a scheme on its own: `Authorization:
    # Bearer x` must not stop at `Bearer` and leave `x`.
    (re.compile(r"(?i)\b(authorization)\s*[:=]\s*(?:(?:bearer|dpop|basic)\s+)?\S+"),
     r"\1 <redacted>"),
    (re.compile(r"(?i)\b(bearer|dpop|basic)\s+(?!<redacted>)\S+"), r"\1 <redacted>"),
    (re.compile(r"(?i)\b(pass(word)?|passwd|secret|token|api[_-]?key|key)\s*[:=]\s*\S+"),
     r"\1=<redacted>"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"), r"\1<redacted>@"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}"
                r"\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b"), "<redacted>"),
)


def scrub(detail: str) -> str:
    '''Take this server's internals out of a `detail`.

    A tool's exception text carries mount paths, hostnames and environment
    dumps, which leak how the deployment is laid out.
    '''
    text = detail
    for path in _INTERNAL_PATHS:
        text = text.replace(path, "<server>")
    for name in _INTERNAL_NAMES:
        text = re.sub(rf"\b{re.escape(name)}\b", "<host>", text)
    for pattern, replacement in _CREDENTIALS:
        text = pattern.sub(replacement, text)
    return text


# NUL, the rest of C0, DEL and C1, whose U+009B is a one-character terminal
# escape. Tab and newlines go in the whitespace collapse instead.
_UNPRINTABLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def bound(detail: Optional[str]) -> Optional[str]:
    '''One line of somebody else's text, short enough to publish: no control
    characters (it reaches a terminal), no newlines (it breaks logs), and at
    most `DETAIL_MAX` characters.'''
    if not detail:
        return detail

    text = _UNPRINTABLE.sub("", detail)
    text = " ".join(scrub(text).split())
    if len(text) <= DETAIL_MAX:
        return text

    # Cut at a word where there is one nearby, so the tail is not half a path.
    cut = text[:DETAIL_MAX]
    space = cut.rfind(" ")
    if space > DETAIL_MAX - 40:
        cut = cut[:space]
    return cut + "..."


_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def trace_id(headers) -> str:
    '''This request's correlation id: the trace id of a W3C `traceparent`
    where one arrived and is valid, else a fresh one -- once per request.'''
    import uuid

    import flask

    held = getattr(flask.g, "sc_trace_id", None) if flask.has_request_context() else None
    if held:
        return held
    found = _TRACEPARENT.match((headers.get("traceparent") or "").strip().lower())
    value = found.group(1) if found and found.group(1) != "0" * 32 else uuid.uuid4().hex
    if flask.has_request_context():
        flask.g.sc_trace_id = value
    return value


def only_query(args, allowed, where: str) -> None:
    '''Refuse a query parameter the collection does not define: a misspelled
    filter would otherwise return everything.'''
    unknown = sorted(set(args) - set(allowed))
    if unknown:
        raise ProblemError(
            "invalid-request",
            detail=f"{where} takes no {', '.join(unknown)}"
                   + (f"; it takes {', '.join(allowed)}" if allowed else ""))


def problem(slug: str, detail: Optional[str] = None,
            status: Optional[int] = None, **members) -> Dict[str, Any]:
    '''An RFC 9457 body. ``type`` and ``title`` come from the registry; a
    client branches on ``type``, never on the rewordable ``detail``.

    `detail` is bounded here and nowhere else -- see `DETAIL_MAX`.
    '''
    err = ERRORS[slug]

    body: Dict[str, Any] = {
        "type": err.uri,
        "title": err.title,
    }

    resolved = status or err.status
    if resolved is not None:
        body["status"] = resolved
    if detail:
        body["detail"] = bound(detail)

    body.update(members)
    return body
