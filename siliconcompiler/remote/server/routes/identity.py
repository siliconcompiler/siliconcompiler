'''
Endpoints 9 to 12: who I am, and which machines can act as me.

``GET /v1/me`` is a mirror and never the gate: it tells a client what the server
will do, and the server decides again at create and again at submit.
'''

import flask

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.routes.auth import require
from siliconcompiler.remote.server.store import now

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

    user = store.one("SELECT * FROM users WHERE id = ?", (session.user_id,))
    if user is None:
        raise ProblemError("not-found")

    return _private({
        # The client persists this per server address, which is how a user
        # tells "my jobs were deleted" from "I am a different person now" --
        # a reimage, a new container, a changed uid and a changed client salt
        # each mint a new row, and those have very different next steps.
        "id": user["id"],
        "issuer": user["issuer"],
        "projects": [],
        "limits": _account_limits(config),
        "usage": _usage(store, session.user_id),
        # No service-scoped terms document exists to block it.
        "can_submit": True,
        "terms": [],
    })


def _account_limits(config) -> dict:
    '''The account's allowance -- six members, and not GET /v1's key set.

    Four keys appear in both blocks and a client combines only those. Here they
    come from the server's own config, because there are no plans and no
    per-user overrides in this profile: a ceiling is the operator's policy
    rather than an account's data.
    '''
    ceiling = config.limits
    return {
        "concurrent_jobs": ceiling["concurrent_jobs"],
        "concurrent_nodes": None,           # reported-only, and unset here
        "pending_uploads": ceiling["pending_uploads"],
        "max_job_nodes": ceiling["max_job_nodes"],
        "devices": None,                    # null = unlimited, not zero
        "job_retention_days": ceiling["job_retention_days"],
    }


def _usage(store, user_id: str) -> dict:
    '''Derived, not metered.

    All four numbers come from `jobs` and `artifacts` directly. A metering
    table would buy a billing history nobody on this deployment bills against.
    Every `limit` is null, because nothing here enforces one -- except
    `jobs_active`, which mirrors a counter that create does enforce.
    '''
    active = store.one(
        "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
        "AND state IN ('queued', 'running', 'cancelling')", (user_id,))["n"]

    stored = store.one(
        "SELECT coalesce(sum(a.size_bytes), 0) AS n FROM artifacts a "
        "JOIN jobs j ON j.id = a.job_id "
        "WHERE j.user_id = ? AND a.deleted_at IS NULL", (user_id,))["n"]

    # The calendar month to date. Windows are calendar; rolling windows are not
    # in v1, so resets_at is always a real instant.
    month_start = now()[:8] + "01T00:00:00.000Z"
    compute = store.one(
        "SELECT coalesce(sum(julianday(finished_at) - julianday(started_at)), 0) "
        "       * 86400 AS n FROM jobs "
        "WHERE user_id = ? AND started_at IS NOT NULL AND finished_at IS NOT NULL "
        "  AND finished_at >= ?", (user_id, month_start))["n"]

    return {
        "compute_seconds": {
            "used": int(compute),
            "limit": None,
            "window": "calendar_month",
            "resets_at": _next_month(month_start),
        },
        # An empty map rather than null: no licence is metered here, and there
        # is no per-tool row to report.
        "licence_seconds": {},
        "storage_bytes": {"used": int(stored), "limit": None},
        "jobs_active": active,
    }


def _next_month(month_start: str) -> str:
    year, month = int(month_start[:4]), int(month_start[5:7])
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return f"{year:04d}-{month:02d}-01T00:00:00.000Z"


@blueprint.route("/v1/devices", methods=["GET"])
@require("devices:read")
def list_devices(session):
    '''Endpoint 10.

    Non-empty in this profile, which is not incidental: the key binding on
    first contact is the only real control the mode has, and this list plus the
    revoke button is its visible half.
    '''
    rows = _store().all(
        "SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL "
        "ORDER BY enrolled_at DESC", (session.user_id,))

    return _private({"devices": [_device(row) for row in rows]})


@blueprint.route("/v1/devices/<device_id>", methods=["GET"])
@require("devices:read")
def get_device(session, device_id):
    '''Endpoint 11.'''
    return _private(_device(_owned_device(session, device_id)))


@blueprint.route("/v1/devices/<device_id>", methods=["DELETE"])
@require("devices:write")
def revoke_device(session, device_id):
    '''Endpoint 12: the only write on this surface.

    Revoking a machine ends every session it holds. Idempotent: a device
    already revoked answers the same way, because the caller's intent is
    satisfied either way.
    '''
    device = _owned_device(session, device_id)

    flask.current_app.config["SC_ISSUER"].revoke_device(
        device["id"], session.user_id)

    response = flask.make_response("", 204)
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _owned_device(session, device_id):
    '''A device, or a 404 that does not say whether it exists.

    The 404-not-403 rule: a 403 would confirm the id belongs to somebody. What
    it conceals here is bounded by an identity nothing verifies, which is worth
    knowing but is not a reason to leak it.
    '''
    row = _store().one(
        "SELECT * FROM devices WHERE id = ? AND user_id = ?",
        (device_id, session.user_id))
    if row is None:
        raise ProblemError("not-found", detail="no such device")
    return row


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
