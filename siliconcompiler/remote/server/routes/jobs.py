'''`/v1/jobs`: the job path, and the signed upload ``PUT`` it hands out.'''

from urllib.parse import urlencode

import flask

from siliconcompiler.remote.server import config
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs import RETRY_AFTER, refuse_undefined
from siliconcompiler.remote.server.routes.auth import require_session

__all__ = ["blueprint"]


blueprint = flask.Blueprint("jobs", __name__)

_CREATE = ("design", "jobname", "project", "run_hash", "continues_from", "python_packages",
           "descriptor")


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _body(defines=()) -> dict:
    '''The request's JSON, or nothing for an empty body: every body here is optional or
    checked field by field, and holds only the members it ``defines``.'''
    if not flask.request.get_data(cache=True):
        return {}
    # Not silent: a body that is not JSON is refused, not taken for no body.
    body = flask.request.get_json()
    if not isinstance(body, dict):
        raise ProblemError("invalid-request", detail="the body must be a JSON object")
    refuse_undefined(body, defines, "this request")
    return body


@blueprint.route("/v1/jobs", methods=["POST"])
@require_session
def create(session):
    job = _jobs().create(session, _body(_CREATE), flask.request.headers.get("Idempotency-Key"))
    response = flask.jsonify(job)
    response.status_code = 201
    response.headers["Location"] = f"/v1/jobs/{job['id']}"
    return response


def origin() -> str:
    '''Where a signed URL this server hands out points: the first public origin, else this host.'''
    origins = flask.current_app.config["SC_PUBLIC_ORIGINS"]
    return (origins[0] if origins else flask.request.host_url).rstrip("/")


@blueprint.route("/v1/jobs/<job_id>/upload-grant", methods=["POST"])
@require_session
def upload_grant(session, job_id):
    return flask.jsonify(_jobs().grant(session, job_id, _body(("size_bytes", "digest")),
                                       origin()))


@blueprint.route("/storage/upload/<job_id>", methods=["PUT"])
def upload(job_id):
    '''No session: the signature names one job and the byte count, and expires.'''
    flask.request.max_content_length = config.LIMITS["max_upload_bytes"]
    _jobs().receive(job_id, flask.request.args, flask.request.stream)
    return "", 204


@blueprint.route("/v1/jobs/<job_id>/submit", methods=["POST"])
@require_session
def submit(session, job_id):
    _body()
    response = flask.jsonify(_jobs().submit(session, job_id))
    response.status_code = 202
    return response


def page(items, cursor):
    '''A listing's body, with a ``Link`` to the next page where there is one.'''
    response = flask.jsonify({"items": items})
    if cursor:
        query = [(name, value) for name, value in flask.request.args.items(multi=True)
                 if name != "cursor"]
        response.headers["Link"] = \
            f'<{flask.request.path}?{urlencode([*query, ("cursor", cursor)])}>; rel="next"'
    return response


@blueprint.route("/v1/jobs", methods=["GET"])
@require_session
def listing(session):
    return page(*_jobs().listing(session, flask.request.args))


@blueprint.route("/v1/jobs/<job_id>", methods=["GET"])
@require_session
def get(session, job_id):
    job = _jobs().get(session, job_id)
    response = flask.jsonify(job)
    if not job["terminal"]:
        response.headers["Retry-After"] = str(RETRY_AFTER)
    return response


@blueprint.route("/v1/jobs/<job_id>/cancel", methods=["POST"])
@require_session
def cancel(session, job_id):
    response = flask.jsonify(_jobs().cancel(session, job_id, _body(("reason",)).get("reason")))
    response.status_code = 202
    return response


@blueprint.route("/v1/jobs/<job_id>", methods=["DELETE"])
@require_session
def delete(session, job_id):
    _jobs().delete(session, job_id)
    return "", 204
