'''
Saying what went wrong, in three lines, without opening a URL.

The ``type`` URIs are static documentation and are identical on every
deployment, so the server cannot say anything specific through them -- which
makes the client the only place the specific failure can be rendered. It holds
the whole problem+json body, and most users never open the link.

The shape is: what failed, the extension members that say which, and the
support reference -- the job id for anything about a job, else the trace id --
beside the page.
'''

import re

from typing import Any, Dict, Optional

__all__ = ["RemoteError", "ServerProblem", "SessionEnded", "describe",
           "NO_NODE_FAILED", "clean"]


class RemoteError(Exception):
    '''Something the client itself could not do.'''


class ServerProblem(RemoteError):
    '''The server refused, and said why in a way worth rendering.'''

    def __init__(self, problem: Dict[str, Any], status: int,
                 help_url: Optional[str] = None, next_step: Optional[str] = None,
                 job_id: Optional[str] = None, titles: Optional[Dict[str, str]] = None,
                 retry_after: Optional[float] = None):
        self.problem = problem
        self.status = status
        self.help_url = help_url
        # Seconds, never below 1, where the refusal said when to ask again.
        self.retry_after = retry_after
        super().__init__(describe(problem, status, next_step=next_step, help_url=help_url,
                                  job_id=job_id, titles=titles))

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
# A slug names a kind of failure; one of these names the instance. `blocked_by`
# has lines of its own.
_DISCRIMINATORS = (
    "resource", "keypath", "limit", "reason", "feature", "artifact_kind", "job_ids",
    "resource_kind", "detected", "member", "step", "index", "job_id",
)

# What a person should do about it, from the registry's client column. Keyed on
# the slug, because the slug is the API and `detail` is prose that may be
# reworded. An unknown slug, or an unknown `reason`, falls to the status.
_NEXT_STEP = {
    "limit-exceeded": "Wait and retry; this allowance refills.",
    "node-limit-exceeded": "Send a smaller flow.",
    "upload-too-large": "Send a smaller archive or request; waiting will not help.",
    "rate-limited": "Slow down and retry.",
    "entitlement-denied": "Ask for a grant; waiting will not help.",
    "account-not-provisioned": "Ask an administrator to provision your account.",
    "not-permitted": "You cannot do that to this job: only its owner, and for a "
                     "cancel or a delete a project owner, may.",
    "download-too-large": "It is larger than this account may download over "
                          "the API; the web portal is the way to it.",
    "software-unavailable": "Ask for a version this server has, or ask its "
                            "operator for the one you need.",
    "artifact-not-approved": "It is held back from download here; ask for access "
                             "where there is a link to.",
    "resource-unavailable": "This server does not hold it and cannot be sent "
                            "it: use one it holds, or ask its operator.",
    "upload-forbidden": "That resource may not be uploaded here; use this "
                        "server's copy.",
    "resource-unresolved": "Set the PDK in your build script.",
    "terms-not-accepted": "Sign each document below, then try again.",
    "declared-mismatch": "The manifest and the job disagree; this is usually a "
                         "client bug worth reporting.",
    "upload-digest-mismatch": "The upload did not arrive intact; upload it again "
                              "and submit.",
    "archive-rejected": "Fix what the reason names, in a new job.",
    "job-state-conflict": "This job is past the point where that is possible.",
    "not-found": "Check the id, or the job may have been deleted.",
    "not-ready": "Not available yet; retry.",
    "feature-unsupported": "This deployment does not offer that now.",
    "insufficient-scope": "This credential may not do that.",
    "session-ended": "Log in again with sc-remote -configure.",
    "invalid-dpop-proof": "The server did not accept this machine's key.",
    "insecure-transport": "Use an https address for this server.",
    "idempotency-key-reuse": "A retry changed the request; start a new job.",
    "invalid-cursor": "Start the listing again.",
    "prior-results-unavailable": "Run from an earlier step, or name a job of your "
                                 "own whose results can be used.",
    # Never HTTP responses: `type` values on a job's or a node's error object,
    # which is where a user meets them.
    "run-failed": "It will fail the same way unchanged. Read the failing node's "
                  "log in the build directory this fetched, and change something "
                  "before you resubmit.",
    "run-interrupted": "The environment ended the run, not the job: resubmitting "
                       "unchanged may work.",
    "staging-failed": "The server could not get the job ready; submit again later.",
    # Retried once in the transport with the nonce the server gave; seen here
    # only when that retry was refused too.
    "dpop-nonce-required": "The server wanted a fresh proof and refused the retry; "
                           "try again.",
}


def _by_status(status: Optional[int]) -> Optional[str]:
    '''🔴 An unknown `type` is acted on by its status, as an untyped failure
    is.'''
    if not isinstance(status, int):
        return None
    if status >= 500:
        return "The server failed; try again later."
    if status == 429:
        return "Wait and retry."
    if status == 401:
        return "Log in again with sc-remote -configure."
    if status == 404:
        return "Check the id, or it may have been deleted."
    if status >= 400:
        return "The server refused the request; retrying it unchanged will not help."
    return None


# `archive-rejected` is one slug over many mistakes. Keyed on `reason`.
_NEXT_STEP_BY_REASON = {
    "missing_member": "The upload left out a file the flow reads; that is a "
                      "client bug, or a task whose requirements miss a file.",
    "unrequested_member": "The archive carried something the server did not ask for; "
                          "that is a client bug.",
    "python_package": "An uploaded wheel was refused; the client builds every "
                      "wheel, so that is a client bug.",
    "breakpoint": "Clear option,breakpoint: nobody is at a remote run.",
    "interactive_task": "Remove the task that opens a window: nobody is at a "
                        "remote run.",
}

# A time or memory limit named in a run's `detail`.
_LIMIT_IN_DETAIL = re.compile(r"\b(time|memory|wall[- ]?clock|oom)\b", re.IGNORECASE)

# 🔴 What to say instead when the run failed and no NODE did. Pointing at *the
# failing node's log* when there is no failing node sends a person looking for
# a file that does not exist -- and it is not the rare case: a flow that dies
# before its first node, or during setup, fails with every node `cancelled`
# and none of them `failed`. The run's own log is the answer, and it arrives
# with the results like everything else.
NO_NODE_FAILED = ("No node failed -- the run itself did. Read remote-job.log "
                  "in the job directory this fetched.")


def _unresolved(entry: Dict[str, Any]) -> str:
    wanted = " or ".join(str(one) for one in entry.get("requirement") or []) \
        or "any version"
    return (f"{entry.get('name', '?')} {wanted} "
            f"(available: {_member(entry.get('available') or [])})")


def _member(value) -> str:
    '''One extension member as a person reads it. A list -- `available` is
    one -- is its items, and an empty one says so rather than printing `[]`.'''
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value) if value else "none"
    return str(value)


def _keypath(value) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(part) for part in value)
    return str(value)


def describe(problem: Dict[str, Any], status: Optional[int] = None,
             next_step: Optional[str] = None,
             help_url: Optional[str] = None,
             job_id: Optional[str] = None,
             titles: Optional[Dict[str, str]] = None) -> str:
    '''Three lines: what failed, which one, and where to look.

    Tolerant by construction, because the bodies this has to render include the
    ones no handler produced -- a proxy's HTML 502 reaches here as a title and a
    status and nothing else.

    ``next_step`` overrides the table. A slug names a kind of failure, so the
    advice keyed on it is right for the kind and can be wrong for the instance;
    a caller that knows more about this occurrence than the slug does says so
    here.

    ``help_url`` is the page the SERVER named for this error (`Link`
    `rel="help"`), and it is printed in place of the `type` URI: it is the copy
    that answers from here, where the public page may not. The `type` is still
    what every branch is taken on.

    ``job_id`` is the support reference for anything about a job; without one
    it is the refusal's `trace_id`. ``titles`` maps a terms id to its title in
    `GET /v1/me`'s `terms`, for a `blocked_by` entry with no link.
    '''
    lines = []

    status = status or problem.get("status")
    title = clean(problem.get("title") or "The server refused the request")
    detail = clean(problem.get("detail")) if problem.get("detail") else None

    first = f"{title}" if status is None else f"{title} ({status})"
    lines.append(first if not detail else f"{first}: {detail}")

    # A keypath as SiliconCompiler prints one, `tool,x,task,y,dataroot,z`.
    named = [f"{name}: "
             + clean(_keypath(problem[name]) if name == "keypath" else _member(problem[name]))
             for name in _DISCRIMINATORS if problem.get(name) is not None]
    if named:
        lines.append("  " + ", ".join(named))

    # `software-unavailable` names every requirement that failed, each with
    # its alternatives and what the server has instead -- one line apiece.
    for entry in problem.get("unresolved") or []:
        if isinstance(entry, dict):
            lines.append("  " + clean(_unresolved(entry)))

    for line in blocked_lines(problem.get("blocked_by"), titles):
        lines.append(f"  {line}")

    slug = _slug(problem)
    step = next_step or _advice(slug, problem, status)
    if step:
        lines.append(f"  {step}")

    trailer = []
    if job_id:
        trailer.append(f"job {job_id}")
    elif problem.get("trace_id"):
        trailer.append(f"trace {clean(str(problem['trace_id']))}")
    if help_url:
        trailer.append(help_url)
    elif isinstance(problem.get("type"), str):
        trailer.append(problem["type"])
    if trailer:
        lines.append("  " + "  ".join(trailer))

    return "\n".join(lines)


# A capability refused (surface *Who may use it: three capabilities*): each is
# a step up in whose code the deployment runs, and each has a way round short
# of the grant.
_CAPABILITY_STEP = {
    "python-env": "Ask the deployment for the python-env grant. A job whose only "
                  "Python is its own modules needs none.",
    "python-wheels": "Ask the deployment for the python-wheels grant, or publish the "
                     "package to one of its indexes.",
}


def _advice(slug: Optional[str], problem: Dict[str, Any],
            status: Optional[int] = None) -> Optional[str]:
    '''The registry's client action for this type, refined by `reason`.

    An unknown `reason` acts on the type alone, and an unknown type -- or none,
    for a body no handler produced -- acts on the status.'''
    if slug not in _NEXT_STEP:
        return _by_status(status)
    if slug == "archive-rejected":
        return _NEXT_STEP_BY_REASON.get(problem.get("reason")) or _NEXT_STEP[slug]
    if slug == "run-failed":
        detail = str(problem.get("detail") or "")
        if _LIMIT_IN_DETAIL.search(detail):
            return ("It hit a limit the server sets, and will fail the same way: "
                    "change what the detail names before you resubmit.")
    if slug == "software-unavailable" and any(
            isinstance(entry, dict) and entry.get("name") == "python"
            for entry in problem.get("unresolved") or []):
        # The interpreter: nothing the user chooses in the job changes it
        # (surface D293).
        return ("No image here runs the Python this machine does. The server's "
                "operator would have to add one; until then, run the job from a "
                "Python it has.")
    if slug == "entitlement-denied" and problem.get("resource_kind") == "capability":
        return _CAPABILITY_STEP.get(problem.get("resource")) or \
            "Ask the deployment for that grant; waiting will not help."
    if slug == "session-ended" and problem.get("reason") == "reused":
        return ("Your credentials were used elsewhere. Rotate this machine's key "
                "with `sc-remote -rotate_key`, then log in again.")
    return _NEXT_STEP[slug]


def blocked_lines(blocked_by, titles: Optional[Dict[str, str]] = None) -> list:
    '''One line per document in a `blocked_by` map: its id and signing link, or
    its title where the entry carries no link. Nothing is opened here.'''
    if not isinstance(blocked_by, dict):
        return []
    lines = []
    for terms_id, entry in blocked_by.items():
        name = clean(str(terms_id))
        url = entry.get("url") if isinstance(entry, dict) else None
        if isinstance(url, str) and url:
            lines.append(f"sign {name}: {clean(url)}")
        else:
            title = (titles or {}).get(terms_id)
            lines.append(f"sign {clean(title) if title else name} "
                         "(no link is available; ask the operator where)")
    return lines


# Everything a terminal acts on except newline, tab and colour (SGR).
_CONTROL = re.compile(r"\x1b(?!\[[0-9;]*m)|[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f\x80-\x9f]")


def clean(text: Optional[str]) -> str:
    '''Server text made safe for a terminal: control characters stripped,
    except newline, tab and colour (surface §20, the last bullet).'''
    if text is None:
        return ""
    text = str(text)
    # An escape that is not colour loses its introducer, and the rest of a
    # colour sequence is left alone.
    return _CONTROL.sub("", text)


def _slug(problem: Dict[str, Any]) -> Optional[str]:
    uri = problem.get("type")
    if not isinstance(uri, str):
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1]
