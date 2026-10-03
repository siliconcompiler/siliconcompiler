'''
Endpoints 1 and 2: what this deployment is, and whether it is up.

Both are unauthenticated and identical for every caller: the two exceptions to
``private, no-store``.
'''

import logging

import flask

__all__ = ["advertised_reported", "advertised_software", "blueprint"]


blueprint = flask.Blueprint("meta", __name__)

logger = logging.getLogger("sc-server")

CAPABILITIES_MAX_AGE = 60


def advertised_software(store, config=None):
    '''What this deployment can actually run, by bucket: the registry, best
    first, with containers only what a live image holds.

    🔴 Without containers, an empty registry falls back to what this process
    runs, so the REQUIRED ``siliconcompiler`` key is never missing. ⚠️ With
    containers there is no fallback: this process says nothing about images.
    '''
    return _advertised(store, config, store.advertised_software)


def advertised_reported(store, config=None):
    '''The same map, less every version no tool reported
    (`Store.reported_versions`).'''
    return _advertised(store, config, store.reported_versions)


def _advertised(store, config, read):
    from siliconcompiler.remote.server.software.images import (
        BUCKETS, INTERPRETER, PRIMARY, own_version)

    containers = bool(config["containers"]) if config is not None else True

    software = read(containers=containers)
    if not (containers or software["python"] or software["tools"]):
        software = {bucket: {} for bucket in BUCKETS.values()}

    # 🔴 One SiliconCompiler, the one this server runs, which reads every
    # manifest (profile §5).
    software["python"][PRIMARY] = [own_version()]
    if not containers:
        # Where nodes run on this host, the user's Python runs in this one.
        import sys

        software[BUCKETS["interpreter"]] = {INTERPRETER: ["%d.%d.%d" % sys.version_info[:3]]}
    return software


@blueprint.route("/v1", methods=["GET"])
def capabilities():
    '''Endpoint 1, unauthenticated: the first call on every client path, and
    where `notices` announce downtime.'''
    config = flask.current_app.config["SC_CONFIG"]
    store = flask.current_app.config["SC_STORE"]

    response = flask.jsonify(config.capabilities(advertised_software(store, config)))
    response.headers["Cache-Control"] = f"public, max-age={CAPABILITIES_MAX_AGE}"
    return response


def health_status(store) -> str:
    '''`pass` or `fail`: what `healthz` answers, and the portal's server
    screen shows.'''
    try:
        # A real table, not `SELECT 1`, which never touches the file and would
        # pass for a deleted store.
        if store.one("SELECT count(*) AS n FROM job_states")["n"] == 0:
            return "fail"
    except Exception as e:                                       # noqa: BLE001
        logger.error(f"health check could not read the store: {e}")
        return "fail"
    return "pass"


@blueprint.route("/v1/healthz", methods=["GET"])
def healthz():
    '''Endpoint 2: liveness, saying as little as possible.

    `status` is the ONLY member: with no credential, a diagnostic would tell
    anyone what is broken inside. Nothing produces `warn` yet.
    '''
    status = health_status(flask.current_app.config["SC_STORE"])

    response = flask.jsonify({"status": status})
    response.mimetype = "application/health+json"
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 200 if status != "fail" else 503
    return response
