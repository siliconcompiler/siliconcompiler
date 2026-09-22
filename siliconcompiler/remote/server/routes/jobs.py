'''
Endpoints 13 to 19: submission and control.

The handlers here are thin on purpose. Every ordering rule, every refusal and
every state transition is in :mod:`siliconcompiler.remote.server.jobs`, because
those are the parts a second implementation has to agree with; what is left in
this file is which verb goes where and which scope guards it.

One route is not an endpoint: the signed ``PUT`` the upload grant points at. It
carries no ``Authorization`` header and no DPoP proof, because that is what a
presigned URL is -- the signature is the credential. It lives outside ``/v1`` so
that the version prefix stays exactly the contract's surface.
'''

import time

import flask

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.routes.auth import require
from siliconcompiler.remote.server.storage import SignatureError

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
    '''The request's JSON, or a refusal that names which problem it is.

    A body that is absent and a body that is malformed are different mistakes,
    and `get_json()`'s own error is a Flask HTML page rather than problem+json.
    '''
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
    '''Endpoint 13.

    A small body and no payload: two authoritative members, an optional
    descriptor and nothing that moves. The bytes are endpoint 14's business,
    which is what lets a job be refused before they move at all.
    '''
    body, status = _jobs().create(session, _body(), _idempotency_key())

    response = _private({
        "id": body["id"],
        "state": body["state"],
        "project": None,
        "created_at": body["created_at"],
    }, status)
    if status == 201:
        response.headers["Location"] = f"/v1/jobs/{body['id']}"
    return response


@blueprint.route("/v1/jobs/<job_id>/upload-grant", methods=["POST"])
@require("jobs:write")
def upload_grant(session, job_id):
    '''Endpoint 14: issue or re-issue the grant.

    200 rather than 201, because re-issue is the point of the endpoint: the row
    already exists, and a 201 on the second call claims a creation that did not
    happen. Without this call a grant that expired left the job in a state with
    no way back.
    '''
    return _private(_jobs().grant(session, job_id, flask.request.url_root))


@blueprint.route("/v1/jobs/<job_id>/submit", methods=["POST"])
@require("jobs:write")
def submit(session, job_id):
    '''Endpoint 15: the job is ready to run.

    The digest is checked against what storage reports before anything is
    extracted. That sequencing is the one detail in the contract that is a
    security property, and it is enforced in the job service rather than here.
    '''
    return _private(_jobs().submit(session, job_id, _body(), _idempotency_key()), 202)


@blueprint.route("/v1/jobs", methods=["GET"])
@require("jobs:read")
def listing(session):
    '''Endpoint 16.

    `items` may be `[]`, and the `Link` header is absent on the last page rather
    than present and empty.
    '''
    items, cursor = _jobs().listing(session, flask.request.args)

    headers = {}
    if cursor:
        query = flask.request.args.to_dict()
        query["cursor"] = cursor
        query_string = "&".join(f"{k}={v}" for k, v in query.items())
        headers["Link"] = f'</v1/jobs?{query_string}>; rel="next"'

    return _private({"items": items}, headers=headers)


@blueprint.route("/v1/jobs/<job_id>", methods=["GET"])
@require("jobs:read")
def get(session, job_id):
    '''Endpoint 17.

    `Retry-After` while the job is still going, so a client never guesses an
    interval. The old client took one from a server field at the start of the
    run and used it until the end.
    '''
    job = _jobs().get(session, job_id)

    headers = {}
    if not job["terminal"]:
        headers["Retry-After"] = str(
            flask.current_app.config["SC_CONFIG"]["poll_interval_seconds"])

    return _private(job, headers=headers)


@blueprint.route("/v1/jobs/<job_id>/cancel", methods=["POST"])
@require("jobs:write")
def cancel(session, job_id):
    '''Endpoint 18.

    The body is optional in both directions: a client may omit it, and this must
    accept the call without one. Requiring a reason would make a Ctrl-C
    impossible to express.
    '''
    reason = _body(required=False).get("reason")
    return _private(_jobs().cancel(session, job_id, reason), 202)


@blueprint.route("/v1/jobs/<job_id>", methods=["DELETE"])
@require("jobs:write")
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
    '''Where the bytes actually go.

    Deliberately outside ``/v1``: it is this deployment's storage, standing in
    for the presigned PUT another deployment would hand out, and the contract's
    surface is the eighteen endpoints rather than wherever a grant points.

    No scope guards it and no session is looked up. The signature names one job,
    expires, and carries the byte ceiling the grant was issued for -- and the
    digest at submit is what finally decides whether these are the bytes the
    caller meant to send.
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
    if job["state"] not in ("created", "awaiting_input"):
        raise ProblemError(
            "job-state-conflict",
            detail=f"a job in {job['state']} takes no upload")

    try:
        size, digest = storage.receive(job_id, flask.request.stream, ceiling)
    except ValueError as e:
        raise ProblemError("upload-too-large", limit="max_upload_bytes",
                           detail=str(e)) from None

    # The digest is returned as a courtesy, not as a credential: the client
    # asserts its own at submit and the server compares against what it reads
    # back off the object, so a client that trusted this one would be comparing
    # the server's answer with the server's answer.
    response = flask.jsonify({"bytes": size, "digest": digest})
    response.headers["Cache-Control"] = "no-store"
    return response
