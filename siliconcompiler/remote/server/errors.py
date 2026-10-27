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

__all__ = ["ERRORS", "TYPE_BASE", "OAuthError", "ProblemError", "problem"]


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
    # `limit-exceeded`, whose `Retry-After` a client would obey for ever. This
    # profile sets no download ceiling and never raises it.
    _Error("download-too-large", 403, "Download too large", ("limit",)),
    _Error("rate-limited", 429, "Too many requests"),

    # A grant's refusal. This profile has no grants and never raises it.
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
    '''A refusal at `/v1/auth/token`, in RFC 6749 section 5.2's shape; transport
    refusals raised before OAuth processing starts stay `ProblemError`.'''

    def __init__(self, error: str, description: Optional[str] = None,
                 reason: Optional[str] = None, status: int = 400):
        self.error = error
        self.description = description
        self.reason = reason
        self.status = status
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

        if self.error.status is None and status is None:
            raise ValueError(
                f"{slug} is never an HTTP response; it is a type on an error object")
        self.status = status or self.error.status

        super().__init__(detail or self.error.title)

    def body(self) -> Dict[str, Any]:
        return problem(self.error.slug, detail=self.detail,
                       status=self.status, **self.members)


# Characters, not bytes: cutting UTF-8 by bytes splits a codepoint.
DETAIL_MAX = 300

# NUL, the rest of C0, DEL and C1, whose U+009B is a one-character terminal escape.
_UNPRINTABLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def bound(detail: Optional[str]) -> Optional[str]:
    '''One line of somebody else's text, short enough to publish: no control
    characters (it reaches a terminal), no newlines, at most `DETAIL_MAX`.'''
    if not detail:
        return detail

    text = " ".join(_UNPRINTABLE.sub("", detail).split())
    return text if len(text) <= DETAIL_MAX else text[:DETAIL_MAX] + "..."


def problem(slug: str, detail: Optional[str] = None,
            status: Optional[int] = None, **members) -> Dict[str, Any]:
    '''An RFC 9457 body. ``type`` and ``title`` come from the registry; a
    client branches on ``type``, never on the rewordable ``detail``.'''
    err = ERRORS[slug]

    body: Dict[str, Any] = {"type": err.uri, "title": err.title}

    resolved = status or err.status
    if resolved is not None:
        body["status"] = resolved
    if detail:
        body["detail"] = bound(detail)

    body.update(members)
    return body
