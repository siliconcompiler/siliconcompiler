'''
Endpoints 3, 4, 5 and 6: getting a session, ending one, and a page for a
person's browser.

🔴 **Two shapes, keyed on the endpoint.** What OAuth processing refuses at
`/v1/auth/token` and `/v1/auth/device` is answered in the OAuth shape --
`{"error", "error_description"}`, with `reason` where one applies -- and the
transport-level refusals raised before it (405, 415, 426, 429; this server
raises only the first two there) stay problem+json, as everywhere.
`/v1/auth/revoke` is an ordinary endpoint and answers problem+json.
'''

from urllib.parse import urlsplit

import flask

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import OAuthError, ProblemError

__all__ = ["blueprint", "current_session", "require", "public_origin", "public_url"]


blueprint = flask.Blueprint("auth", __name__)


GRANT_CLIENT_CREDENTIALS = "client_credentials"
GRANT_REFRESH_TOKEN = "refresh_token"
GRANT_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"

# Refused rather than ignored: silently dropping one would mint a token its
# caller misunderstands. Every other unknown parameter is ignored (RFC 6749 §3.2).
_REFUSED_PARAMETERS = ("actor_token", "audience", "resource")


def _issuer():
    return flask.current_app.config["SC_ISSUER"]


def public_origin() -> str:
    '''The origin this deployment is reached at, from configuration.

    🔴 **Never `Host`, `X-Forwarded-Host`, `base_url` or `url_root`**: a URL
    this server hands out gets pasted and clicked, and a proof checked against
    a caller-chosen host is not checked. They only pick AMONG the configured
    origins, where there are several: the one the request's DPoP proof signed
    for, where it has one, and otherwise the one whose host is `Host` (contract
    D70). Never the socket's scheme, which behind a TLS-terminating proxy is
    `http`. One that matches neither way gets the first.
    '''
    origins = flask.current_app.config["SC_PUBLIC_ORIGINS"]
    signed = _signed_origin()
    if signed:
        for origin in origins:
            if dpop._htu(origin) == signed:
                return origin
    host = flask.request.host
    for origin in origins:
        if urlsplit(origin).netloc == host:
            return origin
    return origins[0]


def _signed_origin():
    '''The canonical origin of this request's DPoP proof's `htu`, or None.
    Read unverified: it only chooses among the configured origins, and the
    proof is then verified against the one it chose.'''
    proof = flask.request.headers.get("DPoP")
    if not proof:
        return None
    try:
        import jwt

        htu = jwt.decode(proof, options={"verify_signature": False}).get("htu")
    except Exception:                                           # noqa: BLE001
        return None
    if not isinstance(htu, str):
        return None
    parts = urlsplit(htu)
    return dpop._htu(f"{parts.scheme}://{parts.netloc}") if parts.netloc else None


def public_url(path: str) -> str:
    '''An absolute URL on this deployment, for a path under its mount point.'''
    return f"{public_origin()}{flask.request.script_root}/{path.lstrip('/')}"


def request_url() -> str:
    '''The URL a DPoP proof's `htu` is checked against.'''
    return public_url(flask.request.path)


def current_session():
    '''The verified caller, or a refusal.

    Cached on the request so that two checks in one handler do not verify the
    proof twice -- and, more importantly, do not trip the replay guard on the
    second look.
    '''
    session = getattr(flask.g, "sc_session", None)
    if session is None:
        session = _issuer().authenticate(
            flask.request.headers.get("Authorization"),
            flask.request.headers.get("DPoP"),
            flask.request.method,
            request_url())
        flask.g.sc_session = session
    return session


def require(scope: str):
    '''Guard a handler with the one scope it needs.'''
    def decorator(handler):
        from functools import wraps

        @wraps(handler)
        def guarded(*args, **kwargs):
            session = current_session()
            session.require(scope)
            return handler(session, *args, **kwargs)
        return guarded
    return decorator


MACHINE_ID_SOURCES = ("linux_machine_id", "macos_platform_uuid", "windows_machine_guid",
                      "none")


@blueprint.route("/v1/auth/token", methods=["POST"])
def token():
    '''Endpoint 4: the only token endpoint.

    Form-encoded rather than JSON, because that is what RFC 6749 specifies and
    this borrows the grant's shape. A DPoP proof is REQUIRED on every grant --
    there is no unbound session to be had here.
    '''
    form = _oauth_form()

    proof = flask.request.headers.get("DPoP")
    if not proof:
        raise OAuthError("invalid_dpop_proof", "a DPoP proof is required on every grant")

    try:
        jkt = dpop.verify_proof(proof, "POST", request_url())
    except dpop.DPoPError as e:
        raise OAuthError("invalid_dpop_proof", str(e)) from None
    _issuer()._check_replay(proof, oauth=True)

    grant_type = form.get("grant_type")

    if grant_type == GRANT_CLIENT_CREDENTIALS:
        client_id = form.get("client_id", "")
        if not client_id.startswith("local:"):
            raise OAuthError("invalid_request",
                             "client_id must be local:<derivation> on this deployment")

        body = _issuer().client_credentials(
            subject=client_id[len("local:"):],
            jkt=jkt,
            requested_scope=form.get("scope"),
            machine_id_hash=form.get("machine_id_hash") or None,
            machine_id_source=_machine_id_source(form),
            display_name=form.get("display_name") or None)

    elif grant_type == GRANT_REFRESH_TOKEN:
        refresh_token = form.get("refresh_token")
        if not refresh_token:
            raise OAuthError("invalid_request", "refresh_token is required")
        # `scope` is ignored: a refresh returns the session's full scope.
        body = _issuer().refresh(refresh_token, jkt,
                                 machine_id_hash=form.get("machine_id_hash") or None,
                                 machine_id_source=_machine_id_source(form))

    elif not grant_type:
        raise OAuthError("invalid_request", "grant_type is required")

    else:
        # The device grant and token exchange included: neither is offered
        # here, and this is the answer on which a client switches login mode.
        raise OAuthError("unsupported_grant_type",
                         f"this deployment does not offer {grant_type}")

    response = flask.jsonify(body)
    # RFC 6749 makes this a MUST on any response carrying tokens.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _oauth_form():
    '''The form, once the transport-level checks pass.

    415 is raised before any OAuth processing, so it stays problem+json; a
    refused parameter is OAuth processing's own `invalid_request`.
    '''
    if flask.request.mimetype != "application/x-www-form-urlencoded":
        raise ProblemError(
            "unsupported-media-type",
            detail="this endpoint takes application/x-www-form-urlencoded")

    form = flask.request.form
    refused = [name for name in _REFUSED_PARAMETERS if name in form]
    if refused:
        raise OAuthError("invalid_request",
                         f"{', '.join(refused)} is not supported here")
    return form


def _machine_id_source(form) -> str:
    # 🔴 One of four, and nothing else (identity D59): the weak-path flag a
    # device carries for ever. Absent reads as none.
    source = form.get("machine_id_source") or "none"
    if source not in MACHINE_ID_SOURCES:
        raise OAuthError("invalid_request",
                         f"machine_id_source is one of {', '.join(MACHINE_ID_SOURCES)}")
    return source


@blueprint.route("/v1/auth/device", methods=["POST"])
def device_authorization():
    '''Endpoint 3: routed, and it refuses in the OAuth shape.

    `unsupported_grant_type`, which is what the device endpoint answers where
    the deployment does not offer the device grant: the client's cue to switch
    to `client_credentials`, never a reason to retry.
    '''
    _oauth_form()
    raise OAuthError("unsupported_grant_type",
                     "this deployment issues sessions with client_credentials")


@blueprint.route("/v1/auth/revoke", methods=["POST"])
def revoke():
    '''Endpoint 5: end this session.

    No scope gates it. A credential may always end itself, and a logout that
    can be scoped away is a session nobody can close.
    '''
    _issuer().revoke(current_session())

    response = flask.make_response("", 204)
    response.headers["Cache-Control"] = "no-store"
    return response


######################################################################
# Endpoint 6: a page for a person's browser
######################################################################

# What a request may name: the page each id lands on.
_PAGES = ("job_id", "terms_id", "artifact_id")


@blueprint.route("/v1/auth/browser", methods=["POST"])
def browser():
    '''Endpoint 6: a single-use sign-in that lands on one portal page.

    🔴 **The landing is built from the id the request names**, and no path a
    caller sends is followed: a redirect that follows caller input is an open
    redirect. The link is on `web_url_base`, never on `Host` or
    `X-Forwarded-Host`, and lives seconds; this portal has no sign-in of its
    own, so `expires_at` is always set here.

    Any session but a CI one may ask, and no scope gates it (surface D310).
    '''
    from siliconcompiler.remote.server.jobs.common import _from_epoch

    session = current_session()
    store = flask.current_app.config["SC_STORE"]
    family = store.one("SELECT kind FROM token_families WHERE id = ?", (session.family_id,))
    if family is None or family["kind"] != "interactive":
        raise ProblemError("not-permitted",
                           detail="a CI session asks for no page: nobody is at a browser")

    named = _page_named()
    jobs = flask.current_app.config["SC_JOBS"]
    if named is None:
        # The portal's home, or the page a browser was turned away from cold:
        # the portal's own breadcrumb, checked when the sign-in is spent.
        landing = None
    elif named[0] == "job_id":
        landing = flask.url_for("portal.job", job_id=jobs.owned(session, named[1])["id"])
    elif named[0] == "terms_id":
        # 🔴 This profile serves no terms documents, so none is one the caller
        # can see.
        raise ProblemError("not-found", detail="no such terms document")
    else:
        row = store.one("SELECT job_id FROM artifacts WHERE id = ?", (named[1],))
        if row is None:
            raise ProblemError("not-found", detail="no such artifact")
        # By its job, as every read of an artifact is: the job's predicate.
        jobs.owned(session, row["job_id"])
        # 🔴 This profile takes no access requests, so every artifact reads
        # `can_request_access: false`, and there is nothing to ask for.
        raise ProblemError("not-permitted",
                           detail="this artifact has nothing to ask for: this server takes "
                                  "no access requests")

    token, expires = flask.current_app.config["SC_PORTAL"].offer(session.user_id, landing)
    response = flask.jsonify({"url": _portal_url("/portal/enter", token=token),
                              "expires_at": _from_epoch(expires)})
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _page_named():
    '''``(member, id)`` the request's body names, or None for the portal's
    home. An empty body is `{}` (surface D306); more than one member, one this
    endpoint does not define, or an id that is not a string, is
    `invalid-request`.'''
    if flask.request.mimetype not in ("application/json", ""):
        raise ProblemError("unsupported-media-type",
                           detail=f"this endpoint takes application/json, not "
                                  f"{flask.request.mimetype}")
    body = flask.request.get_json(silent=True)
    if body is None:
        if flask.request.get_data():
            raise ProblemError("invalid-request", detail="the body must be a JSON object")
        return None
    if not isinstance(body, dict):
        raise ProblemError("invalid-request", detail="the body must be a JSON object")
    unknown = sorted(set(body) - set(_PAGES))
    if unknown:
        raise ProblemError("invalid-request",
                           detail=f"this endpoint takes one of {', '.join(_PAGES)}, "
                                  f"not {', '.join(unknown)}")
    if len(body) > 1:
        raise ProblemError("invalid-request", detail="name one page: at most one member")
    if not body:
        return None
    member, value = next(iter(body.items()))
    if not isinstance(value, str) or not value:
        raise ProblemError("invalid-request", detail=f"{member} is an id")
    return member, value


def _portal_url(path: str, **query) -> str:
    '''A portal URL on `web_url_base`, or on the configured origin this
    request arrived at where there is none -- never on a request header.'''
    from urllib.parse import urlencode

    base = flask.current_app.config["SC_CONFIG"]["web_url_base"]
    root = base.rstrip("/") if base else f"{public_origin()}{flask.request.script_root}"
    return f"{root}{path}" + (f"?{urlencode(query)}" if query else "")
