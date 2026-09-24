'''
Endpoints 9 to 12: who I am, and which machines can act as me.

``GET /v1/me`` is a mirror and never the gate: it tells a client what the server
will do, and the server decides again at create and again at submit.
'''

import flask

from siliconcompiler.remote.server import accounts
from siliconcompiler.remote.server.routes.auth import require

__all__ = ["blueprint"]


blueprint = flask.Blueprint("identity", __name__)


def _store():
    return flask.current_app.config["SC_STORE"]


def _private(body, status: int = 200):
    '''Every authenticated response is uncacheable.

    A cache rule that ever matched /v1/* would serve one caller's response to
    another's request, and these are the responses where that is a disclosure
    rather than a nuisance.
    '''
    response = flask.jsonify(body)
    response.status_code = status
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/v1/me", methods=["GET"])
@require("profile:read")
def me(session):
    '''Endpoint 9.

    `authorized` is omitted whole rather than sent empty: `{}` would claim *you
    were granted nothing*, where the truth is *this server does not do grants*.
    `projects` and `terms` are `[]`, which is the opposite rule and deliberate
    -- *this account is in no projects* is a true statement.
    '''
    store = _store()
    config = flask.current_app.config["SC_CONFIG"]

    user = accounts.user(store, session.user_id)

    return _private({
        # The client persists this per server address, which is how a user
        # tells "my jobs were deleted" from "I am a different person now" --
        # a reimage, a new container, a changed uid and a changed client salt
        # each mint a new row, and those have very different next steps.
        "id": user["id"],
        "issuer": user["issuer"],
        "projects": [],
        "limits": accounts.account_limits(config),
        "usage": accounts.usage(store, session.user_id),
        # No service-scoped terms document exists to block it.
        "can_submit": True,
        "terms": [],
    })


@blueprint.route("/v1/devices", methods=["GET"])
@require("devices:read")
def list_devices(session):
    '''Endpoint 10.

    Non-empty in this profile, which is not incidental: the key binding on
    first contact is the only real control the mode has, and this list plus the
    revoke button is its visible half.
    '''
    return _private({"devices": [_device(row)
                                 for row in accounts.devices_for(_store(), session)]})


@blueprint.route("/v1/devices/<device_id>", methods=["GET"])
@require("devices:read")
def get_device(session, device_id):
    '''Endpoint 11.'''
    return _private(_device(accounts.owned_device(_store(), session, device_id)))


@blueprint.route("/v1/devices/<device_id>", methods=["DELETE"])
@require("devices:write")
def revoke_device(session, device_id):
    '''Endpoint 12: the only write on this surface.

    Revoking a machine ends every session it holds. Idempotent: a device
    already revoked answers the same way, because the caller's intent is
    satisfied either way.
    '''
    device = accounts.owned_device(_store(), session, device_id)

    flask.current_app.config["SC_ISSUER"].revoke_device(
        device["id"], session.user_id)

    response = flask.make_response("", 204)
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _device(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        # The pin itself, so a user can compare what the server holds against
        # what their client says it has.
        "dpop_jkt": row["dpop_jkt"],
        "machine_id_source": row["machine_id_source"],
        "enrolled_at": row["enrolled_at"],
        "last_seen_at": row["last_seen_at"],
        "revoked_at": row["revoked_at"],
    }
