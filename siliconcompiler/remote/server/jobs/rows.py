'''
A job's rows and the objects they become: ownership, state moves, and the job
object as §17 publishes it.

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.errors import bound, ProblemError
from siliconcompiler.remote.server.jobs.common import (
    MAX_REASON, TERMINAL_NODE_STATES, TERMINAL_STATES, _CANCELS, _NoLongerStaging, _bounded,
    _error, _members_json, logger)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import now


class RowsMixin:
    '''A job's rows and the objects they become.'''

    ######################################################################
    # Rows, and the objects they become
    ######################################################################

    def owned(self, session, job_id: str):
        '''A job, or a 404 that does not say whether it exists.

        The predicate is the whole point of the identity work: a stranger
        holding an id is not the owner. A 403 would confirm the id belongs to
        somebody.
        '''
        row = self._store.one(
            "SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, session.user_id))
        if row is None:
            raise ProblemError("not-found", detail="no such job")
        return row

    def _row(self, job_id: str):
        return self._store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def resolved_versions(self, job) -> Dict[str, List[str]]:
        """Every distribution version this job's images declare.

        The job image and each node's, taken together: a forty-node flow over
        six tools resolves six images, and *what did this run* is the union of
        what they hold.
        """
        rows = self._store.all(
            'SELECT step, "index", image_id FROM job_nodes WHERE job_id = ? '
            "  AND image_id IS NOT NULL", (job["id"],))
        runs_python = self._runs_user_python(job)

        return images.contents_of(
            self._store, [job["image_id"], *(row["image_id"] for row in rows)],
            [row["image_id"] for row in rows if (row["step"], row["index"]) in runs_python])

    def _runs_user_python(self, job):
        '''Each node whose task runs the user's Python, as the manifest's read
        found it -- the summary stored in the job root, which it validated.'''
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

        🔴 Read back off `job_state_transitions` rather than stored a second
        time on the job. The transition into the state the job is in IS the
        record of why it got there -- `jobs` has an `error_type` and no
        `error_detail`, and adding one would mean two writers for one fact.

        The runner writes it into the progress file as the exception that
        ended the run, and the reaper and the refusal path write theirs the
        same way, so every terminal state has one and it is the same string
        the portal has always rendered in the history table.
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
        listed (surface D308), so the server's own records are listed as it
        ends -- the `staging` record and the operators' `diagnostics`, which a
        job that never ran leaves and nothing else indexes. In the caller's
        transaction; a run's own output is indexed before it, by
        `_index`.'''
        job = self._row(job_id)
        if job is None:
            return
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
        body = {
            "id": job["id"],
            "state": job["state"],
            # Published rather than derivable on purpose. The rule is read
            # `terminal`, do not switch on the name -- which is what makes an
            # eleventh state additive instead of breaking.
            "terminal": job["state"] in TERMINAL_STATES,
            # 🔴 Every state the job has entered, oldest first (surface §17;
            # D278): how long it spent in each, and why it moved where the
            # server knows. Never empty.
            "transitions": self._transitions(job),
            "design": job["design"],
            "jobname": job["jobname"],
            "flow": job["manifest_flow"],
            # The user id is what GET /v1/me returns, so a client compares it;
            # the name is display only. Nothing here verifies who anybody is.
            "owner": {"id": job["user_id"], "name": self._display_name(job["user_id"])},
            "project": None,
            "created_at": job["created_at"],
            "submitted_at": job["submitted_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
            "archived_at": job["archived_at"],
            "deleted_at": job["deleted_at"],
            # Set exactly when deleted_at is: every job deletion is a person's,
            # so a job carries no deleted_cause (D279).
            "deleted_reason": job["deleted_reason"] if job["deleted_at"] else None,
            "error": _error(job["error_type"], self._why(job), job["error_members"])
            if job["state"] in ("failed", "rejected") else None,
        }
        # Only the live staging phase: a transition's reason, a cancel's
        # included, is on its entry of `transitions`.
        if job["state"] == "staging" and job["state_reason"] and body["error"] is None:
            body["state_reason"] = bound(job["state_reason"])

        # No portal URL: a job's page is asked for by its id, at
        # `POST /v1/auth/browser`, when a client is about to open it (surface
        # D309).

        # 🔴 What it actually ran in. Once a request can carry a range, nothing
        # else answers *what did this job run* -- the descriptor says what was
        # asked for and this says what the server chose.
        #
        # ⚠️ Absent rather than empty where nothing was resolved: on a
        # deployment that runs jobs on the host there is no image and no
        # answer, and `{}` would claim this job ran nothing at all.
        resolved = self.resolved_versions(job)
        if resolved:
            body["resolved_versions"] = resolved

        # Echoed, and absent where the run continues from nothing.
        continued = self._continuations_of(job["id"])
        if continued:
            body["continues_from"] = [{"step": step, "index": index, "job_id": from_job}
                                      for step, index, from_job in continued]

        # 🔴 Present only while the server is asking -- in `created` or
        # `awaiting_input` -- and never `[]` (D127): what to send, and nothing
        # else.
        if job["state"] in ("created", "awaiting_input") and job["upload_sources"]:
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
                    # The job's error's shape: null unless the node failed
                    # (surface §17, *A node's `error`*).
                    "error": _error(row["error_type"], members=row["error_members"]),
                }
                if row["state_reason"] and not row["error_type"]:
                    # Only a cancel writes a node's `state_reason`: the
                    # caller's words, served whole (surface D288).
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
        '''`transitions`, from `job_state_transitions`: each state entered,
        with when, and a reason where one was recorded.

        🔴 **Two kinds of reason, kept apart by the state entered.** Every
        reason on a move into `cancelling` or `cancelled` is the cancel's -- the
        caller's words, checked at the boundary to at most `MAX_REASON` with no
        control character, or the default *cancelled* -- and is served whole
        (surface D288), whatever `max_detail_chars` is set to. Every other
        reason is this server's own, bounded and scrubbed like `detail`.
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

    def _display_name(self, user_id: str) -> str:
        row = self._store.one("SELECT display_name FROM users WHERE id = ?", (user_id,))
        return (row["display_name"] if row else None) or user_id

    def _refuse(self, session, job, problem: ProblemError) -> ProblemError:
        '''Record a refusal, and hand back the problem for the caller to raise.

        A refused job is `rejected` and never `failed`: a refused job never ran,
        and keeping it out of `failed` is what stops a run of entitlement
        denials reading as a run of broken designs.

        🔴 **What is stored is the problem the caller was handed, whole.** The
        two used to be written separately and drifted: a job the scheduler
        would not take was recorded as `run-failed` while its submitter was
        told `not-ready`, so the person and the page they were looking at
        disagreed about a job neither of them could re-read. Taking the
        `ProblemError` itself is what makes that impossible rather than
        unlikely.

        🔴 **And the stored reason is the problem's `detail`, not its slug.**
        The slug is already `jobs.error_type` and is published as `error.type`;
        writing it a second time as prose told a person nothing they could not
        already see, while `detail` -- *which* limit, *which* mismatch -- was
        computed one line later and thrown away.
        '''
        kept = _kept(problem)
        if not kept:
            # 🔴 Before the transition, so the job is never read as terminal
            # with what it was refused for still listed.
            self._forget_upload(job, problem.error.slug)
        with self._store.transaction():
            current = self._row(job["id"])
            if current["state"] != job["state"]:
                # Cancelled while staging checked it: what the owner did stands.
                raise _NoLongerStaging(job["id"])
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = ?, finished_at = ? "
                "WHERE id = ?",
                (problem.error.uri, _members_json(problem.members), now(), job["id"]))
            self._transition(job["id"], job["state"], "rejected",
                             actor=session.user_id if session else None,
                             reason=problem.detail or problem.error.slug)
        self._storage.discard_upload(job["id"])
        return problem


def _kept(problem: ProblemError) -> bool:
    '''Whether a refused job's upload is kept: not where it was refused for
    what it must not carry -- `upload-forbidden`, a `credential`, or a private
    dataroot's value, the `unrequested_member` that names its `keypath`
    (surface D307, D308).'''
    if problem.error.slug == "upload-forbidden":
        return False
    if problem.error.slug != "archive-rejected":
        return True
    reason = problem.members.get("reason")
    return not (reason == "credential"
                or (reason == "unrequested_member" and problem.members.get("keypath")))
