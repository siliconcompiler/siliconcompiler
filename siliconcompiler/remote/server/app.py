'''
The Flask application.

Flask rather than an async framework because the criterion is testability:
seventeen of this profile's eighteen endpoints are request-in, response-out, and
against ``app.test_client()`` those tests have no port, no event loop and no
teardown. The one that is not is the log stream, and the contract already lets
the stream host be a separate origin -- so if SSE under WSGI proves awkward it
moves out without a client change.
'''

from typing import Optional, Union

from pathlib import Path

from siliconcompiler.remote.server.auth import TokenIssuer
from siliconcompiler.remote.server.config import Config
from siliconcompiler.remote.server.dispatch import dispatcher_for
from siliconcompiler.remote.server.errors import ERRORS, ProblemError, problem
from siliconcompiler.remote.server.jobs import JobService
from siliconcompiler.remote.server.storage import Storage
from siliconcompiler.remote.server.store import Store

__all__ = ["create_app", "missing_server_dependency"]


try:
    import flask
    missing_server_dependency: Optional[str] = None
except ModuleNotFoundError as e:                                # pragma: no cover
    flask = None
    missing_server_dependency = e.name


PROBLEM_JSON = "application/problem+json"


def require_server_dependency() -> None:
    '''Fail with the install command rather than a traceback.

    The module entry point is importable whether or not the ``server`` extra is,
    so ``--help`` has to work without it. Only actually starting a server needs
    the extra.
    '''
    if missing_server_dependency:                               # pragma: no cover
        raise ModuleNotFoundError(
            f"{missing_server_dependency} is required to run the server: "
            'pip install "siliconcompiler[server]"',
            name=missing_server_dependency)


def create_app(datadir: Union[str, Path], cluster: str = "local",
               bind_keys: bool = True):
    '''Build the application for one deployment.

    Everything a handler needs hangs off the app: the store, the config, the
    token issuer, and which scheduler a job is dispatched through.

    ``bind_keys`` is the first-contact key binding, and it is on by default.
    Turning it off declares the deployment a single trust domain -- which a
    container fleet has to do, because /etc/machine-id is per image and every
    container derives the same subject, so with binding on the first one binds
    and every later one is refused.
    '''
    require_server_dependency()

    datadir = Path(datadir).resolve()
    datadir.mkdir(parents=True, exist_ok=True)

    config = Config.load(datadir)
    store = Store(datadir / "server.db")
    store.ensure_storage_location(config["storage_location_id"],
                                  config["storage_uri_base"])

    issuer = TokenIssuer(datadir, store, bind_keys=bind_keys)

    # Derived from the same secret the tokens are signed with, so an operator
    # has one file to protect. What keeps that safe is that neither signature
    # can be presented as the other: see Storage's key derivation.
    storage = Storage(datadir, config["storage_uri_base"], issuer.secret)

    app = flask.Flask(__name__)
    app.config.update(SC_DATADIR=datadir, SC_CONFIG=config,
                      SC_STORE=store, SC_CLUSTER=cluster,
                      SC_ISSUER=issuer, SC_BIND_KEYS=bind_keys,
                      SC_STORAGE=storage,
                      SC_JOBS=JobService(store, config, storage,
                                         dispatcher_for(cluster), datadir))

    _register_error_handlers(app)

    from siliconcompiler.remote.server.routes import (
        artifacts, auth, identity, jobs, meta)
    app.register_blueprint(meta.blueprint)
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(identity.blueprint)
    app.register_blueprint(jobs.blueprint)
    app.register_blueprint(artifacts.blueprint)

    # `siliconcompiler` must be advertised or this server does not start. A
    # check rather than a column: it is satisfied by an empty registry today,
    # and it becomes load-bearing once an operator is curating one -- a registry
    # that lists every tool and forgets the framework is a deployment where
    # nothing can be submitted, and finding that out at startup is much cheaper
    # than finding it out at the first submit.
    if "siliconcompiler" not in meta.advertised_software(store):
        raise RuntimeError(
            "no runnable siliconcompiler version: this deployment advertises "
            "no image containing it, so no job could be dispatched")

    return app


def _register_error_handlers(app) -> None:
    '''Render every refusal this server produces as RFC 9457.

    The promise is scoped to what a handler produced: a proxy in front of this
    server, and Flask's own routing below it, answer in their own shapes. What
    is in reach here is made to conform, and the client tolerates the rest.
    '''

    @app.errorhandler(ProblemError)
    def _problem_error(exc: ProblemError):
        response = flask.jsonify(exc.body())
        response.status_code = exc.status
        response.mimetype = PROBLEM_JSON
        for name, value in exc.headers.items():
            response.headers[name] = value
        return response

    # Routing answers before any handler runs, so these four would otherwise
    # leave Flask's HTML. They carry nothing a client branches on beyond the
    # status, but returning the registry's URI costs nothing and means a
    # developer who looks one up finds a page.
    _routing = {
        404: "not-found",
        405: "method-not-allowed",
        406: "not-acceptable",
        415: "unsupported-media-type",
    }

    def _make(slug):
        def handler(exc):
            response = flask.jsonify(problem(slug))
            response.status_code = ERRORS[slug].status
            response.mimetype = PROBLEM_JSON
            if slug == "method-not-allowed":
                allowed = getattr(exc, "valid_methods", None)
                if allowed:
                    # RFC 9110 requires the header; a bare 405 is
                    # non-conforming.
                    response.headers["Allow"] = ", ".join(allowed)
            return response
        return handler

    for status, slug in _routing.items():
        app.register_error_handler(status, _make(slug))
