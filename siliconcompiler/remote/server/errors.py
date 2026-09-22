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

from typing import Any, Dict, Optional

__all__ = ["ERRORS", "TYPE_BASE", "ProblemError", "problem"]


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


# The 31 slugs, in the contract's order. `title` is the part of the body that
# must be identical on every occurrence, so it is fixed here rather than written
# per raise site.
ERRORS: Dict[str, _Error] = {err.slug: err for err in (
    # -- ceilings ------------------------------------------------------------
    _e("limit-exceeded", 429, "Limit exceeded", ("limit",)),
    _e("node-limit-exceeded", 403, "Too many nodes in this flow", ("limit",)),
    _e("upload-too-large", 413, "Upload too large", ("limit",)),
    _e("rate-limited", 429, "Too many requests"),
    _e("too-many-attempts", 429, "Too many attempts"),

    # -- entitlement and resolution -----------------------------------------
    _e("entitlement-denied", 403, "Not entitled to that resource",
       ("resource_kind", "resource")),
    _e("unsatisfiable-request", 422, "This server cannot provide that",
       ("resource_kind", "resource")),
    _e("resource-unresolved", 422, "Could not resolve what this flow needs",
       ("resource_kind",)),
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
FEATURES = ("logs", "logs.stream", "projects", "device_grant")

# Which archive rule was broken. Six conditions shared one slug and no
# discriminator before this member existed; two of them are published limits.
ARCHIVE_VIOLATIONS = ("member_count", "expanded_bytes", "ratio",
                      "link_member", "device_member", "traversal")

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


def problem(slug: str, detail: Optional[str] = None,
            status: Optional[int] = None, **members) -> Dict[str, Any]:
    '''An RFC 9457 body.

    ``type`` and ``title`` come from the registry so that every occurrence of a
    condition is identical; ``detail`` is prose and may be reworded, which is
    why a client branches on ``type`` and never on it.
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
        body["detail"] = detail

    body.update(members)
    return body
