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

from typing import Any, Dict, List

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.store import now

__all__ = ["account_limits", "devices_for", "lifetime", "owned_device",
           "usage", "user"]


def user(store, user_id: str):
    row = store.one("SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise ProblemError("not-found")
    return row


def account_limits(config) -> Dict[str, Any]:
    '''The account's allowance -- six members, and not ``GET /v1``'s key set.

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
