'''
Every way this API says no.

The ``type`` registry is frozen at v1 and the namespace belongs to
SiliconCompiler rather than to any one deployment: both implementations must
return the same URI or a client cannot branch across them. A slug names a *kind*
of failure and never one instance of it, which is why the discriminator lives in
an extension member -- ``limit``, ``feature``, ``violation`` -- rather than in
the slug. A member's value can be added after the freeze; a slug cannot.

Rows are registered here even where nothing raises them yet. An unraised row
costs a line; a missing row costs a major version, and two implementations that
each mint a slug for the same condition cost a client a second table.
'''

import re

from typing import Any, Dict, Optional

__all__ = ["DETAIL_MAX", "ERRORS", "TYPE_BASE", "ProblemError", "bound",
           "problem", "set_detail_max"]


# Fixed by the contract and identical on every deployment.
TYPE_BASE = "https://siliconcompiler.com/server-errors"


class _Error:
    '''One row of the registry.

    ``status`` is None for the three slugs that are never HTTP responses: they
    are ``type`` values on a job's or a node's ``error`` object.
    '''

    def __init__(self, slug: str, status: Optional[int], title: str,
                 members: tuple = ()):
        self.slug = slug
        self.status = status
        self.title = title
        self.members = members

    @property
    def uri(self) -> str:
        return f"{TYPE_BASE}/{self.slug}"


def _e(slug, status, title, members=()):
    return _Error(slug, status, title, members)


# The 34 slugs, in the contract's order. `title` is the part of the body that
# must be identical on every occurrence, so it is fixed here rather than written
# per raise site.
ERRORS: Dict[str, _Error] = {err.slug: err for err in (
    # -- ceilings ------------------------------------------------------------
    _e("limit-exceeded", 429, "Limit exceeded", ("limit",)),
    _e("node-limit-exceeded", 403, "Too many nodes in this flow", ("limit",)),
    _e("upload-too-large", 413, "Upload too large", ("limit",)),
    # 🆕 D117: `max_download_bytes`, which never refills -- so not
    # `limit-exceeded`, whose `Retry-After` a client would obey for ever.
    _e("download-too-large", 403, "Download too large", ("limit",)),
    _e("rate-limited", 429, "Too many requests"),
    _e("too-many-attempts", 429, "Too many attempts"),

    # -- entitlement and resolution -----------------------------------------
    _e("entitlement-denied", 403, "Not entitled to this resource",
       ("resource_kind", "resource")),
    _e("resource-unresolved", 422, "Could not resolve what this flow needs",
       ("resource_kind",)),
    # 🆕 D91, reshaped by D110: no live image satisfies the job's software
    # requirements. `unresolved` lists each failed one with its alternatives
    # and what is available; `reason` is "unavailable" or "combination".
    _e("software-unavailable", 422, "No image provides that software",
       ("reason", "unresolved")),
    # 🆕 D105, widened by D116: the job needs a resource -- any kind, a tool
    # included -- this deployment does not hold and cannot supply. It retired
    # `unsatisfiable-request`, which meant the same with the same members. Not
    # `resource-unresolved`, which is not knowing WHICH.
    _e("resource-unavailable", 422, "This server does not hold that resource",
       ("resource_kind", "resource")),
    # 🆕 D105, D115: crucible's, raised during extraction for restricted
    # material the caller may not upload. `detected` is "attribution" or
    # "content"; `member` the archive entry; `resource` only for a holder, so
    # it is not REQUIRED. Registered because the registry is the contract's;
    # this profile allows every upload (profile D26) and never raises it.
    _e("upload-forbidden", 422, "Upload of that resource is not allowed",
       ("resource_kind", "detected", "member")),
    _e("terms-not-accepted", 403, "Terms not accepted",
       ("terms_scope", "decision_url", "blocked_by")),
    _e("artifact-not-approved", 403, "Artifact not approved"),

    # -- the request itself --------------------------------------------------
    _e("version-skew", 422, "Unsupported client or software version"),
    _e("declared-mismatch", 422, "The manifest contradicts the descriptor"),
    _e("upload-digest-mismatch", 422, "Upload digest does not match"),
    _e("archive-rejected", 422, "Archive rejected", ("violation",)),
    _e("idempotency-key-reuse", 422, "Idempotency key reused with a different request"),
    _e("invalid-cursor", 400, "Invalid cursor"),
    _e("invalid-request", 400, "Invalid request"),
    _e("method-not-allowed", 405, "Method not allowed"),
    _e("unsupported-media-type", 415, "Unsupported media type"),
    _e("not-acceptable", 406, "Not acceptable"),

    # -- state ---------------------------------------------------------------
    _e("job-state-conflict", 409, "The job is not in a state that allows this"),
    _e("not-found", 404, "Not found"),
    _e("not-ready", 409, "Not ready yet", ("artifact_kind",)),
    _e("feature-unsupported", 501, "This deployment does not support that", ("feature",)),

    # -- credentials ---------------------------------------------------------
    _e("invalid-token", 401, "Invalid access token"),
    _e("invalid-dpop-proof", 401, "Invalid DPoP proof"),
    _e("insufficient-scope", 403, "Insufficient scope"),
    _e("session-ended", 401, "Session ended", ("reason",)),
    _e("insecure-transport", 426, "Upgrade required"),

    # -- never HTTP responses: these are `type` values on an error object -----
    _e("scheduler-lost", None, "The scheduler lost this job"),
    _e("run-failed", None, "The run failed"),
)}


# A `feature` value is itself a closed vocabulary, and it is wider than the
# published `features` list by exactly one: device_grant is advertised by
# grant_types_supported rather than by features, and it is the value this
# profile refuses POST /v1/auth/device with.
FEATURES = ("logs", "logs.stream", "logs.stream.job", "projects", "device_grant")

# Which archive rule was broken. Six conditions shared one slug and no
# discriminator before this member existed; two of them are published limits.
ARCHIVE_VIOLATIONS = ("member_count", "expanded_bytes", "ratio",
                      "link_member", "device_member", "traversal",
                      # A follow-up archive carrying anything but what was
                      # asked for (D124): it may not replace what the first
                      # archive carried after the server checked it.
                      "unrequested_member",
                      # A value the flow reads that the client should have
                      # sent -- the design, anything local or editable, or
                      # what was asked for -- and did not (D129).
                      "missing_member",
                      # A node's environment file outside its format, or for
                      # no node of the flow (D131).
                      "environment_file",
                      # A member whose extension a deployment's allowlist does
                      # not admit (contract D40). This profile has no such
                      # allowlist and never raises it; listed so the set is
                      # the contract's.
                      "extension")

# Why a session is over. All three are one client branch -- re-authenticate, and
# do NOT refresh.
SESSION_END_REASONS = ("revoked", "deactivated", "expired")


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


# How much of a `detail` reaches a caller, and it is bounded rather than
# trusted.
#
# 🔴 **Some details are built out of text this server did not write.** A tool's
# exception, a tarfile member's name, a manifest's parse error: every one of
# them can carry a path the CLIENT chose, and `detail` is published to anybody
# who can read the job. The contract's rule is that it does not echo
# unvalidated input; this is where that is enforced, once, for every refusal,
# because a rule applied at each call site is a rule somebody forgets at the
# next one.
#
# ⚠️ What is bounded is what is PUBLISHED. The full text still reaches the
# server's log, which has an entitled reader.
#
# ⚠️ **Characters and not bytes**, which is the one place this contract's usual
# `_bytes` is wrong: truncating UTF-8 by byte count splits a codepoint, and
# what comes out is not text.
#
# The default, and the deployment's `limits.max_detail_chars` replaces it at
# startup. A module-level number rather than a parameter because `problem()` is
# the funnel every refusal passes through, and threading config into it would
# put a way around the bound at every call site.
DETAIL_MAX = 300


def set_detail_max(characters: int) -> None:
    """Adopt the deployment's bound. Called once, at startup."""
    global DETAIL_MAX
    DETAIL_MAX = int(characters)


# This server's own internals, which a `detail` must never carry (D122): the
# paths it keeps its data and mounts under, and its host names. Set once, at
# startup.
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
    '''Take this server's internals out of a `detail` (D122).

    🔴 **A tool's exception text carries mount paths, hostnames and environment
    dumps**, and `detail` is published to whoever can read the job. The
    client's own input was already bounded; the server's is the half that
    leaks how the deployment is laid out.
    '''
    text = detail
    for path in _INTERNAL_PATHS:
        text = text.replace(path, "<server>")
    for name in _INTERNAL_NAMES:
        text = re.sub(rf"\b{re.escape(name)}\b", "<host>", text)
    for pattern, replacement in _CREDENTIALS:
        text = pattern.sub(replacement, text)
    return text


# Everything that is not text: NUL, the escapes a terminal acts on, and the
# rest of C0 and C1's delete. Tab, newline and carriage return are handled by
# the whitespace collapse instead, because they are ordinary in an exception.
_UNPRINTABLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def bound(detail: Optional[str]) -> Optional[str]:
    '''One line of somebody else's text, short enough to publish.

    Three things, and each is a different reader being protected: control
    characters go because a `detail` is printed to a terminal; newlines go
    because a refusal is one line and a multi-line one breaks every log that
    reads it; and the length goes because a stack trace pasted into a JSON
    body is not prose, it is a copy of the log in the wrong place.
    '''
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


def problem(slug: str, detail: Optional[str] = None,
            status: Optional[int] = None, **members) -> Dict[str, Any]:
    '''An RFC 9457 body.

    ``type`` and ``title`` come from the registry so that every occurrence of a
    condition is identical; ``detail`` is prose and may be reworded, which is
    why a client branches on ``type`` and never on it.

    🔴 `detail` is bounded here and nowhere else -- see `bound`. It is the one
    funnel every refusal passes through, which is what makes the rule hold for
    the call site nobody has written yet.
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
