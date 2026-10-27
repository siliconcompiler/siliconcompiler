'''
Endpoints 20, 21 and 22: a job's artifacts and its live logs.

None carries bytes. The listing is JSON; a fetch and a log answer `303` to a
signed URL on this host, whose signature is that route's only credential.
'''

import time

from urllib.parse import quote

import flask

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs import NODE_TERMINAL
from siliconcompiler.remote.server.outputs import artifacts, logstream
from siliconcompiler.remote.server.routes.auth import require_session
from siliconcompiler.remote.server.routes.jobs import origin, page

__all__ = ["blueprint"]


blueprint = flask.Blueprint("results", __name__)

DOWNLOAD_SECONDS = 300


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _see_other(url: str):
    response = flask.make_response("", 303)
    response.headers["Location"] = url
    return response


def _verified(*parts) -> int:
    '''The expiry of a signed URL whose signature covers ``parts``; refused otherwise.'''
    expires = flask.request.args.get("expires", "")
    if not _jobs().storage.verify(flask.request.args.get("sig"), *parts, expires) \
            or time.time() > int(expires):
        raise ProblemError("invalid-request", detail="the signed URL is not valid")
    return int(expires)


@blueprint.route("/v1/jobs/<job_id>/artifacts", methods=["GET"])
@require_session
def listing(session, job_id):
    return page(*_jobs().artifacts(session, job_id, flask.request.args))


@blueprint.route("/v1/jobs/<job_id>/artifacts/<artifact_id>", methods=["GET"])
@require_session
def fetch(session, job_id, artifact_id):
    _jobs().artifact(session, job_id, artifact_id)
    expires = int(time.time()) + DOWNLOAD_SECONDS
    signature = _jobs().storage.sign("download", job_id, artifact_id, expires)
    return _see_other(f"{origin()}/storage/artifact/{job_id}/{artifact_id}"
                      f"?expires={expires}&sig={signature}")


@blueprint.route("/storage/artifact/<job_id>/<artifact_id>", methods=["GET"])
def download(job_id, artifact_id):
    _verified("download", job_id, artifact_id)
    jobs = _jobs()
    path = jobs.storage.artifact_dir(job_id) / artifact_id
    if not path.is_file() or not jobs.store.one(
            "SELECT 1 FROM artifacts WHERE id = ? AND job_id = ?", (artifact_id, job_id)):
        raise ProblemError("not-found", detail="no such artifact")

    # A job's bytes, on this host: never rendered, whatever they claim to be.
    response = flask.send_file(path, mimetype="application/gzip", as_attachment=True,
                               download_name=f"{artifact_id}.gz")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


@blueprint.route("/v1/jobs/<job_id>/logs", methods=["GET"])
@require_session
def logs(session, job_id):
    '''A node's live log. A finished node's stream sends what is left and ends, so a
    late request and a node finishing mid-request are one case.'''
    step, index = flask.request.args.get("step"), flask.request.args.get("index")
    if bool(step) != bool(index):
        raise ProblemError("invalid-request", detail="step and index go together")
    if not step:
        raise ProblemError("feature-unsupported", feature="logs.stream.job",
                           detail="this server streams one node's log at a time")

    jobs = _jobs()
    if jobs.owned(session, job_id)["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")
    state = jobs.node_state(job_id, step, index)
    if state is None:
        raise ProblemError("not-found", detail="no such node")
    if state in ("pending", "queued"):
        raise ProblemError("not-ready", artifact_kind="logs", headers={"Retry-After": "1"},
                           detail="this node has not started")
    if state in NODE_TERMINAL and not artifacts.log_artifact(jobs.store, job_id, step, index):
        raise ProblemError("not-found", detail="this node kept no log")

    # No later than the token that asked, so a revocation reaches an open stream.
    expires = int(session.access_expires_at)
    signature = jobs.storage.sign("stream", job_id, step, index, expires)
    return _see_other(f"{origin()}/stream/logs/{job_id}/{quote(step)}/{quote(index)}"
                      f"?expires={expires}&sig={signature}")


@blueprint.route("/stream/logs/<job_id>/<step>/<index>", methods=["GET"])
def stream(job_id, step, index):
    '''Where `/logs` points: the node's log as server-sent events. `text/event-stream`
    is the only sign of a live stream, since a node can finish before the connect.'''
    deadline = _verified("stream", job_id, step, index)
    jobs = _jobs()
    job = jobs.row(job_id)
    if job is None or job["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")

    tree = jobs.root(job["user_id"], job_id) / job["design"] / job["jobname"]
    start = logstream.resume_from(flask.request.headers.get("Last-Event-ID"))

    def frames():
        try:
            yield from logstream.events(
                tree, tree / step / index / f"sc_{step}_{index}.log", step, index,
                lambda: jobs.node_state(job_id, step, index),
                lambda: artifacts.log_artifact(jobs.store, job_id, step, index),
                start, deadline)
        finally:
            # This runs after the request's teardown, on the thread that served it.
            jobs.store.release()

    response = flask.Response(frames(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Accel-Buffering"] = "no"
    return response
