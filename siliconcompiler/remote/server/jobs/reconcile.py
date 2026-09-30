'''
Reconciliation: what the run says it is doing, written into the store, and a
job whose run is lost or silent ended.

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json

from siliconcompiler.remote.server.errors import TYPE_BASE
from siliconcompiler.remote.server.jobs.common import (
    SCHEDULER_QUERY_FLOOR, TERMINAL_NODE_STATES, _after, _ago, _members_json, _node_error,
    _node_metrics, logger)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.state.store import now


class ReconcileMixin:
    '''Reconciliation.'''

    ######################################################################
    # Reconciliation: what the run says it is doing
    ######################################################################

    def reconcile(self, job) -> None:
        '''Read the run's progress file and move the store to match.

        The run writes a file beside its manifest; nothing calls back. That is
        what lets the process running the flow and the process serving this API
        be on different machines with nothing between them but a filesystem.
        '''
        if self.abandon_if_expired(job):
            return

        if job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while staging, and no staging thread is left to write
            # its `cancelled` -- a restart in between.
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
                # Its sources are being fetched -- or were, by a process that
                # has since restarted. Picked up again; a fetch that finished is
                # held and costs nothing.
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
            # 🔴 The run has stopped saying anything, and that is evidence the
            # scheduler cannot give. See `_silent`.
            logger.warning(f"{job['id']} has not reported since "
                           f"{progress.get('heartbeat')}")
            self._lost(job)
        elif reported == "running" and job["scheduler_job_id"] and not self._alive(job):
            # 🔴 Look again before declaring it lost. "The run says it is
            # going" and "the scheduler has never heard of it" are read at two
            # different moments, and a run that finished in between satisfies
            # both -- the progress file in hand is stale and the scheduler's
            # answer is fresh. Everything between the two readings widens that
            # window, and indexing a node's results is not cheap.
            #
            # A job that really is gone reads the same file twice and is still
            # `running`, which costs one stat to be sure of.
            job_root = self.job_root(job["user_id"], job["id"])
            settled = runspec.read_progress(
                job_root / runspec.PROGRESS_FILENAME,
                job_root)

            if settled and settled.get("state") in ("completed", "failed"):
                # 🔴 Its nodes as the settled file has them, before the job
                # ends: the ones recorded above are from the stale file, and a
                # node that finished between the two readings would otherwise
                # end `cancelled` with the job, as if it had never run.
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
            if state == "completed":
                # 🔴 `completed` only once its artifacts are listed: a client
                # that sees it fetches them.
                self._index_node(job, step, index)

            # 🔴 A published field with no writer is a published field that
            # lies. A node's error was null on every node this server had ever
            # run, including the ones that failed, so a client could not tell
            # *this node is why* from *this node is fine* without re-deriving
            # it from the state it already had. `run-failed` is registered
            # precisely for this: it is one of the three slugs that are never
            # an HTTP response and only ever a `type` on an error object.
            # A node whose image would not pull was interrupted, not failed
            # (implementation-notes §10): the runner says so from the
            # runtime's own pull error, and `detail` names the image, or the
            # limit a node ran into.
            error_type, error_members = _node_error(state, node)

            self._store.execute(
                'UPDATE job_nodes SET state = ?, started_at = ?, finished_at = ?, '
                '  exit_code = ?, error_type = ?, error_members = ? '
                'WHERE job_id = ? AND step = ? AND "index" = ? '
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (state, node.get("started_at"), node.get("finished_at"),
                 None if state == "cancelled" else runspec.exit_code(node.get("exit_code")),
                 error_type, error_members, job["id"], step, index))

            if state in TERMINAL_NODE_STATES and state != "completed":
                # Indexed as the node finishes rather than as the job does, so
                # a node that is done answers /logs with its archive while the
                # rest of the flow is still running -- which is precisely the
                # moment somebody tailing it asks.
                self._index_node(job, step, index)

    @staticmethod
    def _final(job, reported: str) -> str:
        '''The state a job ends in, for a run that reported ``reported``.'''
        if job["state"] == "cancelling":
            # The cancel won the race to the scheduler; what the run managed
            # to finish before it died does not change what was asked for.
            return "cancelled"
        return reported

    def _silent(self, progress) -> bool:
        '''Whether a run that claims to be going has stopped saying so.

        🔴 **The backstop for a scheduler that is wrong, which is not
        hypothetical.** A dynamic node killed without deleting itself leaves
        Slurm reporting its jobs RUNNING for ever on a machine that is gone --
        observed, for thirteen minutes, on a container that no longer existed.
        Every other check here asks the scheduler, so every other check
        believed it.

        The runner writes a heartbeat on a timer rather than on node
        transitions, because a single OpenROAD node runs for half an hour
        without a transition: *nothing written lately* and *dead* had to be
        told apart, and only a clock can do it.

        ⚠️ **No heartbeat means no opinion.** A run started by a runner older
        than this writes none, and the honest answer for it is the one this
        server always gave -- ask the scheduler. Treating a missing field as
        silence would declare every in-flight job of an upgrade dead.
        '''
        beat = progress.get("heartbeat")
        if not beat:
            return False

        patience = self._config["run_heartbeat_seconds"]
        return beat < _ago(patience)

    def abandon_if_expired(self, job) -> bool:
        '''A job whose upload never arrived reaches a terminal state.

        🔴 **`abandoned` is the tenth state and this is the only thing that
        writes it.** Until now a job created and never uploaded to sat in
        `created` for ever: it held a `pending_uploads` slot, it appeared on
        every listing, and -- because the portal refreshes until a job is
        terminal -- its page reloaded itself indefinitely for a run that was
        never going to happen.

        ⚠️ **Two ways to expire, because there are two ways to stall.** A job
        that asked for a grant has one that lapses, which is the contract's
        case. A job that was created and never asked has no expiry at all, so
        the clock runs from its creation instead -- otherwise the only jobs
        that could ever be abandoned are the ones that got furthest.

        Returns whether it moved, so a caller can stop looking at it.
        '''
        if job["state"] not in ("created", "awaiting_input"):
            return False

        # The later of the two: old enough by the operator's clock, AND not
        # holding a grant that is still good. A job whose upload is legitimately
        # in flight has a live grant and is never taken.
        # ⚠️ From the latest transition, not from creation: a job sent back
        # to `awaiting_input` (D124) gets the clock again.
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

        🔴 Marking a node `cancelled` in the store does not cancel anything. A
        node is a scheduler job of its own, so a run that died abruptly leaves
        its nodes running with nobody watching -- and the record then says
        `cancelled` about work that is still burning a compute slot. Seen for
        real: an orchestrator that failed left an OpenROAD detailed route
        running for another fifty-five minutes.

        ⚠️ Only the jobs the scheduler still HAS. scancel answers an error for
        one that has finished, and a warning per finished node is how an
        operator learns to ignore warnings.
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
        '''Per node: the image it ran in, and the scheduler job it became.

        Neither is published on the wire -- a registry path and a scheduler id
        are deployment detail -- so this is what the portal reads instead, and
        it goes through the same ownership predicate every other read does.

        ⚠️ It BACKFILLS. Accounting can lag the scheduler by seconds, so a node
        that finished just before its job did can be missing from every poll
        that ran and present by the time somebody looks. Asking at read time is
        what turns that from a permanent gap into a late answer, and it costs
        nothing once every node has an id.
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
        '''Write down which scheduler job each node became.

        🔴 Two things need it and neither can be done without it. A cancel has
        to stop the work and not only the process coordinating it, now that a
        node is a job of its own; and *which Slurm job was that* is the question
        a person brings to a support thread, which nothing else can answer.

        🔴 **Throttled, because this is the only part of a poll that leaves the
        machine.** Every call is a `squeue`, and every `squeue` is one or more
        RPCs into slurmctld -- so at a one-second poll interval it would be one
        per second per running job, which is exactly the load
        `--max-connections` exists to throttle. `force` is for the two callers
        that cannot accept a stale answer: a cancel, which needs the ids to
        reach the work, and the last look before a job goes terminal.

        ⚠️ Asked for once and then never again. Only the nodes still missing an
        id are looked up, so a job whose nodes are all recorded costs nothing --
        which is what keeps this inside the once-per-run poll rather than
        turning it into per-node polling.
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
            # A gap in the record, and nothing more: this runs inside a poll
            # that is answering somebody's request about the job itself.
            logger.debug(f"could not read node jobs for {job['id']}: {e}")
            return

        if not found:
            return

        with self._store.transaction():
            for (step, index), scheduler_id in found.items():
                self._store.execute(
                    "UPDATE job_nodes SET scheduler_job_id = ? "
                    'WHERE job_id = ? AND step = ? AND "index" = ?',
                    (scheduler_id, job["id"], step, index))

    def _node_job_ids(self, job):
        '''Every node job this run has, as far as the store knows.

        Refreshed first, because a node dispatched since the last poll has no
        id recorded and is exactly the one a cancel most needs to reach.
        '''
        self._record_node_jobs(job, force=True)

        return [row["scheduler_job_id"] for row in self._store.all(
            "SELECT scheduler_job_id FROM job_nodes "
            "WHERE job_id = ? AND scheduler_job_id IS NOT NULL", (job["id"],))]

    def _may_ask_scheduler(self, job_id: str) -> bool:
        """Whether enough time has passed to ask the scheduler again.

        ⚠️ In memory and per process, which is the right shape rather than a
        shortcut: it is a rate limit on THIS process's outbound calls, and two
        API processes each asking at their own floor is exactly what a floor
        per process means. Nothing depends on it being exact, and nothing is
        lost when it resets -- the worst case is one extra `squeue`.
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
            # Cannot tell is not the same as gone, and declaring a live job lost
            # is the more expensive mistake.
            return True

    def _lost(self, job) -> None:
        '''The scheduler no longer has it and it never said how it ended.

        🔴 Unless somebody was cancelling it, in which case this IS how it
        ended. A cancel kills the run, so the very next poll finds a scheduler
        with no job and a progress file still saying `running` -- which is
        exactly the shape of a lost job and is not one. Telling a person their
        cluster ate the run they just stopped is worse than saying nothing.
        '''
        self._reap_orphans(job)

        if job["state"] == "cancelling":
            logger.info(f"{job['id']} is gone from the scheduler, as asked")
            self._settle_cancelled(job)
            return

        logger.warning(f"{job['id']} is gone from the scheduler with no result")
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (f"{TYPE_BASE}/run-interrupted", now(), job["id"]))

            # 🔴 A node that had STARTED did not get cancelled, it died. The
            # contract glosses `cancelled` as *the job ended before this node
            # started*, so using it for a node that was running says something
            # false about the one node somebody will look at first -- it is
            # where the work stopped. `failed` is what *started and did not
            # finish* means, and the environment ended it: `run-interrupted`.
            self._store.execute(
                "UPDATE job_nodes SET state = 'failed', error_type = ?, error_members = ? "
                "WHERE job_id = ? AND state = 'running'",
                (f"{TYPE_BASE}/run-interrupted",
                 _members_json({"detail": "the run ended while this node was running, "
                                          "and never recorded how"}), job["id"]))

            # Everything the run never reached. These really did end before
            # they started.
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')", (job["id"],))
            self._transition(
                job["id"], job["state"], "failed",
                reason="the scheduler no longer has this job and the run never "
                       "recorded how it ended")

    def _settle_cancelled(self, job) -> None:
        '''A cancel that has taken effect: `cancelling` to `cancelled`, and
        every node it stopped `cancelled`, with no exit code and the cancel's
        reason. No error: nothing went wrong.'''
        with self._store.transaction():
            current = self._row(job["id"])
            if current is None or current["state"] != "cancelling":
                return
            said = current["state_reason"] or "cancelled"
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                "  state_reason = ? WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (said, job["id"]))
            self._transition(job["id"], "cancelling", "cancelled", reason=said,
                             state_reason=said)

    def _finish(self, job, state: str, progress) -> None:
        # Belt and braces, and cheap: a run that ended by crashing rather than
        # by finishing can leave the same orphans a lost one does, and on a
        # deployment where a node is not a scheduler job this asks nothing.
        if state == "failed":
            self._reap_orphans(job)

        # 🔴 One more look before nothing looks again. The LAST node to finish
        # is dispatched after the second-to-last poll and finishes before the
        # job does, so the poll that records the others has nothing to find for
        # it -- and once the job is terminal no poll runs at all. A diamond
        # flow came back with three of its four nodes carrying a scheduler id.
        self._record_node_jobs(job, force=True)

        if job["state"] == state:
            return

        # Indexed before the transition, so a job is never readable as terminal
        # with an empty listing: the first thing a client does on seeing
        # `terminal` is ask what the run produced.
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
            # A limit is `run-failed` with `detail` naming it; an image that
            # would not pull is `run-interrupted`, naming the image.
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
            # 🔴 A terminal job has only terminal nodes: whatever the run never
            # finished ended with it.
            said = (job["state_reason"] or "cancelled") if state == "cancelled" else None
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                "  state_reason = ? WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (said, job["id"]))
            # 🔴 A cancelled job's transition carries the cancel's reason, and
            # nothing of the server's: that is what `_transitions` serves whole.
            self._transition(job["id"], job["state"], state,
                             reason=said if state == "cancelled" else reason,
                             state_reason=said)

    def _record_metrics(self, job) -> None:
        '''Each node's metrics and records, into `job_nodes`, once, as the job
        ends: what the portal's metrics panel reads (implementation-notes §E,
        *The portal's metrics come from a table*).

        🔴 **Plain JSON, never SiliconCompiler** (contract §1, its second
        paragraph): the run's final manifest is read with `json`, under a size
        limit, and nothing read this way decides a refusal or a grant.
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
        None -- through the same ownership check as every read of a job.'''
        self.owned(session, job_id)
        row = self._store.one(
            'SELECT metrics, records FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        if row is None:
            return None
        return {"metrics": json.loads(row["metrics"]) if row["metrics"] else None,
                "records": json.loads(row["records"]) if row["records"] else None}

    def _index(self, job) -> None:
        '''Turn what the run left on disk into rows.

        Never fatal: a job that ran is a job that ran, and failing to index its
        output must not make it read as failed. The listing is empty, which is
        a legal answer, and the log says why.
        '''
        try:
            artifacts.collect(self._store, self._storage, self._config, job,
                              self.job_root(job["user_id"], job["id"]))
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index the results of {job['id']}: {e}")

    def _index_node(self, job, step: str, index: str) -> None:
        """Index one node's log, reports and archive, as it finishes."""
        try:
            artifacts.collect_node(
                self._store, self._storage, self._config, job,
                self.job_root(job["user_id"], job["id"]), step, index)
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index {job['id']} {step}/{index}: {e}")
