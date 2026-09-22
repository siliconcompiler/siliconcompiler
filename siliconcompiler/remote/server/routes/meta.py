'''
Endpoints 1 and 2: what this deployment is, and whether it is up.

Both are unauthenticated and identical for every caller, which is what makes
them the two exceptions to the API's caching rule: everything else carries
``private, no-store``, because a cache rule that ever matched ``/v1/*`` would
serve one caller's response to another's request.
'''

import logging

import flask

from siliconcompiler import __version__ as sc_version

__all__ = ["blueprint"]


blueprint = flask.Blueprint("meta", __name__)

logger = logging.getLogger("sc-server")

# A liveness probe is scraped every few seconds, so it must stay cheap. GET /v1
# is read once, by a client, at the start of a session.
CAPABILITIES_MAX_AGE = 60


def advertised_software(store):
    '''What this deployment can actually run, keyed on distribution name.

    A version is advertised only when it is runnable, so normally this is the
    join in the store: software_versions, through image_contents, to a live
    image. `siliconcompiler` is the only required key.

    An empty registry is not an empty answer, though, and that is the case this
    function exists for. A deployment that runs no containers is conforming --
    it leaves both image_id columns NULL for the life of every job -- and what
    it runs is the SiliconCompiler this server process was installed with. So
    with no images registered, that version is the truthful answer, and it stops
    being used the moment an operator registers one.
    '''
    software = store.advertised_software()
    if software:
        return software

    return {"siliconcompiler": [sc_version]}


@blueprint.route("/v1", methods=["GET"])
def capabilities():
    '''Endpoint 1. Unauthenticated.

    The only endpoint whose every field must be real on day one, and the first
    call on every client path: `grant_types_supported` is what a client branches
    on to decide which login it has, and a JSON capabilities block is how it
    knows it reached a v1 server at all.

    Scheduled downtime lives here, in `notices`, rather than on the liveness
    probe -- an announcement is read once by a person, at the start of a
    session, which is exactly when a client calls this.
    '''
    config = flask.current_app.config["SC_CONFIG"]
    store = flask.current_app.config["SC_STORE"]

    response = flask.jsonify(config.capabilities(advertised_software(store)))
    response.headers["Cache-Control"] = f"public, max-age={CAPABILITIES_MAX_AGE}"
    return response


@blueprint.route("/v1/healthz", methods=["GET"])
def healthz():
    '''Endpoint 2. Liveness, and it says as little as it possibly can.

    `status` is REQUIRED and is the ONLY member: `pass`, `warn` or `fail`.
    There is no `output`, no `checks` and no version, because this endpoint
    takes no credential -- a free-text diagnostic here tells anyone who can
    reach the deployment what is broken inside it. The reason a server is
    degraded goes to the log, which has an entitled reader.

    `warn` earns the third state for a server that is degraded but should stay
    in rotation -- the scheduler unreachable so jobs queue while the API is
    fine. Nothing produces it yet; it gets its producer when there is a
    scheduler to probe.
    '''
    store = flask.current_app.config["SC_STORE"]

    status = "pass"
    try:
        # Reads a real table rather than a constant: `SELECT 1` is evaluated
        # without touching the database at all, so it would answer `pass` for a
        # store that had been deleted out from under the process. job_states is
        # ten rows, is required for the server to do anything, and reading it
        # exercises the connection, the file and the schema together.
        if store.one("SELECT count(*) AS n FROM job_states")["n"] == 0:
            status = "fail"
    except Exception as e:                                       # noqa: BLE001
        logger.error(f"health check could not read the store: {e}")
        status = "fail"

    response = flask.jsonify({"status": status})
    response.mimetype = "application/health+json"
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 200 if status != "fail" else 503
    return response
