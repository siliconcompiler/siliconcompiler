'''
Who a caller is, what they are allowed, and which machines act as them.

🔴 **Extracted so that the API and the portal cannot drift.** The rule the
portal exists under is that every authorization decision goes through the same
code the handlers call -- and a decision written inside a route handler is a
decision the portal has to re-implement to reuse. This project has shipped a
missing ``WHERE user_id =`` once already; the mitigation is that there is one
place to forget it, not two.

Nothing here builds a response. A route renders JSON and the portal renders a
page, and what they share is the question underneath.
'''

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.store import now

__all__ = ["account_limits", "devices_for", "effective_limits", "lifetime",
           "owned_device", "set_limit", "usage", "user", "OVERRIDABLE"]


def user(store, user_id: str):
    row = store.one("SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise ProblemError("not-found")
    return row


# Which limits a `user_limits` row may override. One today, and the list is
# here rather than derived from the table so that adding a column is a
# deliberate act in two places rather than an accident in one.
OVERRIDABLE = ("max_download_bytes",)


def effective_limits(store, config, user_id: str) -> Dict[str, Any]:
    '''The deployment's ceilings with this account's overrides applied.

    🔴 **Sparse, three-valued, and `-1` never reaches a client.** A missing row
    or a NULL column inherits the deployment's number; `-1` means unlimited and
    the resolver turns it into the wire's `null`, because the wire had already
    spent `null` on *unlimited* while the table needed it for *inherit*.
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

    ⚠️ Six members and not ``GET /v1``'s key set. Four keys appear in both
    blocks and a client combines only those.

    🆕 **`max_download_bytes` is the seventh, and it is here because it is the
    only one that can differ per account.** `GET /v1` carries no credential and
    cannot vary by caller, so a per-user ceiling has nowhere else to be
    published -- which makes this the block a client must read for it. The
    deployment's default stays on `GET /v1`, and the two disagreeing is exactly
    what an override looks like.
    '''
    ceiling = dict(config.limits)
    ceiling.update(overrides or {})

    return {
        "concurrent_jobs": ceiling["concurrent_jobs"],
        "concurrent_nodes": None,           # reported-only, and unset here
        "pending_uploads": ceiling["pending_uploads"],
        "max_job_nodes": ceiling["max_job_nodes"],
        "devices": None,                    # null = unlimited, not zero
        "job_retention_days": ceiling["job_retention_days"],
        # null here means UNLIMITED, which is the wire's meaning everywhere.
        "max_download_bytes": ceiling["max_download_bytes"],
    }


def set_limit(store, user_id: str, name: str, value: Optional[int],
              actor: str, note: Optional[str] = None) -> None:
    '''Record one operator decision about one account.

    ⚠️ The only writer, and it is not the portal. A ceiling is policy, and this
    deployment has no admin mode -- so the account screen renders this and
    never sets it.
    '''
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


def lifetime(store, user_id: str) -> Dict[str, Any]:
    '''Everything this account has ever run, for the screen.

    🔴 Deliberately NOT part of `usage`, which is what `GET /v1/me` publishes.
    That object answers *what am I consuming against my allowance*, and every
    window in it is a calendar month for that reason -- an all-time total has
    no allowance and no reset, so putting it there would mean a published
    member a client has to be told to ignore. A screen can show a running
    total without the API promising one.

    ⚠️ Derived from `jobs`, like `usage`, and with the same limitation: a job
    that is still running contributes nothing until it finishes, because what
    is being summed is `finished_at - started_at`. A metering table would fix
    that and buy a billing history nobody here bills against.
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
    '''The machines that may act as this caller.

    Non-empty in this profile, which is not incidental: the key binding on
    first contact is the only real control the mode has, and this list plus the
    revoke button is its visible half.
    '''
    return store.all(
        "SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL "
        "ORDER BY enrolled_at DESC", (session.user_id,))


def owned_device(store, session, device_id):
    '''A device, or a 404 that does not say whether it exists.

    🔴 The one place the ownership predicate for a device is written. The
    404-not-403 rule: a 403 would confirm the id belongs to somebody. What it
    conceals here is bounded by an identity nothing verifies, which is worth
    knowing but is not a reason to leak it.
    '''
    row = store.one(
        "SELECT * FROM devices WHERE id = ? AND user_id = ?",
        (device_id, session.user_id))
    if row is None:
        raise ProblemError("not-found", detail="no such device")
    return row
