'''
A job's rows and the objects they become: ownership, state moves, and the job
object as §17 publishes it.
'''

import json

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.errors import bound, ProblemError
from siliconcompiler.remote.server.jobs.common import (
    MAX_REASON, _CANCELS, _NoLongerStaging, _bounded, _error, _members_json, logger)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import (
    PENDING_STATES, TERMINAL_NODE_STATES, TERMINAL_STATES, now)


class RowsMixin:
    '''A job's rows and the objects they become.'''

    def owned(self, session, job_id: str):
        '''A job, or a 404 that does not say whether it exists: a 403 would
        confirm the id belongs to somebody.'''
        row = self._store.one(
            "SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, session.user_id))
        if row is None:
            raise ProblemError("not-found", detail="no such job")
        return row

    def _row(self, job_id: str):
        return self._store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def resolved_versions(self, job) -> Dict[str, List[str]]:
        """Every distribution version this job's images declare: the union of
        the job image and each node's."""
        rows = self._store.all(
            'SELECT step, "index", image_id FROM job_nodes WHERE job_id = ? '
            "  AND image_id IS NOT NULL", (job["id"],))
        runs_python = self._runs_user_python(job)

        return images.contents_of(
            self._store, [job["image_id"], *(row["image_id"] for row in rows)],
            [row["image_id"] for row in rows if (row["step"], row["index"]) in runs_python])

    def _runs_user_python(self, job):
        '''Each node whose task runs the user's Python, from the read's stored
        summary.'''
        from siliconcompiler.remote.server.running import runspec

        path = self.job_root(job["user_id"], job["id"]) / runspec.SUMMARY_FILENAME
        try:
            nodes = json.loads(path.read_text()).get("nodes") or []
        except (OSError, ValueError, AttributeError):
            return set()
        return {(entry.get("step"), entry.get("index")) for entry in nodes
                if isinstance(entry, dict) and entry.get("python")}

    def _why(self, job) -> Optional[str]:
        '''What actually went wrong, in the run's own words.

        🔴 Read off the transition into the current state, never stored twice:
        an `error_detail` column would be a second writer for one fact.
        '''
        if not job["error_type"]:
            return None

        row = self._store.one(
            "SELECT reason FROM job_state_transitions "
            "WHERE job_id = ? AND to_state = ? ORDER BY id DESC LIMIT 1",
            (job["id"], job["state"]))
        return row["reason"] if row else None

    def _transition(self, job_id: str, from_state: Optional[str], to_state: str,
                    actor: Optional[str] = None, reason: Optional[str] = None,
                    state_reason: Optional[str] = None) -> None:
        if to_state in TERMINAL_STATES:
            self._list_records(job_id)
        # `state_reason` describes the state being entered, so every move resets it.
        self._store.execute(
            "UPDATE jobs SET state = ?, state_changed_at = ?, state_reason = ? WHERE id = ?",
            (to_state, now(), _bounded(state_reason, MAX_REASON) if state_reason else None,
             job_id))
        self._store.execute(
            "INSERT INTO job_state_transitions "
            "(job_id, from_state, to_state, actor_id, reason) VALUES (?, ?, ?, ?, ?)",
            (job_id, from_state, to_state, actor, reason))

    def _list_records(self, job_id: str) -> None:
        '''🔴 A job turns terminal only once every artifact it will list is
        listed (surface D308): the server's own records, here, in the caller's
        transaction; a run's output is `_index`'s, before it.'''
        job = self._row(job_id)
        root = self.job_root(job["user_id"], job_id)
        try:
            artifacts.collect_staging(self._store, self._storage, self._config, job, root)
            artifacts.collect_diagnostics(self._store, self._storage, self._config, job, root)
        except OSError as e:
            logger.warning(f"{job_id}: could not list the server's records: {e}")

    def _phase(self, job_id: str, what: str) -> None:
        '''The staging phase, as the job's `state_reason`.'''
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET state_reason = ? WHERE id = ? AND state = 'staging'",
                (what, job_id))

    def wire(self, job, nodes: bool = True) -> Dict[str, Any]:
        '''The job object, as §17 publishes it.'''
        owner = self._store.one("SELECT display_name FROM users WHERE id = ?",
                                (job["user_id"],))
        body = {
            "id": job["id"],
            "state": job["state"],
            # Published so clients never switch on the name, keeping new
            # states additive.
            "terminal": job["state"] in TERMINAL_STATES,
            # 🔴 Every state entered, oldest first, never empty (surface §17;
            # D278).
            "transitions": self._transitions(job),
            "design": job["design"],
            "jobname": job["jobname"],
            "flow": job["manifest_flow"],
            # A client compares the id with GET /v1/me; the name is display only.
            "owner": {"id": job["user_id"], "name": owner["display_name"] or job["user_id"]},
            "project": None,
            "created_at": job["created_at"],
            "submitted_at": job["submitted_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
            "archived_at": job["archived_at"],
            "deleted_at": job["deleted_at"],
            # Every job deletion is a person's, so no deleted_cause (D279).
            "deleted_reason": job["deleted_reason"] if job["deleted_at"] else None,
            "error": _error(job["error_type"], self._why(job), job["error_members"])
            if job["state"] in ("failed", "rejected") else None,
        }
        # Only the live staging phase; other reasons are on `transitions`.
        if job["state"] == "staging" and job["state_reason"] and body["error"] is None:
            body["state_reason"] = bound(job["state_reason"])

        # No portal URL: a client asks `POST /v1/auth/browser` (surface D309).

        # 🔴 What the server chose, where the descriptor says what was asked.
        # ⚠️ Absent rather than `{}` on the host, which would claim it ran
        # nothing.
        resolved = self.resolved_versions(job)
        if resolved:
            body["resolved_versions"] = resolved

        # Echoed, and absent where the run continues from nothing.
        continued = self._continuations_of(job["id"])
        if continued:
            body["continues_from"] = [{"step": step, "index": index, "job_id": from_job}
                                      for step, index, from_job in continued]

        # 🔴 Present only while the server is asking, and never `[]` (D127).
        if job["state"] in PENDING_STATES and job["upload_sources"]:
            asking = json.loads(job["upload_sources"])
            if asking:
                body["upload_sources"] = asking

        rows = self._store.all(
            'SELECT step, "index", state, started_at, finished_at, exit_code, error_type, '
            'error_members, state_reason FROM job_nodes WHERE job_id = ? '
            'ORDER BY step, "index"',
            (job["id"],))

        if nodes:
            body["nodes"] = []
            for row in rows:
                node = {
                    "step": row["step"],
                    "index": row["index"],
                    "state": row["state"],
                    "terminal": row["state"] in TERMINAL_NODE_STATES,
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "exit_code": row["exit_code"],
                    # Null unless the node failed (surface §17).
                    "error": _error(row["error_type"], members=row["error_members"]),
                }
                if row["state_reason"] and not row["error_type"]:
                    # Only a cancel writes it: the caller's words (surface D288).
                    node["state_reason"] = row["state_reason"]
                body["nodes"].append(node)

        def count(state):
            return sum(1 for row in rows if row["state"] == state)

        body["progress"] = {
            "total_count": len(rows),
            "completed_count": count("completed"),
            "failed_count": count("failed"),
            "skipped_count": count("skipped"),
            "cancelled_count": count("cancelled"),
        }
        return body

    def _transitions(self, job) -> List[Dict[str, Any]]:
        '''`transitions`: each state entered, when, and any recorded reason.

        🔴 A reason entering `cancelling` or `cancelled` is the caller's, checked
        at the boundary and served whole (surface D288); every other is this
        server's, bounded and scrubbed like `detail`.
        '''
        rows = self._store.all(
            "SELECT to_state, occurred_at, reason FROM job_state_transitions "
            "WHERE job_id = ? ORDER BY occurred_at, rowid", (job["id"],))
        entries = []
        for row in rows:
            entry = {"state": row["to_state"], "at": row["occurred_at"]}
            if row["reason"]:
                entry["reason"] = row["reason"] if row["to_state"] in _CANCELS \
                    else bound(row["reason"])
            entries.append(entry)
        return entries or [{"state": job["state"], "at": job["state_changed_at"]}]

    def _refuse(self, job, problem: ProblemError) -> ProblemError:
        '''Record a refusal, and hand back the problem for the caller to raise.

        `rejected`, never `failed`: a refused job never ran. 🔴 What is stored
        is the problem the caller was handed, whole, so the two cannot drift;
        its reason is the `detail`, since the slug is already `error.type`.
        '''
        kept = _kept(problem)
        if not kept:
            # 🔴 Before the transition, so the job is never read as terminal
            # with what it was refused for still listed.
            self._forget_upload(job, problem.error.slug)
        with self._store.transaction():
            current = self._row(job["id"])
            if current["state"] != job["state"]:
                # Cancelled meanwhile: what the owner did stands.
                raise _NoLongerStaging(job["id"])
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = ?, finished_at = ? "
                "WHERE id = ?",
                (problem.error.uri, _members_json(problem.members), now(), job["id"]))
            self._transition(job["id"], job["state"], "rejected",
                             reason=problem.detail or problem.error.slug)
        self._storage.discard_upload(job["id"])
        return problem


def _kept(problem: ProblemError) -> bool:
    '''Whether a refused job's upload is kept: not where it carried what it
    must not, a `credential` or a private dataroot (surface D307, D308).'''
    if problem.error.slug != "archive-rejected":
        return True
    reason = problem.members.get("reason")
    return not (reason == "credential"
                or (reason == "unrequested_member" and problem.members.get("keypath")))
