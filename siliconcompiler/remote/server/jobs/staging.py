'''
Staging: the manifest's read, the sources fetched, the job sent back for what
cannot be had, and every refusal before a node runs.

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json

from pathlib import Path
from typing import Any, Dict, Tuple

from siliconcompiler.remote import owners
from siliconcompiler.remote.server.errors import bound, ERRORS, ProblemError
from siliconcompiler.remote.server.jobs.common import (
    _NoLongerStaging, _ServerFailure, _bounded, _problem_from, _resources, logger,
    requirements)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.running.dispatch import DispatchError
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.staging import manifestread, sandbox
from siliconcompiler.remote.server.state.store import now


class StagingMixin:
    '''Staging.'''

    def _start_preparing(self, job_id: str) -> None:
        import threading

        with self._preparing_lock:
            if job_id in self._preparing:
                return
            self._preparing.add(job_id)
        threading.Thread(target=self._prepare, args=(job_id,), daemon=True,
                         name=f"prepare-{job_id[:8]}").start()

    def _prepare(self, job_id: str) -> None:
        '''Everything between submit and `queued`: unpack and check the
        upload, fetch what the run needs and the server does not hold, copy
        earlier results, build environments, then dispatch -- or send the job
        back asking for what could not be had.

        In parallel, a timeout per source and one deadline for the job. A
        transient failure is retried until the deadline; a permanent one --
        and whatever is still missing at the deadline -- goes back to the
        client, which has the credentials the server does not.

        🔴 A refusal found in the upload ends the job `rejected`; this server's
        own failure ends it `failed`, `staging-failed`, never `rejected`.
        '''
        import time
        from concurrent.futures import ThreadPoolExecutor, wait as futures_wait

        from siliconcompiler.remote.server.staging.sources import Permanent, Transient

        try:
            job = self._row(job_id)
            if job is None or job["state"] != "staging":
                raise _NoLongerStaging(job_id)
            root = self.job_root(job["user_id"], job_id)
            unpacked = root / job["design"] / job["jobname"]
            if job["unpack_pending"]:
                summary, entries = self._unpack(job)
            else:
                summary = self._stored_summary(job, root)
                entries = self._account(None, job, summary, unpacked)

            wanted = {}
            for entry in entries:
                if entry.status == owners.FETCH:
                    wanted.setdefault((entry.source, entry.ref), []).append(entry)
            if wanted:
                self._phase(job_id, "fetching sources")

            timeout = self._config["fetch_timeout_seconds"]
            deadline = time.monotonic() + self._config["fetch_deadline_seconds"]
            # What only the client can send goes back with whatever fails to
            # fetch: one trip to `awaiting_input`, asking for all of it.
            failed = [(entry, "this server does not hold it and cannot fetch it")
                      for entry in entries if entry.status == owners.ASK]
            pause = 2
            while wanted:
                # 🔴 Watched rather than waited on: a cancel stops the fetch.
                pool = ThreadPoolExecutor(max_workers=4)
                tried = {key: pool.submit(self._fetch, key[0], key[1], timeout)
                         for key in wanted}
                while not all(future.done() for future in tried.values()):
                    futures_wait(list(tried.values()), timeout=1)
                    if self._row(job_id)["state"] != "staging":
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise _NoLongerStaging(job_id)
                pool.shutdown(wait=False)
                last = {}
                for key, future in tried.items():
                    try:
                        future.result()
                        wanted.pop(key)
                    except Permanent as e:
                        logger.info(f"{job_id}: a source cannot be fetched: {e}")
                        failed.extend((entry, str(e)) for entry in wanted.pop(key))
                    except Transient as e:
                        logger.info(f"{job_id}: a source did not answer, retrying: {e}")
                        last[key] = str(e)
                if wanted and time.monotonic() + pause >= deadline:
                    for key, entries_of in wanted.items():
                        why = f"no answer before the deadline ({last.get(key, 'timed out')})"
                        failed.extend((entry, why) for entry in entries_of)
                    wanted = {}
                elif wanted:
                    time.sleep(pause)
                    pause = min(pause * 2, 60)
                    if self._row(job_id)["state"] != "staging":
                        raise _NoLongerStaging(job_id)

            job = self._row(job_id)
            if job["state"] != "staging":
                raise _NoLongerStaging(job_id)

            if failed:
                self._send_back(job, failed)
                return

            # Everything in hand: a missing file in a fetched copy is refused
            # here, from `staging` -- and then it queues, and only moves on.
            entries = self._account(None, job, summary, unpacked)

            # The results of each node this run reads and does not run, from
            # the earlier job that ran it (surface D175).
            copies = self._account_upstream(None, job, summary, unpacked)
            if copies:
                self._phase(job_id, "copying earlier results")
            self._copy_results(job, unpacked, copies)

            # The job's Python packages: installed here where nodes run on this
            # host, so one that will not install rejects the job before any
            # node runs; built into an image on each one a node running the
            # user's Python resolved to where they run in containers -- which
            # needs the images resolved first. A package no configured index
            # has sends the job back for its wheel.
            absent = self._install_on_host(job, summary)
            plan = None
            if not absent:
                plan, absent = self._build_environments(
                    job, summary, self._resolve_images(None, job, summary))
            if self._row(job_id)["state"] != "staging":
                raise _NoLongerStaging(job_id)
            if absent:
                self._send_back(self._row(job_id), [], python=absent)
                return

            # `queued` only once the scheduler holds it.
            self._phase(job_id, "handing the job to the scheduler")
            self._dispatch(None, self._row(job_id), summary, entries, plan=plan)
        except ProblemError:
            # Already recorded on the job by `_refuse`.
            pass
        except _NoLongerStaging:
            # Cancelled while it staged: nothing holds it, so this is where its
            # `cancelled` is written.
            job = self._row(job_id)
            if job is not None and not job["scheduler_job_id"]:
                self._settle_cancelled(job)
        except _ServerFailure as e:
            self._fail_staging(job_id, str(e))
        except Exception as e:                                   # noqa: BLE001
            logger.exception(f"could not stage {job_id}")
            self._fail_staging(job_id, f"this server could not get the job ready: "
                                       f"{type(e).__name__}")
        finally:
            with self._preparing_lock:
                self._preparing.discard(job_id)
            self._store.release()

    def _fail_staging(self, job_id: str, detail: str) -> None:
        '''This server's own failure while staging: `failed`, `staging-failed`,
        with `detail` naming what failed -- and in the job-level `logs`.'''
        job = self._row(job_id)
        if job is not None and job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while it failed: what the owner did stands.
            self._settle_cancelled(job)
            return
        with self._store.transaction():
            job = self._row(job_id)
            if job is None or job["state"] != "staging":
                return
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = NULL, finished_at = ? "
                "WHERE id = ?", (ERRORS["staging-failed"].uri, now(), job_id))
            self._transition(job_id, "staging", "failed", reason=_bounded(detail))
        logger.warning(f"{job_id}: staging failed: {detail}")
        self._log_staging(self._row(job_id), detail)

    def _record_in_job_log(self, job, lines) -> None:
        '''Lines of the server's own record of a job, in the run log the
        job-level `logs` carries, each scrubbed like `detail`.'''
        from siliconcompiler.remote.server.running.dispatch import RUN_LOG

        root = self.job_root(job["user_id"], job["id"])
        try:
            root.mkdir(parents=True, exist_ok=True)
            with open(root / RUN_LOG, "a") as f:
                for line in lines:
                    f.write(f"{now()} {bound(line)}\n")
        except OSError as e:
            logger.warning(f"{job['id']}: could not write the job's log: {e}")

    def _log_staging(self, job, detail: str) -> None:
        '''What went wrong while staging, in the job-level `logs`, scrubbed
        like `detail`: the only account a person can reach of a job that never
        ran.'''
        from siliconcompiler.remote.server.running.dispatch import RUN_LOG

        root = self.job_root(job["user_id"], job["id"])
        try:
            root.mkdir(parents=True, exist_ok=True)
            with open(root / RUN_LOG, "a") as f:
                f.write(f"{now()} staging failed: {bound(detail)}\n")
            with self._store.transaction():
                artifacts.collect_run_log(self._store, self._storage, self._config,
                                          job, root)
        except OSError as e:
            logger.warning(f"{job['id']}: could not keep the staging log: {e}")

    def _fetch(self, source: str, ref: str, timeout: int) -> str:
        '''One source into this server's copy -- or, where `fetch_fails` is
        set, a permanent failure, so the job goes back to its client.'''
        from siliconcompiler.remote.server.staging.sources import Permanent

        if self._config["fetch_fails"]:
            raise Permanent("this server fetches nothing (fetch_fails is set, as in "
                            "test mode 4)")
        return self._sources.fetch(source, ref, timeout)

    def _send_back(self, job, failed, python=()) -> None:
        '''`staging` back to `awaiting_input` -- the one backwards edge
        (surface D130) -- naming what failed, and nothing else.

        ``failed`` is ``(entry, why)`` pairs for dataroots, and ``python`` each
        Python package no configured index has, which the client answers with
        its wheel (surface *How it is built, while the job is staging*). The
        transition says why for each: a job going backwards is the one move a
        person watching it will not expect, and "a source could not be
        fetched" tells them nothing about which or what to do.

        ⚠️ The job counts against `pending_uploads` again and frees its
        `concurrent_jobs` slot, both because those count by state; and
        `abandon_after_seconds` runs again from this transition.
        '''
        asked, reasons = [], []
        for entry, why in failed:
            if entry.wire not in asked:
                asked.append(entry.wire)
                reasons.append(f"{entry.kind} {entry.name} ({entry.dataroot}): {why}")
        for name in python:
            wire = {"kind": "python", "name": name}
            if wire not in asked:
                asked.append(wire)
                reasons.append(f"the Python package {name}: no index this server "
                               "installs from has it")
        reason = (f"{len(asked)} source(s) this server cannot supply, so the client "
                  "is asked to send them -- " + "; ".join(reasons))
        # 🔴 Remembered: the wheel answering one replaces its listed entry, and
        # is the one wheel allowed to overlap the lists.
        answered = sorted(set(json.loads(job["python_answered"] or "[]")) | set(python))
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_sources = ?, python_answered = ?, "
                "  submit_idempotency_key = NULL, submit_reply = NULL, submit_key_at = NULL "
                "WHERE id = ?", (json.dumps(asked), json.dumps(answered) if answered else None,
                                 job["id"]))
            self._transition(job["id"], "staging", "awaiting_input",
                             reason=_bounded(reason))

    def _refuse_staging(self, job, problem: ProblemError) -> ProblemError:
        '''`_refuse`, for a job that may have moved on while it waited.

        🔴 A build can take minutes, and a job cancelled meanwhile is
        `cancelled`: refusing it afterwards would rewrite what its owner did as
        something the server decided.
        '''
        current = self._row(job["id"])
        if current is None or current["state"] != "staging":
            raise _NoLongerStaging(job["id"])
        return self._refuse(None, current, problem)

    def _check_denied(self, session, job, summary) -> None:
        '''Refuse a run that uses a PDK, library or tool nobody may use.

        🔴 **After the manifest's read and before image resolution**: what the
        manifest names is only known once it is open, and *you may not use it*
        is asked before *can this server provide it* -- a denied tool this
        deployment has no image for is still a denial, and the caller should
        hear the answer that does not change when an image is added.

        ⚠️ The first one found is the one named, in the order PDK, library,
        tool, because the slug carries one `resource`. The detail says how many
        more there are, so fixing one is not followed by a surprise.

        ⚠️ **A summary that lies can evade this**, since the names are the
        read's (contract §1, *The summary cannot widen access*). That widens
        nothing here: `denied_resources` is a test stand-in for grants, and
        this profile has no controlled resources, no content index and no
        gate a summary feeds -- anyone may upload the same files anyway.
        '''
        wanted = _resources(summary) + [("tool", name) for name in summary["tools"]]

        denied = [(kind, name) for kind, name in wanted
                  if self._config.denied(kind, name)]
        if not denied:
            return

        kind, name = denied[0]
        more = len(denied) - 1
        raise self._refuse(session, job, ProblemError(
            "entitlement-denied", resource_kind=kind, resource=name,
            detail=f"this flow uses a {kind} this deployment does not allow"
                   + (f", and {more} more" if more else "")))

    ######################################################################
    # The manifest's read (contract §1)
    ######################################################################

    def _read(self, job, root: Path) -> Dict[str, Any]:
        '''Read the uploaded manifest -- in a process of its own, never this
        one -- and act on what the read says.

        🔴 **Contract §1, *No server process holding credentials parses a
        manifest*.** The read is `manifestread`, started contained by
        `sandbox`; what comes back is data, validated here, stored in the job
        root, and every check after it works from it. The descriptor said what
        the client believed; this is what it sent, and only this side is
        authoritative, which is why the checks run twice.

        Returns the summary, as :meth:`_summary` shapes it for the checks.
        '''
        unpacked = root / job["design"] / job["jobname"]
        if not (unpacked / f"{job['design']}.pkg.json").is_file():
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_missing",
                detail=f"the archive holds no {job['design']}.pkg.json at its root"))

        declared = requirements(json.loads(job["descriptor"]) or {})
        asked = manifestread.request(
            unpacked, job["design"], job["jobname"],
            (declared.get(images.BUCKETS["python"]) or {}).get("siliconcompiler"),
            self._skipped_upstream(job))
        try:
            raw = self._run_read(job, root, asked)
        except sandbox.Cancelled:
            raise _NoLongerStaging(job["id"]) from None
        except sandbox.ReadFailed as e:
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_invalid",
                detail=_bounded(f"the manifest has not been read: {e}"))) from None
        except OSError as e:
            raise _ServerFailure(f"this server could not start the manifest's read: "
                                 f"{e}") from None

        try:
            raw = manifestread.validate(raw)
        except manifestread.Invalid as e:
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_invalid",
                detail=_bounded(f"the manifest's read returned a summary this server "
                                f"cannot use: {e}"))) from None

        contained = raw.get("contained") or {}
        logger.info(f"{job['id']}: read its manifest in {raw.get('seconds')}s"
                    + ("" if contained.get("network") else ", with no network namespace")
                    + ("" if contained.get("limits") else ", with no resource limits"))

        # 🔴 In the job root, above the tree the upload expanded into, so no
        # upload can write it: a resumed staging and a follow-up's allowed set
        # read it back.
        runspec.write_json(root / runspec.SUMMARY_FILENAME, raw)
        return self._act_on(job, raw)

    def _run_read(self, job, root: Path, asked) -> Any:
        '''The read: in the job's own image where this deployment runs jobs in
        containers, and on this host otherwise, as a subprocess of this
        server's own SiliconCompiler -- the one version it advertises, so the
        one every job resolves to (profile §5, D63).'''
        limits = dict(
            timeout=self._config["manifest_read_timeout_seconds"],
            alive=lambda: (self._row(job["id"]) or {"state": None})["state"] == "staging",
            cpu_seconds=self._config["manifest_read_cpu_seconds"],
            memory_bytes=self._config["manifest_read_memory_bytes"])
        workdir = root / sandbox.READ_DIRNAME
        if not (self._config["containers"] and job["image_id"]):
            return sandbox.run_read(asked, workdir, **limits)

        image = self._store.one("SELECT registry_ref, digest FROM images WHERE id = ?",
                                (job["image_id"],))
        ref = images.pinned_ref(image["registry_ref"], image["digest"])
        if self._dispatcher.name != "slurm":
            # The docker daemon's own container, as nodes run in here.
            try:
                return sandbox.run_read_in_image(asked, workdir, ref, **limits)
            except OSError as e:
                # 🔴 The job's image that cannot be had while staging is this
                # server's failure, not the job's (database D145).
                raise _ServerFailure(str(e)) from None

        # A bundle of the job's own image, with nothing but its tree mounted.
        try:
            common = images.stage_bundle(self.bundles_root(), ref, image["digest"],
                                         mounts=self.container_mounts())
            bundle = images.read_bundle(common, self.job_bundles(job["id"]) / "read",
                                        root / job["design"] / job["jobname"])
        except Exception as e:                                   # noqa: BLE001
            raise _ServerFailure(f"this server could not unpack the image the job's "
                                 f"manifest is read in: {e}") from None
        try:
            return sandbox.run_read_in_bundle(self._dispatcher, asked, workdir, str(bundle),
                                              queue=self._config["batch_queue"], **limits)
        except DispatchError as e:
            raise _ServerFailure(f"this server's scheduler refused the manifest's read: "
                                 f"{e}") from None

    def _stored_summary(self, job, root: Path) -> Dict[str, Any]:
        '''The summary the job's last read stored, validated again; the read
        run once more where there is none -- a job staged before one was kept.'''
        path = root / runspec.SUMMARY_FILENAME
        try:
            with open(path, "rb") as f:
                body = f.read(manifestread.MAX_SUMMARY_BYTES + 1)
            if len(body) > manifestread.MAX_SUMMARY_BYTES:
                raise ValueError("too large")
            return self._summary(manifestread.validate(json.loads(body)))
        except (OSError, ValueError):
            return self._read(job, root)

    def _act_on(self, job, raw) -> Dict[str, Any]:
        '''Refuse what the read found, in the order the checks run.'''
        outcome = raw["outcome"]
        if outcome is not None and raw["nodes"] is None:
            raise self._refuse_staging(job, _problem_from(outcome))

        nodes = raw["nodes"] or []
        if len(nodes) > self._config.limits["max_job_nodes"]:
            raise self._refuse_staging(job, ProblemError(
                "node-limit-exceeded", limit="max_job_nodes",
                detail=f"{len(nodes)} nodes, and this server runs at most "
                       f"{self._config.limits['max_job_nodes']}"))
        if outcome is not None:
            raise self._refuse_staging(job, _problem_from(outcome))

        # The read compared them; this compares what it reported.
        if (raw["design"], raw["jobname"]) != (job["design"], job["jobname"]):
            raise self._refuse_staging(job, ProblemError(
                "declared-mismatch",
                detail=f"the manifest is {raw['design']}/{raw['jobname']} and the job "
                       f"is {job['design']}/{job['jobname']}"))
        return self._summary(raw)

    @staticmethod
    def _summary(raw) -> Dict[str, Any]:
        '''A validated summary, as the checks read it.

        🔴 **The tools are this server's reading of the nodes**, never the
        summary's own list: a check that widened nothing still has no reason to
        believe a second copy of the same answer.
        '''
        nodes = [(entry["step"], entry["index"]) for entry in raw["nodes"]]
        node_tools = {(entry["step"], entry["index"]): entry["tool"] for entry in raw["nodes"]}
        edges = [tuple(edge) for edge in raw["edges"]]
        # A node that runs where its input ran follows its FIRST input
        # (`runflow.inheriting_nodes`), in the edges' order.
        before: Dict[Tuple[str, str], Tuple[str, str]] = {}
        for from_step, from_index, to_step, to_index in edges:
            before.setdefault((to_step, to_index), (from_step, from_index))
        return {
            "raw": raw,
            "flow": raw["flow"],
            "nodes": nodes,
            "edges": edges,
            "node_tools": node_tools,
            "inherits": {(entry["step"], entry["index"]):
                         before.get((entry["step"], entry["index"]))
                         for entry in raw["nodes"] if entry["inherits"]},
            # Each node whose task runs the user's Python: where the job's
            # Python packages are installed.
            "python": [(entry["step"], entry["index"])
                       for entry in raw["nodes"] if entry["python"]],
            "tools": sorted({tool for tool in node_tools.values() if tool}),
            "pdk": raw["pdk"],
            "libraries": list(raw["libraries"]),
            "fpga": raw["fpga"],
            # What the flow reads (D129), from the `require` the client worked
            # out and carried here; None where it could not.
            "required": ({tuple(key) for key in raw["required"]}
                         if raw["required"] is not None else None),
            "upstream": [tuple(node) for node in raw["upstream"]],
            "values": raw["values"],
        }
