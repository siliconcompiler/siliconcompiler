'''
Endpoints 20, 21 and 22: getting the results out.

🔴 None of these carries bytes: they answer `303` or a listing, and the bytes
come from a signed route below, standing in for a presigned URL.

🔴 The listing and the log redirect are `jobs:read`, the bytes
`artifacts:read`, deliberately: a CI caller that only watches runs still
reaches its log.
'''

import secrets
import threading
import time

import flask

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.outputs import logstream
from siliconcompiler.remote.server.routes import next_page
from siliconcompiler.remote.server.routes.auth import public_url, require
from siliconcompiler.remote.server.state.storage import DOWNLOAD_SECONDS, SignatureError
from siliconcompiler.remote.server.state.store import TERMINAL_NODE_STATES

__all__ = ["blueprint"]


blueprint = flask.Blueprint("artifacts", __name__)


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _redirect(row):
    '''A 303 to where the bytes actually are.'''
    storage = flask.current_app.config["SC_STORAGE"]

    expires = int(time.time()) + DOWNLOAD_SECONDS
    signature = storage.sign_download(row["id"], expires)

    target = public_url(f"storage/artifact/{row['job_id']}/{row['id']}"
                        f"?expires={expires}&sig={signature}")

    response = flask.make_response("", 303)
    response.headers["Location"] = target
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/v1/jobs/<job_id>/artifacts", methods=["GET"])
@require("jobs:read")
def listing(session, job_id):
    '''Endpoint 21. 🔴 `items` may be `[]`, and no kind, not even the
    manifest, is guaranteed.'''
    from siliconcompiler.remote.server.errors import only_query

    only_query(flask.request.args, ("kind", "step", "index", "limit", "cursor"),
               "GET /v1/jobs/{id}/artifacts")
    items, cursor = _jobs().artifacts(session, job_id, flask.request.args)

    response = flask.jsonify({"items": items})
    response.headers["Cache-Control"] = "private, no-store"
    if cursor:
        # 🔴 Encoded: a `step` holding a space or an `&` is still one value.
        response.headers["Link"] = next_page(f"/v1/jobs/{job_id}/artifacts", cursor)
    return response


@blueprint.route("/v1/jobs/<job_id>/artifacts/<artifact_id>", methods=["GET"])
@require("artifacts:read")
def fetch(session, job_id, artifact_id):
    '''Endpoint 22. `artifacts:read`, not `jobs:read`.'''
    return _redirect(_jobs().artifact(session, job_id, artifact_id))


@blueprint.route("/v1/jobs/<job_id>/logs", methods=["GET"])
@require("jobs:read")
def logs(session, job_id):
    '''Endpoint 20: one node's log with both `step` and `index`, or the whole
    job's live stream with neither.'''
    step = flask.request.args.get("step")
    index = flask.request.args.get("index")

    if not step and not index:
        _jobs().job_log(session, job_id)
        return _job_stream_redirect(job_id, _until(session))

    if not step or not index:
        raise ProblemError(
            "invalid-request",
            detail="step and index go together: both for one node, neither "
                   "for the whole job")

    node = _jobs().node_log(session, job_id, step, index)
    ended = node["state"] in TERMINAL_NODE_STATES
    return _stream_redirect(job_id, step, index, _until(session), ended)


def _until(session) -> int:
    '''🔴 A stream ends no later than the credential that obtained it.'''
    return int(session.expires_at or time.time())


def _stream_redirect(job_id, step, index, expires, ended=False):
    '''A capability URL on this host, standing in for a separate stream host.

    🔴 Authorization was evaluated at `/logs`; the URL carries its own TTL.
    '''
    storage = flask.current_app.config["SC_STORAGE"]

    nonce = secrets.token_urlsafe(8)
    signature = storage.sign_stream(job_id, step, index, expires, nonce)

    # `ended` is unsigned and grants nothing: it only ends the stream at once.
    target = public_url(f"stream/logs/{job_id}/{step}/{index}"
                        f"?expires={expires}&n={nonce}&sig={signature}"
                        + ("&ended=1" if ended else ""))

    response = flask.make_response("", 303)
    response.headers["Location"] = target
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _job_stream_redirect(job_id, expires):
    '''The same capability URL as a node's, for the whole job.'''
    storage = flask.current_app.config["SC_STORAGE"]

    nonce = secrets.token_urlsafe(8)
    signature = storage.sign_job_stream(job_id, expires, nonce)

    target = public_url(f"stream/logs/{job_id}?expires={expires}&n={nonce}&sig={signature}")

    response = flask.make_response("", 303)
    response.headers["Location"] = target
    response.headers["Cache-Control"] = "private, no-store"
    return response


######################################################################
# Not an endpoint: where a 303 above points
######################################################################

@blueprint.route("/stream/logs/<job_id>", methods=["GET"])
def tail_job(job_id):
    '''Every node's live log, merged, where a coordinate-less `303` points:
    one slot of `concurrent_log_streams` for a flow of any width.'''
    config = flask.current_app.config["SC_CONFIG"]
    storage = flask.current_app.config["SC_STORAGE"]
    store = flask.current_app.config["SC_STORE"]
    jobs = flask.current_app.config["SC_JOBS"]
    limiter = flask.current_app.config["SC_STREAMS"]

    args = flask.request.args
    try:
        storage.verify_job_stream(job_id, args.get("expires"), args.get("sig"),
                                  time.time(), args.get("n"))
    except SignatureError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if job is None or job["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")

    _first_connection(args.get("sig"), args.get("expires"))
    owner = job["user_id"]
    if not limiter.acquire(owner):
        raise ProblemError(
            "limit-exceeded", limit="concurrent_log_streams",
            detail=f"you already have {limiter.held(owner)} logs open",
            headers={"Retry-After": str(config["poll_interval_seconds"])})

    nodes = jobs.job_nodes(job_id)
    index = logstream.EventIndex(jobs.stream_index_path(job_id), len(nodes))
    start = logstream.resume_job(
        flask.request.headers.get("Last-Event-ID"), args.get("last_event_id"),
        index)
    deadline = _deadline(args.get("expires"))

    def frames():
        try:
            yield from logstream.job_events(
                nodes, lambda step, index: jobs.node_log_path(job, step, index),
                node_states=lambda: jobs.node_states(job_id),
                job_over=lambda: jobs.job_over(job_id),
                start=start, deadline=deadline,
                artifact_id=lambda step, index: jobs.node_log_artifact(
                    job_id, step, index),
                index=index, root=jobs.job_root(job["user_id"], job["id"]),
                keepalive=config["stream_keepalive_seconds"])
        finally:
            limiter.release(owner)
            # The generator runs after the request's teardown, on its thread.
            store.release()

    return _event_stream(frames())


def _deadline(expires) -> float:
    '''The URL's own expiry, on the monotonic clock: a reconnect with the
    same URL cannot restart it.'''
    return time.monotonic() + max(0.0, int(expires) - time.time())


def _first_connection(signature, expires) -> None:
    '''🔴 A stream URL serves one connection. A client reconnects by asking
    `/logs` again, where authorization is evaluated.'''
    seen = flask.current_app.config.setdefault("SC_STREAMS_SEEN", {})
    lock = flask.current_app.config.setdefault("SC_STREAMS_SEEN_LOCK", threading.Lock())
    now_at = time.time()
    with lock:
        for used, until in list(seen.items()):
            if until < now_at:
                del seen[used]
        if signature in seen:
            raise ProblemError(
                "invalid-request",
                detail="this stream URL has been used; ask /logs again for another")
        seen[signature] = int(expires)


def _event_stream(frames):
    response = flask.Response(frames, mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-store"
    # A buffering proxy in front would break the stream.
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response


@blueprint.route("/stream/logs/<job_id>/<step>/<index>", methods=["GET"])
def tail(job_id, step, index):
    '''The live tail, where a `303` from ``/logs`` points.

    ``text/event-stream`` is the ONLY signal that this is a stream, since a
    node can finish between the redirect and the fetch.
    '''
    config = flask.current_app.config["SC_CONFIG"]
    storage = flask.current_app.config["SC_STORAGE"]
    store = flask.current_app.config["SC_STORE"]
    jobs = flask.current_app.config["SC_JOBS"]
    limiter = flask.current_app.config["SC_STREAMS"]

    args = flask.request.args
    try:
        storage.verify_stream(job_id, step, index, args.get("expires"),
                              args.get("sig"), time.time(), args.get("n"))
    except SignatureError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if job is None or job["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")

    _first_connection(args.get("sig"), args.get("expires"))
    owner = job["user_id"]
    if not limiter.acquire(owner):
        raise ProblemError(
            "limit-exceeded", limit="concurrent_log_streams",
            detail=f"you already have {limiter.held(owner)} logs open",
            headers={"Retry-After": str(config["poll_interval_seconds"])})

    start = logstream.resume_from(
        flask.request.headers.get("Last-Event-ID"), args.get("last_event_id"))
    deadline = _deadline(args.get("expires"))

    def frames():
        try:
            yield from logstream.events(
                jobs.node_log_path(job, step, index), step, index,
                node_state=lambda: jobs.node_state(job_id, step, index),
                start=start, deadline=deadline,
                artifact_id=lambda: jobs.node_log_artifact(job_id, step, index),
                root=jobs.job_root(job["user_id"], job["id"]),
                keepalive=config["stream_keepalive_seconds"],
                ended=args.get("ended") == "1")
        finally:
            # A reader hanging up arrives as GeneratorExit, and would otherwise
            # leak the slot and the connection.
            limiter.release(owner)
            store.release()

    return _event_stream(frames())


@blueprint.route("/storage/artifact/<job_id>/<artifact_id>", methods=["GET"])
def download(job_id, artifact_id):
    '''The bytes, on this host, standing in for a presigned URL; outside
    `/v1`, and the signature its only credential.'''
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
        # Indexed and then lost: this deployment's fault.
        raise ProblemError(
            "not-found", detail="the bytes for this artifact are missing")

    # 🔴 Always an attachment, never sniffed or active: a job's bytes, on this
    # host.
    response = flask.send_file(
        path, mimetype=row["media_type"], conditional=True,
        as_attachment=True, download_name=_download_name(store, row))
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


# Every artifact is gzipped; a manifest or job-level log is one file, not a tar.
_SUFFIX = {"manifest": ".pkg.json.gz", "job-logs": ".log.gz"}


def _download_name(store, row) -> str:
    '''``<design>-<jobname>-<step>-<index>-<kind>`` and the right suffix; a
    job-level artifact leaves the node out.'''
    job = store.one("SELECT design, jobname FROM jobs WHERE id = ?",
                    (row["job_id"],))

    parts = [job["design"], job["jobname"]]
    if row["step"]:
        # Hyphenated: `elaborate0` could be either node.
        parts.append(f"{row['step']}-{row['index']}")
    parts.append(row["kind"])

    stem = "-".join(part for part in parts if part)
    kind = "job-logs" if row["kind"] == "logs" and not row["step"] else row["kind"]
    return f"{stem}{_SUFFIX.get(kind, '.tar.gz')}"
