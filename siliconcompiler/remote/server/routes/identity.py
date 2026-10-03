'''
Endpoints 9 to 12: who I am, and which machines can act as me.

``GET /v1/me`` is a mirror, never the gate: create and submit decide again.
'''

import flask

from siliconcompiler.remote.server.identity import accounts
from siliconcompiler.remote.server.routes.auth import require

__all__ = ["blueprint"]


blueprint = flask.Blueprint("identity", __name__)


def _store():
    return flask.current_app.config["SC_STORE"]


def _private(body, status: int = 200):
    '''Every authenticated response is uncacheable: a cache rule matching
    /v1/* would serve one caller's response to another.'''
    response = flask.jsonify(body)
    response.status_code = status
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/v1/me", methods=["GET"])
@require("profile:read")
def me(session):
    '''Endpoint 9. `authorized` is omitted, since `{}` would claim *granted
    nothing* where this server does no grants; `projects` and `terms` are `[]`,
    which is true.'''
    store = _store()
    config = flask.current_app.config["SC_CONFIG"]

    user = accounts.user(store, session.user_id)

    return _private({
        # The client keeps this per server, to tell "my jobs were deleted"
        # from "I am a different identity now".
        "id": user["id"],
        "issuer": user["issuer"],
        "projects": [],
        "limits": accounts.account_limits(
            config, accounts.effective_limits(store, config, session.user_id)),
        "usage": accounts.usage(store, session.user_id),
        "session": accounts.session_view(store, session),
        # No service-scoped terms document exists to block it.
        "can_submit": True,
        "terms": [],
    })


@blueprint.route("/v1/devices", methods=["GET"])
@require("devices:read")
def list_devices(session):
    '''Endpoint 10.'''
    from siliconcompiler.remote.server.errors import only_query

    only_query(flask.request.args, (), "GET /v1/devices")
    return _private({"items": [_device(row, session)
                               for row in accounts.devices_for(_store(), session)]})


@blueprint.route("/v1/devices/<device_id>", methods=["GET"])
@require("devices:read")
def get_device(session, device_id):
    '''Endpoint 11.'''
    return _private(_device(accounts.owned_device(_store(), session, device_id), session))


@blueprint.route("/v1/devices/<device_id>", methods=["DELETE"])
@require("devices:write")
def revoke_device(session, device_id):
    '''Endpoint 12: revoking a machine ends every session it holds;
    idempotent.'''
    device = accounts.owned_device(_store(), session, device_id)

    flask.current_app.config["SC_ISSUER"].revoke_device(
        device["id"], session.user_id)

    response = flask.make_response("", 204)
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _device(row, session) -> dict:
    '''One device, the same object in the list and endpoint 11.'''
    return {
        "id": row["id"],
        "name": row["name"],
        "current": row["id"] == getattr(session, "device_id", None),
        "machine_id_source": row["machine_id_source"],
        "enrolled_at": row["enrolled_at"],
        "last_seen_at": row["last_seen_at"],
    }
