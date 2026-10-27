'''Getting a session, ending one, and who the session is.'''

from functools import wraps

import flask

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server import config
from siliconcompiler.remote.server.errors import OAuthError, ProblemError
from siliconcompiler.remote.server.state.store import iso

__all__ = ["blueprint", "require_session"]


blueprint = flask.Blueprint("auth", __name__)


def _identity():
    return flask.current_app.config["SC_IDENTITY"]


def _store():
    return flask.current_app.config["SC_STORE"]


def request_urls() -> list:
    '''What a proof's `htu` may name: this request's URL, or the same path on
    each configured public origin. Never `Host`, when origins are configured.'''
    origins = flask.current_app.config["SC_PUBLIC_ORIGINS"]
    if not origins:
        return [flask.request.base_url]
    return [f"{origin.rstrip('/')}{flask.request.script_root}{flask.request.path}"
            for origin in origins]


def require_session(handler):
    '''Hand the handler the verified caller.'''
    @wraps(handler)
    def guarded(*args, **kwargs):
        session = _identity().authenticate(
            flask.request.headers.get("Authorization"), flask.request.headers.get("DPoP"),
            flask.request.method, request_urls())
        return handler(session, *args, **kwargs)
    return guarded


@blueprint.route("/v1/auth/token", methods=["POST"])
def token():
    '''The token endpoint: form-encoded, and a DPoP proof on every grant.'''
    form = flask.request.form
    try:
        jkt = _identity().check_proof(flask.request.headers.get("DPoP"), "POST",
                                      request_urls())
    except dpop.DPoPError as e:
        raise OAuthError("invalid_dpop_proof", str(e)) from None

    grant_type = form.get("grant_type")
    if grant_type == "client_credentials":
        client_id = form.get("client_id", "")
        if not client_id.startswith("local:") or client_id == "local:":
            raise OAuthError("invalid_request", "client_id must be local:<subject>")
        body = _identity().client_credentials(
            client_id[len("local:"):], jkt, form.get("display_name") or None,
            form.get("machine_id_source") or "none")
    elif grant_type == "refresh_token":
        if not form.get("refresh_token"):
            raise OAuthError("invalid_request", "refresh_token is required")
        body = _identity().refresh(form["refresh_token"], jkt)
    elif not grant_type:
        raise OAuthError("invalid_request", "grant_type is required")
    else:
        raise OAuthError("unsupported_grant_type",
                         f"this deployment does not offer {grant_type}")

    response = flask.jsonify(body)
    response.headers["Pragma"] = "no-cache"
    return response


@blueprint.route("/v1/auth/device", methods=["POST"])
def device_authorization():
    raise ProblemError("feature-unsupported",
                       detail="this deployment issues sessions with client_credentials")


@blueprint.route("/v1/auth/revoke", methods=["POST"])
@require_session
def revoke(session):
    _identity().revoke_session(session.session_id)
    return "", 204


@blueprint.route("/v1/me", methods=["GET"])
@require_session
def me(session):
    user = _store().one("SELECT * FROM users WHERE id = ?", (session.user_id,))
    refresh = _store().one(
        "SELECT expires_at FROM tokens WHERE session_id = ? AND kind = 'refresh'",
        (session.session_id,))
    return flask.jsonify({
        "id": user["id"],
        "issuer": user["issuer"],
        "session": {
            "kind": "interactive",
            "device_id": session.device_id,
            "scope": " ".join(config.SCOPES),
            "access_expires_at": iso(session.access_expires_at),
            "refresh_expires_at": iso(refresh["expires_at"]) if refresh else None,
            "session_expires_at": iso(session.session_expires_at),
        },
        "can_submit": True,
        "limits": config.LIMITS,
    })


@blueprint.route("/v1/devices", methods=["GET"])
@require_session
def list_devices(session):
    rows = _store().all("SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL "
                        "ORDER BY enrolled_at", (session.user_id,))
    return flask.jsonify({"items": [
        {"id": row["id"], "name": row["name"], "current": row["id"] == session.device_id,
         "machine_id_source": row["machine_id_source"],
         "enrolled_at": iso(row["enrolled_at"]), "last_seen_at": iso(row["last_seen_at"])}
        for row in rows]})


@blueprint.route("/v1/devices/<device_id>", methods=["DELETE"])
@require_session
def revoke_device(session, device_id):
    '''Ends every session the machine holds; idempotent.'''
    if _store().one("SELECT 1 FROM devices WHERE id = ? AND user_id = ?",
                    (device_id, session.user_id)) is None:
        raise ProblemError("not-found", detail="no such device")
    _identity().revoke_device(device_id)
    return "", 204
