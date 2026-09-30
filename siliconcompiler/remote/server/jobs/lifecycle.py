'''
What a caller does to a job once it exists: list it, read it, cancel it, delete
it, archive it (surface §16 to §19).

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import shutil

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    MAX_REASON, TERMINAL_STATES, _CONTROL, _decode_cursor, _encode_cursor, _flag, _limit,
    logger)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.state.store import now


class LifecycleMixin:
    '''What a caller does to a job once it exists.'''

    ######################################################################
    # 16, 17. list and get
    ######################################################################

    def listing(self, session, args) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        '''The caller's jobs, newest first, over a keyset cursor.

        Ordered by `(created_at, id)` descending, which is the ordering the
        partial indexes carry -- and the reason the ids are UUIDv7: the
        tiebreaker sorts the same way the timestamp does, so the cursor needs no
        second column.
        '''
        where = ["user_id = ?", "deleted_at IS NULL"]
        params: List[Any] = [session.user_id]

        # 🔴 A filter repeats to OR within its key; keys AND together
        # (surface §16) -- so `?archived=true&archived=false` is both views.
        def values(name):
            if hasattr(args, "getlist"):
                given = args.getlist(name)
            else:
                given = args.get(name)
                given = given if isinstance(given, list) else [] if given is None else [given]
            return [value for value in given if value != ""]

        def any_of(sql_for, choices):
            if not choices:
                return
            where.append("(" + " OR ".join(sql_for for _ in choices) + ")")
            params.extend(choices)

        archived = {_flag(value) for value in values("archived")} or {False}
        if archived == {True}:
            where.append("archived_at IS NOT NULL")
        elif archived == {False}:
            where.append("archived_at IS NULL")

        states = values("state")
        known = {row["state"] for row in self._store.all("SELECT state FROM job_states")}
        for state in states:
            if state not in known:
                raise ProblemError("invalid-request", detail=f"no such job state: {state}")
        any_of("state = ?", states)

        terminal = {_flag(value) for value in values("terminal")}
        if terminal == {True}:
            where.append(f"state IN ({', '.join('?' * len(TERMINAL_STATES))})")
            params.extend(sorted(TERMINAL_STATES))
        elif terminal == {False}:
            where.append(f"state NOT IN ({', '.join('?' * len(TERMINAL_STATES))})")
            params.extend(sorted(TERMINAL_STATES))

        for column in ("design", "jobname"):
            any_of(f"{column} = ?", values(column))
        any_of("manifest_flow = ?", values("flow"))

        if values("project"):
            raise ProblemError(
                "feature-unsupported", feature="projects",
                detail="this deployment has no projects")

        cursor = args.get("cursor")
        if cursor:
            created_at, job_id = _decode_cursor(cursor)
            where.append("(created_at < ? OR (created_at = ? AND id < ?))")
            params.extend([created_at, created_at, job_id])

        limit = _limit(args.get("limit"))

        rows = self._store.all(
            f"SELECT * FROM jobs WHERE {' AND '.join(where)} "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (*params, limit + 1))

        more = len(rows) > limit
        rows = rows[:limit]

        for row in rows:
            if row["state"] not in TERMINAL_STATES:
                self.reconcile(row)

        items = [self.wire(self._row(row["id"]), nodes=False) for row in rows]
        next_cursor = _encode_cursor(rows[-1]) if more and rows else None
        return items, next_cursor

    def get(self, session, job_id: str) -> Dict[str, Any]:
        job = self.owned(session, job_id)
        if job["state"] not in TERMINAL_STATES:
            self.reconcile(job)
            job = self._row(job_id)
        return self.wire(job)

    ######################################################################
    # 18, 19. cancel and delete
    ######################################################################

    def cancel(self, session, job_id: str, reason: Optional[str]) -> Dict[str, Any]:
        '''Endpoint 18. `cancelling` where work is in flight -- `staging`,
        `queued` or `running` -- and `cancelled` where there is none.

        🔴 **The write is conditional on the state it moves from**, so a job the
        scheduler has already ended stays as it is, and the `202` carries it.
        The scheduler side then writes `cancelled` once the work stops; a job
        still staging has no scheduler id, and its `cancelled` is written here,
        by the staging thread, when it stops.
        '''
        job = self.owned(session, job_id)

        if reason is not None:
            # 🔴 Checked, never repaired (surface §6), and never echoed.
            if not isinstance(reason, str) or len(reason) > MAX_REASON \
                    or _CONTROL.search(reason):
                raise ProblemError(
                    "invalid-request",
                    detail=f"reason is one line of free text of at most {MAX_REASON} "
                           "characters")

        if job["state"] in TERMINAL_STATES or job["state"] == "cancelling":
            # Idempotent: the caller's intent is already satisfied.
            return self.wire(job)

        in_flight = job["state"] in ("staging", "queued", "running")
        target = "cancelling" if in_flight else "cancelled"
        said = reason or "cancelled"

        with self._store.transaction():
            moved = self._transition_if(job["id"], job["state"], target,
                                        actor=session.user_id, reason=reason,
                                        state_reason=said)
            if moved:
                self._store.execute(
                    "UPDATE jobs SET cancel_requested_at = ? WHERE id = ?",
                    (now(), job["id"]))
                if target == "cancelled":
                    self._store.execute(
                        "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
                    self._storage.discard_upload(job["id"])

        if moved and job["scheduler_job_id"]:
            self._dispatcher.cancel(job["scheduler_job_id"],
                                    node_job_ids=self._node_job_ids(job))

        return self.wire(self._row(job["id"]))

    def _transition_if(self, job_id: str, from_state: str, to_state: str, **kwargs) -> bool:
        '''`_transition`, only where the job is still in ``from_state``.'''
        current = self._row(job_id)
        if current is None or current["state"] != from_state:
            return False
        self._transition(job_id, from_state, to_state, **kwargs)
        return True

    def whodunnit(self, session, job=None) -> str:
        """Who acted, in words: the person, by display name, and -- where it is
        their job -- that they own it. Never the device, and never an id."""
        row = self._store.one("SELECT display_name FROM users WHERE id = ?",
                              (session.user_id,))
        name = ((row["display_name"] if row else None) or "").strip()
        if job is not None and job["user_id"] == session.user_id:
            return f"{name}, its owner" if name else "its owner"
        return name or "another user"

    def delete(self, session, job_id: str) -> None:
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            return                                      # idempotent

        if job["state"] not in TERMINAL_STATES:
            raise ProblemError(
                "job-state-conflict",
                detail="cancel this job before deleting it: 'delete it and its "
                       "data' cannot mean 'hide it and keep spending'")

        shutil.rmtree(self.job_root(job["user_id"], job["id"]), ignore_errors=True)
        shutil.rmtree(self.job_bundles(job["id"]), ignore_errors=True)
        for path in (self.stream_index_path(job["id"]),
                     Path(f"{self.stream_index_path(job['id'])}.lock")):
            path.unlink(missing_ok=True)
        self._storage.discard_upload(job["id"])

        # 🔴 **An artifact under legal hold is never deleted** (entitlements
        # D54), by its owner or anybody: its row and its bytes stay, and the
        # rest go -- through `_unlink`, never a sweep of the job's directory,
        # which would take the held bytes with it.
        going = self._store.all(
            "SELECT id, location_id, storage_key FROM artifacts WHERE job_id = ? "
            "AND deleted_at IS NULL AND legal_hold_at IS NULL", (job["id"],))
        self._unlink(going)

        # The row stays, with `deleted_at` set: a `deleted` state was refused
        # because it would erase whether the job had completed, failed or been
        # rejected, which is the one fact you want when somebody asks where
        # their results went.
        with self._store.transaction():
            who = f"deleted by {self.whodunnit(session, job)}"
            self._store.execute(
                "UPDATE jobs SET deleted_at = ?, deleted_by = ?, delete_reason = ? "
                "WHERE id = ?", (now(), session.user_id, who, job["id"]))
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                "  delete_reason = ? WHERE job_id = ? AND deleted_at IS NULL "
                "  AND legal_hold_at IS NULL",
                (now(), session.user_id, who, job["id"]))

    def discard_node(self, session, job_id: str, step: str, index: str,
                     reason: str) -> int:
        '''Throw away what ONE node produced, and keep the run.

        🔴 **The node is the unit of deletion, and per-artifact would be the
        wrong grain.** There is no deleting a node's reports and keeping its
        logs: the node archive holds both, so removing one row while the
        archive still carried a copy would free nothing and make its
        `deleted_at` a claim the disk disagreed with. Taking the coordinates
        together is what actually reclaims the space.

        ⚠️ Job-level rows -- the manifest, the run's own log -- belong to no
        node and are never touched here. `discard_artifacts` is the whole-job
        version and takes those too.
        '''
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            raise ProblemError(
                "not-found", detail="this job's data was already deleted")

        if self._store.one(
                'SELECT 1 FROM job_nodes WHERE job_id = ? AND step = ? '
                'AND "index" = ?', (job_id, step, index)) is None:
            raise ProblemError(
                "not-found", detail=f"no node {step}/{index} in this job")

        rows = self._store.all(
            'SELECT id, location_id, storage_key FROM artifacts WHERE job_id = ? '
            'AND step = ? AND "index" = ? AND deleted_at IS NULL '
            "AND legal_hold_at IS NULL", (job_id, step, index))

        self._unlink(rows)
        if rows:
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                '  delete_reason = ? WHERE job_id = ? AND step = ? AND "index" = ? '
                "  AND deleted_at IS NULL AND legal_hold_at IS NULL",
                (now(), session.user_id, reason, job_id, step, index))

        # 🔴 The node's working tree goes with them, for the same reason the
        # whole-job version takes the job's: it is what these were indexed
        # FROM, so leaving it reclaims the smaller copy and keeps the larger
        # one. Only this node's directory, so the rest of the run is untouched.
        work = (self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / step / index)
        shutil.rmtree(work, ignore_errors=True)

        logger.info(f"discarded {len(rows)} artifact(s) of {job_id} {step}/{index}")
        return len(rows)

    def _unlink(self, rows) -> None:
        '''Drop the bytes of some artifact rows. The rows are the caller's; an
        object another live row still names is left where it is.'''
        going = [row["id"] for row in rows]
        for row in rows:
            if artifacts.referenced_elsewhere(self._store, row, going):
                continue
            try:
                path = self._storage.artifact_path(row["storage_key"])
                if path.is_file():
                    path.unlink()
            except OSError as e:
                logger.debug(f"could not unlink {row['storage_key']}: {e}")

    def discard_artifacts(self, session, job_id: str, reason: str) -> int:
        '''Throw away what a run produced, and keep the run.

        🔴 **Not `DELETE /v1/jobs/{id}`, and the difference is the whole point.**
        Deleting the JOB sets `jobs.deleted_at`, which by the contract takes it
        out of the collection entirely -- the job is gone from every listing and
        reachable only by id. That is far more than somebody means when they
        ask to reclaim the space a finished run is using.

        This deletes the OBJECTS: the bytes go, every row stays and stays
        listed, and the job keeps its states, its timings and its place in the
        list. *Where did my results go* remains answerable, which is the entire
        reason the artifact rows outlive their contents.

        ⚠️ A legal hold is skipped rather than refused. One held object should
        not stop a person clearing the other forty, and the table would reject
        the write anyway -- an artifact cannot be both held and deleted.
        '''
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            raise ProblemError(
                "not-found", detail="this job's data was already deleted")

        rows = self._store.all(
            "SELECT id, location_id, storage_key FROM artifacts "
            "WHERE job_id = ? AND deleted_at IS NULL AND legal_hold_at IS NULL",
            (job_id,))

        self._unlink(rows)
        if rows:
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                "  delete_reason = ? WHERE job_id = ? AND deleted_at IS NULL "
                "  AND legal_hold_at IS NULL",
                (now(), session.user_id, reason, job_id))

        # 🔴 The build tree goes with them. It is what the artifacts were
        # indexed FROM, so leaving it would reclaim the smaller copy and keep
        # the larger one -- and the portal reads a node's log out of it, which
        # would then outlive the artifact that replaced it.
        shutil.rmtree(self.job_root(job["user_id"], job["id"]),
                      ignore_errors=True)

        logger.info(f"discarded {len(rows)} artifact(s) of {job_id}")
        return len(rows)

    def archive(self, session, job_id: str, archived: bool) -> None:
        '''Put a job away, or take it back out.

        ⚠️ **A view preference and not an operation on the run**, which is why
        the contract gives it no endpoint and names the portal as its writer.
        Nothing about the job changes: a direct read still answers, every
        subresource still works, and only the default collection stops
        including it.

        🔴 Terminal only, and the constraint is in the schema as well as here.
        A queued job holds a `concurrent_jobs` slot and a created one holds a
        live upload grant, so hiding a job that is still going makes *why can I
        not submit* unanswerable from any screen.
        '''
        job = self.owned(session, job_id)

        if archived and job["state"] not in TERMINAL_STATES:
            raise ProblemError(
                "job-state-conflict",
                detail="only a job that has stopped can be archived: hiding a "
                       "running one makes 'why can I not submit' unanswerable")

        if archived:
            self._store.execute(
                "UPDATE jobs SET archived_at = ?, archived_by = ? WHERE id = ?",
                (now(), session.user_id, job_id))
        else:
            self._store.execute(
                "UPDATE jobs SET archived_at = NULL, archived_by = NULL "
                "WHERE id = ?", (job_id,))
