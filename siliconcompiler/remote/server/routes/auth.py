'''
Endpoints 3, 4 and 5: getting a session, and ending one.

The device grant is routed and refuses. That is the contract's own answer for a
deployment whose ``grant_types_supported`` omits it, and routing it rather than
leaving it unrouted is what turns a 404 that means *this server is old* into a
501 that means *this deployment will never do that*.
'''

import flask

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import ProblemError

__all__ = ["blueprint", "current_session", "require"]


blueprint = flask.Blueprint("auth", __name__)


GRANT_CLIENT_CREDENTIALS = "client_credentials"
GRANT_REFRESH_TOKEN = "refresh_token"
GRANT_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"


def _issuer():
    return flask.current_app.config["SC_ISSUER"]


def request_url() -> str:
    '''The URL a DPoP proof is checked against.

    `url_root` rather than anything reconstructed by hand, so a deployment
    behind a proxy checks against what the client actually addressed.
    '''
    return flask.request.base_url


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


@blueprint.route("/v1/auth/token", methods=["POST"])
def token():
    '''Endpoint 4: the only token endpoint.

    Form-encoded rather than JSON, because that is what RFC 6749 specifies and
    this borrows the grant's shape. A DPoP proof is REQUIRED on every grant --
    there is no unbound session to be had here.
    '''
    if not flask.request.mimetype == "application/x-www-form-urlencoded":
        raise ProblemError(
            "unsupported-media-type",
            detail="the token endpoint takes application/x-www-form-urlencoded")

    proof = flask.request.headers.get("DPoP")
    if not proof:
        raise ProblemError("invalid-dpop-proof",
                           detail="a DPoP proof is required on every grant")

    try:
        jkt = dpop.verify_proof(proof, "POST", request_url())
    except dpop.DPoPError as e:
        raise ProblemError("invalid-dpop-proof", detail=str(e)) from None

    form = flask.request.form
    grant_type = form.get("grant_type")

    if grant_type == GRANT_CLIENT_CREDENTIALS:
        client_id = form.get("client_id", "")
        if not client_id.startswith("local:"):
            raise ProblemError(
                "invalid-request",
                detail="client_id must be local:<derivation> on this deployment")

        body = _issuer().client_credentials(
            subject=client_id[len("local:"):],
            jkt=jkt,
            requested_scope=form.get("scope"),
            machine_id_hash=form.get("machine_id_hash") or None,
            machine_id_source=form.get("machine_id_source") or "none",
            display_name=form.get("display_name") or None)

    elif grant_type == GRANT_REFRESH_TOKEN:
        refresh_token = form.get("refresh_token")
        if not refresh_token:
            raise ProblemError("invalid-request", detail="refresh_token is required")
        body = _issuer().refresh(refresh_token, jkt, form.get("scope"))

    elif grant_type == GRANT_DEVICE_CODE:
        raise ProblemError(
            "feature-unsupported", feature="device_grant",
            detail="this deployment does not support the device grant")

    else:
        raise ProblemError(
            "invalid-request",
            detail=f"unsupported grant_type: {grant_type}")

    response = flask.jsonify(body)
    # RFC 6749 makes this a MUST on any response carrying tokens.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


@blueprint.route("/v1/auth/device", methods=["POST"])
def device_authorization():
    '''Endpoint 3: routed, and it refuses.

    Permanent rather than transient, so a client must not retry. The `feature`
    member says which capability is missing, and `device_grant` is in that
    vocabulary precisely because this capability is advertised by
    grant_types_supported rather than by `features`.
    '''
    raise ProblemError(
        "feature-unsupported", feature="device_grant",
        detail="this deployment issues sessions with client_credentials")


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
