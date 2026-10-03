'''
The Flask application.

Flask, not an async framework, for testability: every endpoint is request-in,
response-out under ``app.test_client()``. The one exception, the log stream,
may move to a separate origin without a client change.
'''

import logging

from typing import List, Optional, Union

from pathlib import Path

from siliconcompiler.remote.server import errors
from siliconcompiler.remote.server.config import Config, private_paths
from siliconcompiler.remote.server.errors import ERRORS, OAuthError, ProblemError, problem
from siliconcompiler.remote.server.identity.auth import TokenIssuer
from siliconcompiler.remote.server.jobs import JobService
from siliconcompiler.remote.server.outputs import reaper
from siliconcompiler.remote.server.outputs.logstream import StreamLimiter
from siliconcompiler.remote.server.running.dispatch import dispatcher_for
from siliconcompiler.remote.server.state.storage import Storage
from siliconcompiler.remote.server.state.store import Store

__all__ = ["create_app", "missing_server_dependency"]


try:
    import flask
    missing_server_dependency: Optional[str] = None
except ModuleNotFoundError as e:                                # pragma: no cover
    flask = None
    missing_server_dependency = e.name


PROBLEM_JSON = "application/problem+json"


def _keep_off_path(datadir: Path) -> None:
    '''Take the data directory, and anything under it, off `sys.path`.'''
    import os
    import sys

    root = str(datadir)
    sys.path[:] = [entry for entry in sys.path
                   if not (os.path.realpath(entry or os.curdir) == root
                           or os.path.realpath(entry or os.curdir).startswith(root + os.sep))]


def create_app(datadir: Union[str, Path], cluster: str = "local",
               bind_keys: bool = True, test_mode: Optional[int] = None,
               public_origins: Optional[List[str]] = None):
    '''Build the application for one deployment.

    ``bind_keys`` off declares the deployment a single trust domain, which a
    container fleet has to do (see `TokenIssuer`). ``test_mode`` is one of
    ``config.TEST_MODES``; ``public_origins`` applies where config.json names
    none.
    '''
    # The install command, not a traceback: the entry point imports without
    # the ``server`` extra, so ``--help`` works.
    if missing_server_dependency:                               # pragma: no cover
        raise ModuleNotFoundError(
            f"{missing_server_dependency} is required to run the server: "
            'pip install "siliconcompiler[server]"',
            name=missing_server_dependency)

    datadir = Path(datadir).resolve()
    datadir.mkdir(parents=True, exist_ok=True)

    # Nothing under the data directory is importable: every job's extracted
    # archive is there. No manifest is read in this process.
    _keep_off_path(datadir)

    config = Config.load(datadir, test_mode=test_mode)
    if cluster == "slurm" and not config["containers"] and "python.env" in config["features"]:
        # Without a builder the install runs while staging, on this host, and
        # a Slurm node elsewhere would run what this host's platform chose.
        raise ValueError("features lists python.env, and nodes run on Slurm hosts "
                         "with no container to build an environment into; turn on "
                         "containers and env_builder, or leave python.env out")
    store = Store(datadir / "server.db")
    store.ensure_storage_location(config["storage_location_id"],
                                  config["storage_uri_base"])

    issuer = TokenIssuer(datadir, store, bind_keys=bind_keys)

    # Derived from the token secret, so an operator protects one file; neither
    # signature can pass as the other (see Storage's key derivation).
    storage = Storage(datadir, config["storage_uri_base"], issuer.secret)

    app = flask.Flask(__name__)
    app.config.update(SC_DATADIR=datadir, SC_CONFIG=config,
                      SC_STORE=store, SC_CLUSTER=cluster,
                      SC_ISSUER=issuer, SC_BIND_KEYS=bind_keys,
                      SC_STORAGE=storage,
                      SC_PUBLIC_ORIGINS=_origins(
                          config["public_origins"] or public_origins
                          or ["http://localhost"]),
                      SC_JOBS=JobService(store, config, storage,
                                         dispatcher_for(cluster), datadir),
                      SC_STREAMS=StreamLimiter(
                          config.limits["concurrent_log_streams"]))

    _check_page_scheme(config["web_url_base"], app.config["SC_PUBLIC_ORIGINS"])
    _register_error_handlers(app)
    # The portal is served wherever the API is, so over plain http its session
    # cookie is a bearer secret on the wire.
    beyond = plaintext_origins(app.config["SC_PUBLIC_ORIGINS"])
    if beyond:
        logging.getLogger("sc-server").warning(
            f"serving plain http at {', '.join(beyond)}: the portal's session cookie, "
            "the signed storage route and the stream URL cross the network in the "
            "clear there. Serve https through a reverse proxy, and set public_origins "
            "to its https origin")

    @app.teardown_request
    def _release_connection(_error=None):
        # Each request runs on its own thread, so its connection is released
        # as it ends (`Store.release`); a log stream's generator runs after
        # this and releases its own.
        store.release()

    from siliconcompiler.remote.server import portal
    from siliconcompiler.remote.server.routes import (
        artifacts, auth, errorpages, identity, jobs, meta)
    app.register_blueprint(meta.blueprint)
    app.register_blueprint(errorpages.blueprint)
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(identity.blueprint)
    app.register_blueprint(jobs.blueprint)
    app.register_blueprint(artifacts.blueprint)
    app.register_blueprint(portal.blueprint)

    # Browser sessions live here and nowhere else (see portal.Sessions).
    app.config["SC_PORTAL"] = portal.Sessions()

    # One SiliconCompiler, the one this server runs (PROFILE.md section 5):
    # checked here rather than at somebody's first submit.
    _check_an_image_holds_this_version(store, config)
    _report_read_containment()

    # Before anything can refuse, so every `detail` is held to the bound.
    errors.set_detail_max(config.limits["max_detail_chars"])
    # What a published `detail` must never say about this deployment.
    import socket
    errors.set_internals(
        paths=[datadir] + list(config["container_mounts"] or [])
        + private_paths(config["private_dataroots"] or {}),
        names=[socket.gethostname(), socket.getfqdn()])

    # Last: a failed sweep must never be why this server does not start.
    reaper.sweep(store, storage, config, datadir)

    return app


def plaintext_origins(origins) -> List[str]:
    '''The origins this server is reached at over plain http from beyond
    this machine.'''
    import ipaddress
    from urllib.parse import urlsplit

    beyond = []
    for origin in origins:
        parts = urlsplit(origin)
        if parts.scheme != "http":
            continue
        host = parts.hostname or ""
        try:
            local = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
        if not local:
            beyond.append(origin)
    return beyond


def _check_page_scheme(web_url_base, origins) -> None:
    '''An answer to an `https` request sends only to `https` URLs.
    `POST /v1/auth/browser`'s link is built on `web_url_base`, so that may not be
    `http` beside an `https` origin.'''
    from urllib.parse import urlsplit

    if not web_url_base or urlsplit(str(web_url_base)).scheme != "http":
        return
    secure = [origin for origin in origins if urlsplit(origin).scheme == "https"]
    if secure:
        raise ValueError(
            f"web_url_base is {web_url_base}, plain http, and this deployment is also "
            f"reached at {', '.join(secure)}: an answer to an https request sends the "
            "client only to https URLs, so web_url_base must be https")


def _origins(values) -> List[str]:
    '''Each configured origin as scheme://host[:port], and nothing else.'''
    from urllib.parse import urlsplit

    origins = []
    for value in values:
        parts = urlsplit(str(value).strip())
        if parts.scheme not in ("http", "https") or not parts.netloc \
                or parts.path.strip("/") or parts.query or parts.fragment:
            raise ValueError(f"public_origins holds scheme://host[:port]; not {value!r}")
        origins.append(f"{parts.scheme}://{parts.netloc}")
    if not origins:
        raise ValueError("public_origins names no origin")
    return origins


def _report_read_containment() -> None:
    '''Warn at startup of what the manifest's read cannot contain itself with
    on this host (PROFILE.md section 5).'''
    from siliconcompiler.remote.server.staging import sandbox

    logger = logging.getLogger("sc-server")
    achieved = sandbox.probe()
    if not achieved.get("network"):
        logger.warning("a job's manifest is read with this host's network: unprivileged "
                       "user namespaces are not available here, so the read cannot give "
                       "itself a network namespace of its own")
    if not achieved.get("limits"):
        logger.warning("a job's manifest is read with no CPU or memory limit of its own: "
                       "this platform does not set them")


def _check_an_image_holds_this_version(store, config) -> None:
    '''With containers on, a live image holds this server's own
    SiliconCompiler, or this server does not start.'''
    from siliconcompiler.remote.server.software import images

    if not config["containers"]:
        return
    if any(images.holds_own_version(image) for image in images.live_images(store)):
        return
    raise RuntimeError(
        f"no live image holds siliconcompiler {images.own_version()}, the version this "
        "server runs: this deployment runs jobs in containers, and a job's image must "
        "hold the SiliconCompiler that reads its manifest, so nothing could be "
        "dispatched. Register one with python3 -m siliconcompiler.remote.server.software.registry")


def _register_error_handlers(app) -> None:
    '''Render every refusal this server produces as RFC 9457. A proxy in front
    answers in its own shape, which the client tolerates.'''

    from siliconcompiler.remote.server.routes.errorpages import help_link

    def _with_help(response, body):
        # The page for this type, on THIS host: the public one may not be
        # reachable from where a person is reading the refusal.
        link = help_link(body.get("type"))
        if link:
            response.headers["Link"] = link
        return response

    def _occurrence(body, status):
        '''Which request this was: `instance`, and a correlation id the server's
        log carries too.'''
        body.setdefault("instance", flask.request.path)
        body.setdefault("trace_id", errors.trace_id(flask.request.headers))
        if status >= 500:
            logging.getLogger("sc-server").warning(
                f"{body['trace_id']} {flask.request.method} {flask.request.path} -> "
                f"{status} {body.get('type', '').rsplit('/', 1)[-1]}: "
                f"{body.get('detail', '')}")
        return body

    @app.errorhandler(ProblemError)
    def _problem_error(exc: ProblemError):
        body = _occurrence(exc.body(), exc.status)
        response = flask.jsonify(body)
        response.status_code = exc.status
        response.mimetype = PROBLEM_JSON
        for name, value in exc.headers.items():
            response.headers[name] = value
        return _with_help(response, body)

    @app.errorhandler(OAuthError)
    def _oauth_error(exc: OAuthError):
        response = flask.jsonify(exc.body())
        response.status_code = exc.status
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        for name, value in exc.headers.items():
            response.headers[name] = value
        return response

    # Routing answers before any handler runs, so these would otherwise be
    # Flask's HTML.
    _routing = {
        404: "not-found",
        405: "method-not-allowed",
        406: "not-acceptable",
        415: "unsupported-media-type",
    }

    def _make(slug):
        def handler(exc):
            body = _occurrence(problem(slug), ERRORS[slug].status)
            response = _with_help(flask.jsonify(body), body)
            response.status_code = ERRORS[slug].status
            response.mimetype = PROBLEM_JSON
            if slug == "method-not-allowed":
                allowed = getattr(exc, "valid_methods", None)
                if allowed:
                    # RFC 9110 requires the header on a 405.
                    response.headers["Allow"] = ", ".join(allowed)
            return response
        return handler

    for status, slug in _routing.items():
        app.register_error_handler(status, _make(slug))
