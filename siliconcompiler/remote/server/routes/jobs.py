'''
Endpoints 13 to 19: submission and control, plus the signed upload ``PUT``.

Thin on purpose: every ordering rule, refusal and transition is in
:mod:`siliconcompiler.remote.server.jobs`; here is only verb, path and scope.
'''

import time

import flask

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.routes import next_page
from siliconcompiler.remote.server.routes.auth import public_url, require
from siliconcompiler.remote.server.routes.errorpages import help_link
from siliconcompiler.remote.server.state.storage import SignatureError
from siliconcompiler.remote.server.state.store import PENDING_STATES

__all__ = ["blueprint"]


blueprint = flask.Blueprint("jobs", __name__)


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _private(body, status: int = 200, headers=None):
    response = flask.jsonify(body)
    response.status_code = status
    response.headers["Cache-Control"] = "private, no-store"
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def _body(required: bool = True):
    '''The request's JSON, or a problem+json refusal saying which mistake it
    is, never `get_json()`'s HTML page.'''
    if flask.request.mimetype not in ("application/json", ""):
        raise ProblemError(
            "unsupported-media-type",
            detail=f"this endpoint takes application/json, not {flask.request.mimetype}")

    body = flask.request.get_json(silent=True)
    if body is None:
        if required:
            raise ProblemError("invalid-request", detail="a JSON body is required")
        return {}
    if not isinstance(body, dict):
        raise ProblemError("invalid-request", detail="the body must be a JSON object")
    return body


def _idempotency_key():
    key = flask.request.headers.get("Idempotency-Key")
    if key is None:
        return None
    if not key or len(key) > 200:
        raise ProblemError("invalid-request",
                           detail="Idempotency-Key is at most 200 characters")
    return key


@blueprint.route("/v1/jobs", methods=["POST"])
@require("jobs:write")
def create(session):
    '''Endpoint 13: no payload, so a job can be refused before bytes move.'''
    body, status = _jobs().create(session, _body(), _idempotency_key())

    # 🔴 The job object itself, so `upload_sources` is one member wherever the
    # server asks.
    response = _private(body, status)
    if status == 201:
        response.headers["Location"] = f"/v1/jobs/{body['id']}"
    return response


@blueprint.route("/v1/jobs/<job_id>/upload-grant", methods=["POST"])
@require("jobs:write")
def upload_grant(session, job_id):
    '''Endpoint 14: issue or re-issue the grant; 200, since a re-issue
    creates nothing.'''
    return _private(_jobs().grant(session, job_id, public_url(""),
                                  _body(required=False)))


@blueprint.route("/v1/jobs/<job_id>/submit", methods=["POST"])
@require("jobs:write")
def submit(session, job_id):
    '''Endpoint 15: the job is ready to run (the order is the job service's).'''
    # `{}`: an empty body and a JSON `{}` alike (surface D306).
    return _private(_jobs().submit(session, job_id, _body(required=False),
                                   _idempotency_key()), 202)


@blueprint.route("/v1/jobs", methods=["GET"])
@require("jobs:read")
def listing(session):
    '''Endpoint 16; no `Link` on the last page.'''
    from siliconcompiler.remote.server.errors import only_query

    only_query(flask.request.args, ("state", "flow", "design", "jobname", "project",
                                    "mine", "archived", "terminal", "limit", "cursor"),
               "GET /v1/jobs")
    items, cursor = _jobs().listing(session, flask.request.args)

    headers = {"Link": next_page("/v1/jobs", cursor)} if cursor else {}

    return _private({"items": items}, headers=headers)


@blueprint.route("/v1/jobs/<job_id>", methods=["GET"])
@require("jobs:read")
def get(session, job_id):
    '''Endpoint 17, with `Retry-After` while the job is still going.'''
    job = _jobs().get(session, job_id)

    headers = {}
    if not job["terminal"]:
        headers["Retry-After"] = str(
            flask.current_app.config["SC_CONFIG"]["poll_interval_seconds"])

    # A failed job's error type gets its page, as a refusal's does.
    link = help_link((job.get("error") or {}).get("type"))
    if link:
        headers["Link"] = link

    return _private(job, headers=headers)


@blueprint.route("/v1/jobs/<job_id>/cancel", methods=["POST"])
@require("jobs:write")
def cancel(session, job_id):
    '''Endpoint 18. The body is optional, so a Ctrl-C can be expressed.'''
    reason = _body(required=False).get("reason")
    return _private(_jobs().cancel(session, job_id, reason), 202)


@blueprint.route("/v1/jobs/<job_id>", methods=["DELETE"])
@require("jobs:delete")
def delete(session, job_id):
    '''Endpoint 19: idempotent, and the row survives it.'''
    _jobs().delete(session, job_id)

    response = flask.make_response("", 204)
    response.headers["Cache-Control"] = "private, no-store"
    return response


######################################################################
# Not an endpoint: the target of the upload grant
######################################################################

@blueprint.route("/storage/upload/<job_id>", methods=["PUT"])
def upload(job_id):
    '''Where the bytes actually go: this deployment's stand-in for a presigned
    PUT, outside ``/v1``.

    No session: the signature names one job, expires and carries the byte
    ceiling, and the digest at submit decides what runs.
    '''
    storage = flask.current_app.config["SC_STORAGE"]
    store = flask.current_app.config["SC_STORE"]

    args = flask.request.args
    try:
        ceiling = storage.verify_upload(
            job_id, args.get("max_bytes"), args.get("expires"), args.get("sig"),
            time.time())
    except SignatureError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    job = store.one("SELECT state, deleted_at FROM jobs WHERE id = ?", (job_id,))
    if job is None or job["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")
    if job["state"] not in PENDING_STATES:
        raise ProblemError(
            "job-state-conflict",
            detail=f"a job in {job['state']} takes no upload")

    try:
        size, digest = storage.receive(job_id, flask.request.stream, ceiling)
    except ValueError as e:
        raise ProblemError("upload-too-large", detail=str(e)) from None

    # A courtesy, not a credential.
    response = flask.jsonify({"size_bytes": size, "digest": digest})
    response.headers["Cache-Control"] = "no-store"
    return response
