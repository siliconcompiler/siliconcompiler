'''
Saying what went wrong, in three lines, without opening a URL.

The ``type`` URIs are static documentation and are identical on every
deployment, so the server cannot say anything specific through them -- which
makes the client the only place the specific failure can be rendered. It holds
the whole problem+json body, and most users never open the link.

The shape is: what failed, the extension member that says which, and the
trace id beside the page.
'''

from typing import Any, Dict, Optional

__all__ = ["RemoteError", "ServerProblem", "SessionEnded", "describe"]


class RemoteError(Exception):
    '''Something the client itself could not do.'''


class ServerProblem(RemoteError):
    '''The server refused, and said why in a way worth rendering.'''

    def __init__(self, problem: Dict[str, Any], status: int):
        self.problem = problem
        self.status = status
        super().__init__(describe(problem, status))

    @property
    def slug(self) -> Optional[str]:
        uri = self.problem.get("type")
        if not isinstance(uri, str):
            return None
        return uri.rstrip("/").rsplit("/", 1)[-1]

    def member(self, name: str) -> Any:
        '''An extension member -- `limit`, `feature`, `reason`, and the rest.'''
        return self.problem.get(name)


class SessionEnded(ServerProblem):
    '''The session is over: log in again, and do not refresh.

    Its own class because it is the one refusal whose answer is neither retry
    nor give up -- three stored reasons collapse to one client branch, which is
    why the contract gives them one slug and a `reason` member.
    '''

    @property
    def reason(self) -> str:
        return self.problem.get("reason") or "revoked"


# The extension members that say *which*, in the order they are worth reading.
# A slug names a kind of failure; one of these names the instance.
_DISCRIMINATORS = (
    "limit", "feature", "reason", "resource", "resource_kind",
    "violation", "artifact_kind", "terms_scope", "blocked_by",
)

# What a person should do about it. Keyed on the slug, because the slug is the
# API and `detail` is prose that may be reworded.
_NEXT_STEP = {
    "limit-exceeded": "Wait and retry; this allowance refills.",
    "node-limit-exceeded": "Send a smaller flow; waiting will not help.",
    "upload-too-large": "Reduce what is collected; waiting will not help.",
    "rate-limited": "Slow down and retry.",
    "entitlement-denied": "Ask an operator for access; waiting will not help.",
    "unsatisfiable-request": "This deployment cannot provide that at all.",
    "resource-unresolved": "Name the resource explicitly in your build script.",
    "terms-not-accepted": "Accept the agreement, then submit again.",
    "version-skew": "Install a version this server accepts.",
    "declared-mismatch": "The manifest and the descriptor disagree; "
                         "this is usually a client bug worth reporting.",
    "upload-digest-mismatch": "The upload did not arrive intact; submit again.",
    "archive-rejected": "The upload broke a limit on what an archive may hold.",
    "job-state-conflict": "This job is past the point where that is possible.",
    "not-found": "Check the id, or the job may have been deleted.",
    "not-ready": "Not available yet; retry.",
    "feature-unsupported": "This deployment does not have that and never will.",
    "insufficient-scope": "This credential may not do that; log in again.",
    "session-ended": "Log in again with sc-remote -configure.",
    "invalid-dpop-proof": "The server did not accept this machine's key.",
    "insecure-transport": "Use an https address for this server.",
    "idempotency-key-reuse": "A retry changed the request; start a new job.",
    "invalid-cursor": "Start the listing again.",
}


def describe(problem: Dict[str, Any], status: Optional[int] = None) -> str:
    '''Three lines: what failed, which one, and where to look.

    Tolerant by construction, because the bodies this has to render include the
    ones no handler produced -- a proxy's HTML 502 reaches here as a title and a
    status and nothing else.
    '''
    lines = []

    status = status or problem.get("status")
    title = problem.get("title") or "The server refused the request"
    detail = problem.get("detail")

    first = f"{title}" if status is None else f"{title} ({status})"
    lines.append(first if not detail else f"{first}: {detail}")

    named = [f"{name}: {problem[name]}"
             for name in _DISCRIMINATORS if problem.get(name) is not None]
    if named:
        lines.append("  " + ", ".join(named))

    slug = _slug(problem)
    step = _NEXT_STEP.get(slug) if slug else None
    if step:
        lines.append(f"  {step}")

    trailer = []
    if problem.get("trace_id"):
        trailer.append(f"trace {problem['trace_id']}")
    if isinstance(problem.get("type"), str):
        trailer.append(problem["type"])
    if trailer:
        lines.append("  " + "  ".join(trailer))

    return "\n".join(lines)


def _slug(problem: Dict[str, Any]) -> Optional[str]:
    uri = problem.get("type")
    if not isinstance(uri, str):
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1]
