'''
Reconciliation: what the run says it is doing, written into the store, and a
job whose run is lost or silent ended.
'''

import json

from siliconcompiler.remote.server.errors import TYPE_BASE
from siliconcompiler.remote.server.jobs.common import (
    SCHEDULER_QUERY_FLOOR, _after, _ago, _members_json, _node_error, _node_metrics, logger)
from siliconcompiler.remote.server.outputs import artifacts, record
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.state.store import (
    PENDING_STATES, TERMINAL_NODE_STATES, TERMINAL_STATES, now)

# A node the run has not finished with, as a `job_nodes` condition and its params.
_UNFINISHED = f"state NOT IN ({', '.join('?' * len(TERMINAL_NODE_STATES))})"
_TERMINAL_NODES = tuple(sorted(TERMINAL_NODE_STATES))


class ReconcileMixin:
    '''Reconciliation.'''

    def reconcile(self, job) -> None:
        '''Read the run's progress file and move the store to match. Nothing
        calls back, so the run and this API share only a filesystem.'''
        if self.abandon_if_expired(job):
            return

        if job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while staging, with no staging thread left after a restart.
            with self._preparing_lock:
                busy = job["id"] in self._preparing
            if not busy:
                self._settle_cancelled(job)
            return

        root = self.job_root(job["user_id"], job["id"])
        progress = runspec.read_progress(
            root / runspec.PROGRESS_FILENAME, root)

        if progress is None:
            # Nothing written yet. Either it has not started, or it never will.
            if job["scheduler_job_id"] and not self._alive(job):
                self._lost(job)
            elif job["state"] == "staging":
                # Picked up again after a restart; a finished fetch is held.
                self._start_preparing(job["id"])
            return

        self._record_nodes(job, progress)
        self._record_node_jobs(job)

        reported = progress.get("state")
        started_at = progress.get("started_at")

        if job["state"] == "queued" and started_at:
            with self._store.transaction():
                self._store.execute(
                    "UPDATE jobs SET started_at = ? WHERE id = ?", (started_at, job["id"]))
                self._transition(job["id"], "queued", "running")
            job = self._row(job["id"])

        if reported in ("completed", "failed"):
            self._finish(job, self._final(job, reported), progress)
        elif reported == "running" and self._silent(progress):
            # 🔴 Evidence the scheduler cannot give; see `_silent`.
            logger.warning(f"{job['id']} has not reported since "
                           f"{progress.get('heartbeat')}")
            self._lost(job)
        elif reported == "running" and job["scheduler_job_id"] and not self._alive(job):
            # 🔴 Look again before declaring it lost: a run that finished
            # between reading the progress file and asking the scheduler looks
            # lost by both.
            job_root = self.job_root(job["user_id"], job["id"])
            settled = runspec.read_progress(
                job_root / runspec.PROGRESS_FILENAME,
                job_root)

            if settled and settled.get("state") in ("completed", "failed"):
                # 🔴 Nodes from the settled file before the job ends, or one
                # that finished in between would end `cancelled`.
                self._record_nodes(job, settled)
                self._finish(job, self._final(job, settled["state"]), settled)
            else:
                self._lost(job)

    def _record_nodes(self, job, progress) -> None:
        '''Each node's state as ``progress`` has it, into the store. A node
        that already reached a terminal state keeps it.'''
        for key, node in (progress.get("nodes") or {}).items():
            step, _, index = key.partition("/")
            state = node.get("state", "pending")
            if state in TERMINAL_NODE_STATES:
                # 🔴 Any terminal state only once the node's artifacts are listed
                # (surface D310), indexed as the node finishes, not the job.
                self._index_node(job, step, index)

            # 🔴 Written on every node, or a failed node's published `error`
            # would be null (implementation-notes §10).
            error_type, error_members = _node_error(state, node)

            self._store.execute(
                'UPDATE job_nodes SET state = ?, started_at = ?, finished_at = ?, '
                '  exit_code = ?, error_type = ?, error_members = ? '
                f'WHERE job_id = ? AND step = ? AND "index" = ? AND {_UNFINISHED}',
                (state, node.get("started_at"), node.get("finished_at"),
                 None if state == "cancelled" else runspec.exit_code(node.get("exit_code")),
                 error_type, error_members, job["id"], step, index, *_TERMINAL_NODES))

    @staticmethod
    def _final(job, reported: str) -> str:
        '''The state a job ends in, for a run that reported ``reported``.'''
        if job["state"] == "cancelling":
            # The cancel won the race; what the run finished does not change it.
            return "cancelled"
        return reported

    def _silent(self, progress) -> bool:
        '''Whether a run that claims to be going has stopped saying so.

        🔴 The backstop for a wrong scheduler: a killed dynamic node can leave
        Slurm reporting RUNNING for ever. The runner's heartbeat is on a timer,
        since one node can run half an hour without a transition.

        ⚠️ No heartbeat is silence: the runner stamps one on every write.
        '''
        return (progress.get("heartbeat") or "") < _ago(self._config["run_heartbeat_seconds"])

    def abandon_if_expired(self, job) -> bool:
        '''A job whose upload never arrived reaches a terminal state; returns
        whether it moved.

        🔴 The only writer of `abandoned`: otherwise the job holds a
        `pending_uploads` slot for ever.
        '''
        if job["state"] not in PENDING_STATES:
            return False

        # The later of the operator's clock and a live grant, so an upload in
        # flight is never taken; a job never granted one still expires.
        # ⚠️ From the latest transition, so a job sent back (D124) starts again.
        deadline = max(
            _after(job["state_changed_at"] or job["created_at"],
                   self._config.limits["abandon_after_seconds"]),
            job["upload_grant_expires_at"] or "")
        if deadline > now():
            return False

        logger.info(f"{job['id']} was never uploaded to; abandoning it")
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?",
                (now(), job["id"]))
            self._transition(
                job["id"], job["state"], "abandoned",
                reason="the upload never arrived and the grant expired")

        self._storage.discard_upload(job["id"])
        return True

    def _reap_orphans(self, job) -> None:
        '''Stop the work a run left behind when it went away.

        🔴 Each node is a scheduler job of its own, so marking it `cancelled`
        stops nothing. ⚠️ Only jobs the scheduler still HAS, so finished ones
        raise no warnings.
        '''
        nodes = [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ?', (job["id"],))]

        try:
            orphans = self._dispatcher.running_nodes(job["id"], nodes)
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"could not look for orphans of {job['id']}: {e}")
            return

        if not orphans:
            return

        logger.warning(f"{job['id']} left {len(orphans)} node job(s) behind; "
                       "cancelling them")
        self._dispatcher.cancel(None, node_job_ids=orphans)

    def node_placements(self, session, job_id: str):
        '''Per node: the image it ran in, and the scheduler job it became --
        deployment detail for the portal, never on the wire.

        ⚠️ It BACKFILLS, since accounting can lag the scheduler by seconds.
        '''
        job = self.owned(session, job_id)
        self._record_node_jobs(job)

        refs = {row["id"]: row["registry_ref"]
                for row in self._store.all("SELECT id, registry_ref FROM images")}

        return {(row["step"], row["index"]):
                (refs.get(row["image_id"]), row["scheduler_job_id"])
                for row in self._store.all(
                    'SELECT step, "index", image_id, scheduler_job_id '
                    "FROM job_nodes WHERE job_id = ?", (job["id"],))}

    def _record_node_jobs(self, job, force: bool = False) -> None:
        '''Write down which scheduler job each node became, so a cancel reaches
        the work and support can answer *which Slurm job was that*.

        🔴 Throttled (`SCHEDULER_QUERY_FLOOR`): each call is a `squeue`. `force`
        is for a cancel and the last look before a job goes terminal. Only
        nodes still missing an id are asked about.
        '''
        missing = [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes '
            "WHERE job_id = ? AND scheduler_job_id IS NULL", (job["id"],))]

        if not missing:
            return
        if not force and not self._may_ask_scheduler(job["id"]):
            return

        try:
            found = self._dispatcher.node_jobs(job["id"], missing)
        except Exception as e:                                   # noqa: BLE001
            # A gap in the record, never a failed request.
            logger.debug(f"could not read node jobs for {job['id']}: {e}")
            return

        if not found:
            return

        # Each node claimed once, by whichever concurrent backfill writes first.
        claimed = []
        with self._store.transaction():
            for (step, index), scheduler_id in found.items():
                done = self._store.execute(
                    "UPDATE job_nodes SET scheduler_job_id = ? "
                    'WHERE job_id = ? AND step = ? AND "index" = ? '
                    "  AND scheduler_job_id IS NULL",
                    (scheduler_id, job["id"], step, index))
                if done.rowcount:
                    claimed.append((step, index, scheduler_id))
        self._keep_late_records(job, claimed)

    def _keep_late_records(self, job, nodes) -> None:
        '''Keep the scheduler's record of each node whose id arrived after its
        job was indexed, usually the last node, in its `diagnostics`.'''
        if not nodes:
            return
        row = self._row(job["id"])
        if row["state"] not in TERMINAL_STATES or row["deleted_at"]:
            return
        root = self.job_root(row["user_id"], row["id"])
        if not root.is_dir():
            return
        for step, index, scheduler_id in nodes:
            try:
                said = self._dispatcher.describe(scheduler_id)
                if said:
                    record.keep(root, "slurm.txt", said, step=step, index=index)
                artifacts.collect_diagnostics(self._store, self._storage, self._config,
                                              row, root, step, index)
            except Exception as e:                               # noqa: BLE001
                logger.error(f"could not keep the scheduler's record of {row['id']} "
                             f"{step}/{index}: {e}")

    def _node_job_ids(self, job):
        '''Every node job this run has, refreshed first: a node dispatched since
        the last poll is the one a cancel most needs to reach.'''
        self._record_node_jobs(job, force=True)

        return [row["scheduler_job_id"] for row in self._store.all(
            "SELECT scheduler_job_id FROM job_nodes "
            "WHERE job_id = ? AND scheduler_job_id IS NOT NULL", (job["id"],))]

    def _may_ask_scheduler(self, job_id: str) -> bool:
        """Whether enough time has passed to ask the scheduler again.

        ⚠️ In memory and per process, deliberately: a rate limit on THIS
        process's calls, whose reset costs one extra `squeue`.
        """
        import time as _time

        now_at = _time.monotonic()
        last = self._asked.get(job_id, 0.0)
        if now_at - last < SCHEDULER_QUERY_FLOOR:
            return False

        self._asked[job_id] = now_at
        return True

    def _alive(self, job) -> bool:
        try:
            return self._dispatcher.is_alive(job["scheduler_job_id"])
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not ask the scheduler about {job['id']}: {e}")
            # Cannot tell is not gone: declaring a live job lost costs more.
            return True

    def _lost(self, job) -> None:
        '''The scheduler no longer has it and it never said how it ended.

        🔴 Unless it was being cancelled, which looks exactly like a lost job
        and is how a cancel ends.
        '''
        self._reap_orphans(job)

        if job["state"] == "cancelling":
            logger.info(f"{job['id']} is gone from the scheduler, as asked")
            self._settle_cancelled(job)
            return

        logger.warning(f"{job['id']} is gone from the scheduler with no result")
        # 🔴 What it left, the operators' record above all, listed before the
        # job turns terminal (surface D310).
        self._index(job)
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (f"{TYPE_BASE}/run-interrupted", now(), job["id"]))

            # 🔴 A node that had STARTED died, not cancelled: `cancelled` means
            # *the job ended before this node started*.
            self._store.execute(
                "UPDATE job_nodes SET state = 'failed', error_type = ?, error_members = ? "
                "WHERE job_id = ? AND state = 'running'",
                (f"{TYPE_BASE}/run-interrupted",
                 _members_json({"detail": "the run ended while this node was running, "
                                          "and never recorded how"}), job["id"]))

            # Everything the run never reached.
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL "
                f"WHERE job_id = ? AND {_UNFINISHED}", (job["id"], *_TERMINAL_NODES))
            self._transition(
                job["id"], job["state"], "failed",
                reason="the scheduler no longer has this job and the run never "
                       "recorded how it ended")

    def _settle_cancelled(self, job) -> None:
        '''A cancel that has taken effect: the job and every unfinished node
        `cancelled`, with the cancel's reason and no error. A stopped run is
        indexed first (surface D310).'''
        if job["scheduler_job_id"] and job["state"] == "cancelling":
            self._index(job)
        with self._store.transaction():
            current = self._row(job["id"])
            if current["state"] != "cancelling":
                return
            said = current["state_reason"] or "cancelled"
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                f"  state_reason = ? WHERE job_id = ? AND {_UNFINISHED}",
                (said, job["id"], *_TERMINAL_NODES))
            self._transition(job["id"], "cancelling", "cancelled", reason=said,
                             state_reason=said)

    def _finish(self, job, state: str, progress) -> None:
        # A crashed run can leave the same orphans a lost one does.
        if state == "failed":
            self._reap_orphans(job)

        # 🔴 One more look: the LAST node can start and finish between polls,
        # and once the job is terminal no poll runs.
        self._record_node_jobs(job, force=True)

        if job["state"] == state:
            return

        # Indexed before the transition: a client seeing `terminal` lists at once.
        self._index(job)
        self._record_metrics(job)

        reason = progress.get("error")
        nodes = sorted((progress.get("nodes") or {}).items())
        limited = [f"{key} exceeded its {node['limit']} limit"
                   for key, node in nodes if isinstance(node, dict) and node.get("limit")]
        interrupted = [f"{key} could not start: its image "
                       f"{(node['interrupted'] or {}).get('image')} could not be pulled"
                       for key, node in nodes
                       if isinstance(node, dict) and isinstance(node.get("interrupted"), dict)]
        if state == "failed" and (interrupted or limited):
            reason = "; ".join(interrupted + limited + ([reason] if reason else []))
        slug = "run-interrupted" if interrupted else "run-failed"

        with self._store.transaction():
            if state == "failed":
                self._store.execute(
                    "UPDATE jobs SET error_type = ? WHERE id = ?",
                    (f"{TYPE_BASE}/{slug}", job["id"]))
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?",
                (progress.get("finished_at") or now(), job["id"]))
            # 🔴 A terminal job has only terminal nodes.
            said = (job["state_reason"] or "cancelled") if state == "cancelled" else None
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                f"  state_reason = ? WHERE job_id = ? AND {_UNFINISHED}",
                (said, job["id"], *_TERMINAL_NODES))
            # 🔴 A cancel's transition carries only the cancel's reason, which
            # `_transitions` serves whole.
            self._transition(job["id"], job["state"], state,
                             reason=said if state == "cancelled" else reason,
                             state_reason=said)

    def _record_metrics(self, job) -> None:
        '''Each node's metrics and records into `job_nodes`, once, as the job
        ends, for the portal's panel (implementation-notes §E).

        🔴 Plain JSON, never SiliconCompiler (contract §1), and nothing read
        this way decides a refusal or a grant.
        '''
        root = self.job_root(job["user_id"], job["id"])
        found = _node_metrics(root / job["design"] / job["jobname"]
                              / f"{job['design']}.pkg.json")
        if not found:
            return
        with self._store.transaction():
            for (step, index), (metrics, records) in found.items():
                self._store.execute(
                    'UPDATE job_nodes SET metrics = ?, records = ? '
                    'WHERE job_id = ? AND step = ? AND "index" = ?',
                    (json.dumps(metrics), json.dumps(records), job["id"], step, index))

    def node_metrics(self, session, job_id: str, step: str, index: str):
        '''One node's metrics and records as the job's end recorded them, or
        None.'''
        self.owned(session, job_id)
        row = self._store.one(
            'SELECT metrics, records FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        if row is None:
            return None
        return {"metrics": json.loads(row["metrics"]) if row["metrics"] else None,
                "records": json.loads(row["records"]) if row["records"] else None}

    def _index(self, job) -> None:
        '''Turn what the run left on disk into rows. Never fatal: a failed index
        must not make a run read as failed.'''
        try:
            self._keep_scheduler_record(job)
            artifacts.collect(self._store, self._storage, self._config, job,
                              self.job_root(job["user_id"], job["id"]))
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index the results of {job['id']}: {e}")

    def _keep_scheduler_record(self, job) -> None:
        '''What the scheduler says of the job and each node, into the operators'
        `diagnostics` (surface D295), while the scheduler still remembers.'''
        root = self.job_root(job["user_id"], job["id"])
        if job["scheduler_job_id"]:
            said = self._dispatcher.describe(job["scheduler_job_id"])
            if said:
                record.keep(root, "slurm.txt", said)
        for row in self._store.all(
                'SELECT step, "index", scheduler_job_id FROM job_nodes '
                "WHERE job_id = ? AND scheduler_job_id IS NOT NULL", (job["id"],)):
            said = self._dispatcher.describe(row["scheduler_job_id"])
            if said:
                record.keep(root, "slurm.txt", said, step=row["step"], index=row["index"])

    def _index_node(self, job, step: str, index: str) -> None:
        """Index one node's log, reports and archive, as it finishes."""
        try:
            artifacts.collect_node(
                self._store, self._storage, self._config, job,
                self.job_root(job["user_id"], job["id"]), step, index)
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index {job['id']} {step}/{index}: {e}")
