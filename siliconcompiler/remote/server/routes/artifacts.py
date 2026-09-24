'''
Endpoints 20, 21 and 22: getting the results out.

🔴 **None of these three carries bytes.** Two answer `303` and one answers a
listing, which is the rule that keeps an orchestrator's capacity off the size of
what it stores. The bytes come from a signed route below, standing in for the
presigned URL another deployment would hand out.

🔴 **The scope gate differs by route and that is deliberate.** The listing and
the log redirect are `jobs:read`; the artifact bytes are `artifacts:read`. So a
CI caller that watches runs and never pulls deliverables still reaches its own
log -- watching a run is what such a caller exists to do.
'''

import time

import flask

from siliconcompiler.remote.server import logstream
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.routes.auth import require
from siliconcompiler.remote.server.storage import DOWNLOAD_SECONDS, SignatureError

__all__ = ["blueprint"]


blueprint = flask.Blueprint("artifacts", __name__)


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _redirect(row):
    '''A 303 to where the bytes actually are.

    🔴 The target's shape is deliberately not announced here. A client branches
    on the `Content-Type` it is served after following, because a node can
    finish between this redirect and the fetch -- so anything computed at this
    end can be stale by the time it is used, and the type of the thing actually
    served cannot be.
    '''
    storage = flask.current_app.config["SC_STORAGE"]

    expires = int(time.time()) + DOWNLOAD_SECONDS
    signature = storage.sign_download(row["id"], expires)

    target = (f"{flask.request.url_root.rstrip('/')}/storage/artifact/"
              f"{row['job_id']}/{row['id']}?expires={expires}&sig={signature}")

    response = flask.make_response("", 303)
    response.headers["Location"] = target
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/v1/jobs/<job_id>/artifacts", methods=["GET"])
@require("jobs:read")
def listing(session, job_id):
    '''Endpoint 21.

    🔴 `items` may be `[]` and no kind is guaranteed, the manifest included. A
    client that requires one to be present has the same bug one kind further
    along -- three deployments reach an empty listing by different routes, and
    none of them is an error.
    '''
    items, cursor = _jobs().artifacts(session, job_id, flask.request.args)

    response = flask.jsonify({"items": items})
    response.headers["Cache-Control"] = "private, no-store"
    if cursor:
        query = flask.request.args.to_dict()
        query["cursor"] = cursor
        query_string = "&".join(f"{k}={v}" for k, v in query.items())
        response.headers["Link"] = \
            f'</v1/jobs/{job_id}/artifacts?{query_string}>; rel="next"'
    return response


@blueprint.route("/v1/jobs/<job_id>/artifacts/<artifact_id>", methods=["GET"])
@require("artifacts:read")
def fetch(session, job_id, artifact_id):
    '''Endpoint 22. `artifacts:read`, not `jobs:read`.'''
    return _redirect(_jobs().artifact(session, job_id, artifact_id))


@blueprint.route("/v1/jobs/<job_id>/logs", methods=["GET"])
@require("jobs:read")
def logs(session, job_id):
    '''Endpoint 20: one node's log, and it never carries bytes.

    Both query parameters are REQUIRED, and they are two fields rather than one
    string: `step=place, index=10` and `step=place1, index=0` both render
    `place10` and are two different nodes.
    '''
    step = flask.request.args.get("step")
    index = flask.request.args.get("index")
    if not step or not index:
        raise ProblemError(
            "invalid-request", detail="both step and index are required")

    target, payload = _jobs().node_log(session, job_id, step, index)

    if target == "artifact":
        return _redirect(payload)
    return _stream_redirect(job_id, step, index)


def _stream_redirect(job_id, step, index):
    '''A capability URL on this host, with its own lifetime.

    The contract sends a live tail to a stream host on its own origin and this
    deployment has one origin, so the answer is the one `file://` storage
    already gives for artifacts: a signed route here, reached through the same
    `303`. 🔴 Nothing on the wire changes -- authorization was still evaluated
    at `/logs`, and the URL still carries a TTL of its own rather than the
    access token's, which is what lets a six-hour log outlive a 900-second
    token.
    '''
    config = flask.current_app.config["SC_CONFIG"]
    storage = flask.current_app.config["SC_STORAGE"]

    expires = int(time.time()) + config.limits["max_log_stream_seconds"]
    signature = storage.sign_stream(job_id, step, index, expires)

    target = (f"{flask.request.url_root.rstrip('/')}/stream/logs/"
              f"{job_id}/{step}/{index}?expires={expires}&sig={signature}")

    response = flask.make_response("", 303)
    response.headers["Location"] = target
    response.headers["Cache-Control"] = "private, no-store"
    return response


######################################################################
# Not an endpoint: where a 303 above points
######################################################################

@blueprint.route("/stream/logs/<job_id>/<step>/<index>", methods=["GET"])
def tail(job_id, step, index):
    '''The live tail, where a `303` from ``/logs`` points.

    Served as ``text/event-stream``, which is the ONLY thing that tells a client
    this is a stream rather than a file -- and deliberately so: a node can
    finish between the redirect and the fetch, so anything decided at ``/logs``
    can be stale by the time it is used, and the type of what was actually
    served cannot be.
    '''
    config = flask.current_app.config["SC_CONFIG"]
    storage = flask.current_app.config["SC_STORAGE"]
    store = flask.current_app.config["SC_STORE"]
    jobs = flask.current_app.config["SC_JOBS"]
    limiter = flask.current_app.config["SC_STREAMS"]

    args = flask.request.args
    try:
        storage.verify_stream(job_id, step, index, args.get("expires"),
                              args.get("sig"), time.time())
    except SignatureError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if job is None or job["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")

    owner = job["user_id"]
    if not limiter.acquire(owner):
        raise ProblemError(
            "limit-exceeded", limit="concurrent_log_streams",
            detail=f"you already have {limiter.held(owner)} logs open",
            headers={"Retry-After": str(config["poll_interval_seconds"])})

    start = logstream.resume_from(
        flask.request.headers.get("Last-Event-ID"), args.get("last_event_id"))
    deadline = time.monotonic() + config.limits["max_log_stream_seconds"]

    def frames():
        try:
            yield from logstream.events(
                jobs.node_log_path(job, step, index), step, index,
                node_state=lambda: jobs.node_state(job_id, step, index),
                start=start, deadline=deadline,
                artifact_id=lambda: jobs.node_log_artifact(job_id, step, index))
        finally:
            # In a finally, because the commonest way a tail ends is the reader
            # hanging up -- which reaches this generator as GeneratorExit and
            # would otherwise leak the slot for the life of the process.
            limiter.release(owner)

    response = flask.Response(frames(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-store"
    # For whatever fronts this: an SSE response that is buffered is not a
    # stream, and the exemption is owed by the proxy rather than by the client.
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response


@blueprint.route("/storage/artifact/<job_id>/<artifact_id>", methods=["GET"])
def download(job_id, artifact_id):
    '''The bytes, on this host, standing in for a presigned URL.

    Outside `/v1` for the same reason the upload route is: the contract's
    surface is the eighteen endpoints, not wherever a deployment's storage
    happens to live. The signature is the credential and it names one artifact
    -- authorization was decided at the endpoint that issued it, which is where
    the token and the proof were presented.
    '''
    storage = flask.current_app.config["SC_STORAGE"]
    store = flask.current_app.config["SC_STORE"]

    args = flask.request.args
    try:
        storage.verify_download(artifact_id, args.get("expires"),
                                args.get("sig"), time.time())
    except SignatureError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    row = store.one(
        "SELECT * FROM artifacts WHERE id = ? AND job_id = ?", (artifact_id, job_id))
    if row is None or row["deleted_at"]:
        raise ProblemError("not-found", detail="no such artifact")

    try:
        path = storage.artifact_path(row["storage_key"])
    except SignatureError as e:                                 # pragma: no cover
        raise ProblemError("not-found", detail=str(e)) from None

    if not path.is_file():
        # Indexed and then lost: the row says the bytes should be here and they
        # are not, which is this deployment's fault and not the caller's.
        raise ProblemError(
            "not-found", detail="the bytes for this artifact are missing")

    # 🔴 Named after what it IS. Without this every download lands in somebody's
    # downloads folder as a bare uuid, and a person who fetched the logs of six
    # nodes has six files they cannot tell apart.
    inline = row["media_type"] in ("text/plain", "application/json")

    response = flask.send_file(
        path, mimetype=row["media_type"], conditional=True,
        as_attachment=not inline, download_name=_download_name(store, row))
    response.headers["Cache-Control"] = "private, no-store"
    return response


# What a browser should call each kind once it is on disk.
_SUFFIX = {
    "application/gzip": ".tar.gz",
    "application/json": ".pkg.json",
    "text/plain": ".log",
}


def _download_name(store, row) -> str:
    '''``<design>-<jobname>-<step>-<index>-<kind>`` and the right suffix.

    The node is in it because the node is the thing a person is looking for.
    Job-level artifacts have no node and say so by leaving it out rather than
    by carrying an empty segment.
    '''
    job = store.one("SELECT design, jobname FROM jobs WHERE id = ?",
                    (row["job_id"],))

    parts = [job["design"], job["jobname"]] if job else []
    if row["step"]:
        # Hyphenated, because `elaborate0` cannot be read back: it is step
        # `elaborate` index `0` and also a step called `elaborate0`.
        parts.append(f"{row['step']}-{row['index']}")
    parts.append(row["kind"])

    stem = "-".join(part for part in parts if part)
    return f"{stem}{_SUFFIX.get(row['media_type'], '')}"
