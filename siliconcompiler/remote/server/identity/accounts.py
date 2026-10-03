'''
Who a caller is, what they are allowed, and which machines act as them.

Shared by the API and the portal so their authorization cannot drift: there
is one place to forget a ``WHERE user_id =``, not two. Nothing here builds a
response.
'''

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.state.store import ACTIVE_STATES, now, stamp

__all__ = ["account_limits", "devices_for", "effective_limits", "lifetime",
           "owned_device", "set_limit", "usage", "user", "OVERRIDABLE"]


def user(store, user_id: str):
    row = store.one("SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise ProblemError("not-found")
    return row


# Which limits a `user_limits` row may override; listed, not derived from the
# table, so adding one is deliberate.
OVERRIDABLE = ("max_download_bytes",)


def effective_limits(store, config, user_id: str) -> Dict[str, Any]:
    '''The deployment's ceilings with this account's overrides applied.

    NULL inherits, and `-1` becomes the wire's `null` (unlimited), never
    reaching a client (see schema.sql's `user_limits`).
    '''
    limits = dict(config.limits)

    row = store.one("SELECT * FROM user_limits WHERE user_id = ?", (user_id,))
    if row is None:
        return limits

    for key in OVERRIDABLE:
        value = row[key]
        if value is None:
            continue                        # inherit
        limits[key] = None if value == -1 else value

    return limits


def account_limits(config, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    '''The account's allowance, as `GET /v1/me` publishes it.

    Every member REQUIRED, with the caller's effective values: `GET /v1` cannot
    vary by caller, so a per-user override is published only here.
    '''
    ceiling = dict(config.limits)
    ceiling.update(overrides or {})

    return {
        "concurrent_jobs": ceiling["concurrent_jobs"],
        "concurrent_nodes": None,           # reported-only, and unset here
        "pending_uploads": ceiling["pending_uploads"],
        "max_job_nodes": ceiling["max_job_nodes"],
        "devices": None,                    # null = unlimited, not zero
        "max_staging_seconds": ceiling["max_staging_seconds"],
        "artifact_retention_seconds": ceiling["artifact_retention_seconds"],
        "max_download_bytes": ceiling["max_download_bytes"],
    }


def set_limit(store, user_id: str, name: str, value: Optional[int],
              actor: str, note: Optional[str] = None) -> None:
    '''Record one operator decision about one account; the only writer, and
    never the portal.'''
    if name not in OVERRIDABLE:
        raise ValueError(
            f"{name} is not a per-user limit; try {', '.join(OVERRIDABLE)}")
    if value is not None and value < -1:
        raise ValueError("a limit is -1 for unlimited, or zero and above")

    store.execute(
        f"INSERT INTO user_limits (user_id, {name}, set_by, note) "
        "VALUES (?, ?, ?, ?) "
        f"ON CONFLICT (user_id) DO UPDATE SET {name} = excluded.{name}, "
        "  set_at = excluded.set_at, set_by = excluded.set_by, "
        "  note = excluded.note",
        (user_id, value, actor, note))


def usage(store, user_id: str) -> Dict[str, Any]:
    '''`GET /v1/me`'s `usage`, derived from `jobs` and `artifacts`, not
    metered: nobody bills here. Every `limit` is null, as nothing enforces one.
    '''
    active = store.one(
        "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
        f"AND state IN ({', '.join('?' * len(ACTIVE_STATES))})",
        (user_id, *ACTIVE_STATES))["n"]

    stored = store.one(
        "SELECT coalesce(sum(a.size_bytes), 0) AS n FROM artifacts a "
        "JOIN jobs j ON j.id = a.job_id "
        "WHERE j.user_id = ? AND a.deleted_at IS NULL", (user_id,))["n"]

    # Windows are calendar months in v1, so resets_at is a real instant.
    month_start = now()[:8] + "01T00:00:00.000Z"

    def compute_since(start):
        return int(store.one(
            "SELECT coalesce(sum(julianday(finished_at) - julianday(started_at)), 0) "
            "       * 86400 AS n FROM jobs "
            "WHERE user_id = ? AND started_at IS NOT NULL AND finished_at IS NOT NULL "
            "  AND finished_at >= ?", (user_id, start))["n"])

    return {
        # `total` is every job row, deleted ones included.
        "compute_seconds": {
            "used": compute_since(month_start),
            "total": compute_since(""),
            "limit": None,
            "window": "calendar_month",
            "resets_at": _next_month(month_start),
        },
        # No license is metered, so no per-tool row.
        "license_seconds": {},
        # A stock: no `total`, window or reset.
        "storage_bytes": {"used": int(stored), "total": None, "limit": None,
                          "window": None, "resets_at": None},
        "concurrent_jobs": active,
    }


def session_view(store, session) -> Dict[str, Any]:
    '''`GET /v1/me`'s `session`: the calling token's own, read without
    rotating anything.'''
    from datetime import datetime, timezone

    from siliconcompiler.remote.server.identity.auth import SCOPES

    family = store.one("SELECT kind, expires_at FROM token_families WHERE id = ?",
                       (session.family_id,))
    refresh = store.one(
        "SELECT expires_at FROM refresh_tokens WHERE family_id = ? AND replaced_at IS NULL "
        "  AND revoked_at IS NULL ORDER BY issued_at DESC LIMIT 1", (session.family_id,))
    access = None
    if session.expires_at is not None:
        access = stamp(datetime.fromtimestamp(session.expires_at, tz=timezone.utc))
    kind = family["kind"]
    return {
        "kind": kind,
        # As a token's scope string, in the registry's own order.
        "scope": " ".join(scope for scope in SCOPES if scope in session.scope),
        "device_id": session.device_id if kind == "interactive" else None,
        "access_expires_at": access,
        "refresh_expires_at": refresh["expires_at"] if refresh else None,
        "session_expires_at": family["expires_at"],
    }


def lifetime(store, user_id: str) -> Dict[str, Any]:
    '''Everything this account has ever run, for the portal screen.

    Deliberately NOT in `usage`, which measures against an allowance; an
    all-time total has none. A running job counts only once it finishes.
    '''
    compute = store.one(
        "SELECT coalesce(sum(julianday(finished_at) - julianday(started_at)), 0) "
        "       * 86400 AS n FROM jobs "
        "WHERE user_id = ? AND started_at IS NOT NULL AND finished_at IS NOT NULL",
        (user_id,))["n"]

    rows = store.all(
        "SELECT state, count(*) AS n FROM jobs WHERE user_id = ? GROUP BY state",
        (user_id,))

    by_state = {row["state"]: row["n"] for row in rows}
    return {
        "compute_seconds": int(compute),
        "jobs": sum(by_state.values()),
        "by_state": by_state,
    }


def _next_month(month_start: str) -> str:
    year, month = int(month_start[:4]), int(month_start[5:7])
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return f"{year:04d}-{month:02d}-01T00:00:00.000Z"


def devices_for(store, session) -> List[Any]:
    '''The machines that may act as this caller: the visible half of the key
    binding, this profile's one real control.'''
    return store.all(
        "SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL "
        "ORDER BY enrolled_at DESC", (session.user_id,))


def owned_device(store, session, device_id):
    '''A device, or a 404 that does not say whether it exists.

    The one place a device's ownership predicate is written; a 403 would
    confirm the id belongs to somebody.
    '''
    row = store.one(
        "SELECT * FROM devices WHERE id = ? AND user_id = ?",
        (device_id, session.user_id))
    if row is None:
        raise ProblemError("not-found", detail="no such device")
    return row
