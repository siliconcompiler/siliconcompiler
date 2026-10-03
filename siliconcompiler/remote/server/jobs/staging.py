'''
Staging: the manifest's read, the sources fetched, the job sent back for what
cannot be had, and every refusal before a node runs.
'''

import json
import shutil

from pathlib import Path
from typing import Any, Dict, Tuple

from siliconcompiler.remote import owners
from siliconcompiler.remote.server.errors import ERRORS, ProblemError
from siliconcompiler.remote.server.jobs.common import (
    _NoLongerStaging, _ServerFailure, _StagingTimedOut, _bounded, _members_json,
    _problem_from, _resources, logger, requirements)
from siliconcompiler.remote.server.outputs import artifacts, record
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.running.dispatch import DispatchError
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.staging import manifestread, sandbox
from siliconcompiler.remote.server.state.store import TERMINAL_STATES, now


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
        '''Everything between submit and `queued`, in order: unpack and check
        the upload, fetch sources, copy earlier results, install or build the
        job's Python packages, dispatch -- or send the job back for what could
        not be had.

        Fetches run in parallel, transient failures retried to one deadline;
        what still fails goes back to the client, which holds the credentials.

        🔴 The whole pass is bounded by `max_staging_seconds` (surface D294);
        a resubmit gets a fresh deadline.

        🔴 A refusal found in the upload ends the job `rejected`; this server's
        own failure ends it `failed`, `staging-failed`, never `rejected`.
        '''
        import time
        from concurrent.futures import ThreadPoolExecutor, wait as futures_wait

        from siliconcompiler.remote.server.staging.sources import Permanent, Transient

        try:
            job = self._row(job_id)
            if job["state"] != "staging":
                raise _NoLongerStaging(job_id)
            root = self.job_root(job["user_id"], job_id)
            self._staging_deadlines[job_id] = time.monotonic() + self._staging_limit(job)
            record.begin_pass(root)

            unpacked = root / job["design"] / job["jobname"]
            if job["unpack_pending"]:
                summary, entries = self._unpack(job)
            else:
                summary = self._stored_summary(job, root)
                entries = self._account(job, summary, unpacked)
            self._check_staging_time(job_id, "reading the upload")

            wanted = {}
            for entry in entries:
                if entry.status == owners.FETCH:
                    wanted.setdefault((entry.source, entry.ref), []).append(entry)
            if wanted:
                self._phase(job_id, "fetching sources")

            timeout = self._config["fetch_timeout_seconds"]
            deadline = time.monotonic() + self._config["fetch_deadline_seconds"]
            # What only the client can send goes back with fetch failures, in
            # one trip to `awaiting_input`.
            failed = [(entry, "this server does not hold it and cannot fetch it")
                      for entry in entries if entry.status == owners.ASK]
            pause = 2
            while wanted:
                # 🔴 Watched, not waited on: a cancel or the staging limit stops it.
                pool = ThreadPoolExecutor(max_workers=4)
                each = max(1, int(min(timeout, self._staging_left(job_id))))
                tried = {key: pool.submit(self._fetch, key[0], key[1], each)
                         for key in wanted}
                while not all(future.done() for future in tried.values()):
                    futures_wait(list(tried.values()), timeout=1)
                    if self._row(job_id)["state"] != "staging":
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise _NoLongerStaging(job_id)
                    if self._staging_left(job_id) <= 0:
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise _StagingTimedOut("fetching sources")
                pool.shutdown(wait=False)
                last = {}
                for key, future in tried.items():
                    try:
                        future.result()
                        record.note(root, [f"fetched {key[0]} at {key[1]}"])
                        wanted.pop(key)
                    except Permanent as e:
                        logger.info(f"{job_id}: a source cannot be fetched: {e}")
                        record.note(root, [f"could not fetch {key[0]} at {key[1]}: {e}"])
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
                    self._check_staging_time(job_id, "fetching sources")
                    time.sleep(pause)
                    pause = min(pause * 2, 60)
                    if self._row(job_id)["state"] != "staging":
                        raise _NoLongerStaging(job_id)

            job = self._row(job_id)
            if job["state"] != "staging":
                raise _NoLongerStaging(job_id)

            # 🔴 A private dataroot is never asked for (surface D299): its failed
            # fetch rejects the job, as create would have.
            private = [(entry, why) for entry, why in failed
                       if entry.origin == owners.PRIVATE]
            if private:
                entry, why = private[0]
                raise self._refuse_staging(job, ProblemError(
                    "resource-unavailable", resource=owners.keypath_owner(entry.keypath),
                    keypath=list(entry.keypath),
                    detail=f"the private dataroot {owners.shown(entry.keypath)} is not "
                           f"held by this server, and its fetch failed: {why}"))
            if failed:
                self._send_back(job, failed)
                return

            # Everything in hand: a file missing from a fetched copy is refused.
            entries = self._account(job, summary, unpacked)

            # Each node the run reads and does not run (surface D175).
            copies = self._account_upstream(job, summary, unpacked)
            if copies:
                self._phase(job_id, "copying earlier results")
            self._copy_results(job, unpacked, copies)
            self._check_staging_time(job_id, "copying earlier results")

            # The job's Python packages: installed on this host, or built over
            # the resolved images with containers. A package no index has sends
            # the job back for its wheel.
            absent = self._install_on_host(job, summary)
            plan = None
            if not absent:
                plan, absent = self._build_environments(
                    job, summary, self._resolve_images(job, summary))
            if self._row(job_id)["state"] != "staging":
                raise _NoLongerStaging(job_id)
            if absent:
                self._send_back(self._row(job_id), [], python=absent)
                return
            self._check_staging_time(job_id, "resolving the job's images")

            # `queued` only once the scheduler holds it.
            self._phase(job_id, "handing the job to the scheduler")
            self._dispatch(self._row(job_id), summary, entries, plan=plan)
            record.note(root, ["handed the job to the scheduler"])
        except ProblemError:
            # Already recorded on the job by `_refuse`.
            pass
        except _NoLongerStaging:
            # Cancelled while it staged: its `cancelled` is written here.
            job = self._row(job_id)
            if not job["scheduler_job_id"]:
                self._settle_cancelled(job)
        except _StagingTimedOut as e:
            self._time_out_staging(job_id, str(e))
        except _ServerFailure as e:
            self._fail_staging(job_id, str(e))
        except Exception as e:                                   # noqa: BLE001
            logger.exception(f"could not stage {job_id}")
            self._fail_staging(job_id, f"this server could not get the job ready: "
                                       f"{type(e).__name__}")
        finally:
            self._staging_deadlines.pop(job_id, None)
            with self._preparing_lock:
                self._preparing.discard(job_id)
            self._keep_staging_record(job_id)
            self._store.release()

    ######################################################################
    # The staging limit, and the record staging leaves (surface D294, D295)
    ######################################################################

    def _staging_limit(self, job) -> int:
        '''The caller's `max_staging_seconds`, as `GET /v1/me` publishes it.'''
        from siliconcompiler.remote.server.identity import accounts

        return int(accounts.effective_limits(
            self._store, self._config, job["user_id"])["max_staging_seconds"])

    def _staging_left(self, job_id: str) -> float:
        '''Seconds left of this pass of staging, or infinity outside a pass.'''
        import time

        deadline = self._staging_deadlines.get(job_id)
        return float("inf") if deadline is None else deadline - time.monotonic()

    def _check_staging_time(self, job_id: str, doing: str) -> None:
        '''Raise `_StagingTimedOut` where this pass has run out of time.'''
        if self._staging_left(job_id) <= 0:
            raise _StagingTimedOut(doing)

    def _time_out_staging(self, job_id: str, doing: str) -> None:
        '''The pass ran past `max_staging_seconds`: `failed`,
        `staging-timed-out`, naming what it was doing.'''
        job = self._row(job_id)
        if job["state"] == "cancelling" and not job["scheduler_job_id"]:
            self._settle_cancelled(job)
            return
        detail = (f"staging ran past this account's max_staging_seconds "
                  f"({self._staging_limit(job)}s) while {doing}")
        with self._store.transaction():
            job = self._row(job_id)
            if job["state"] != "staging":
                return
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = ?, finished_at = ? "
                "WHERE id = ?", (ERRORS["staging-timed-out"].uri,
                                 _members_json({"limit": "max_staging_seconds"}), now(),
                                 job_id))
            # Before the transition, which lists the record as it then stands.
            self._note(job, [f"timed out: {detail}"])
            self._transition(job_id, "staging", "failed", reason=_bounded(detail))
        logger.warning(f"{job_id}: {detail}")

    def _fail_staging(self, job_id: str, detail: str) -> None:
        '''This server's own failure while staging: `failed`, `staging-failed`.'''
        job = self._row(job_id)
        if job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while it failed: what the owner did stands.
            self._settle_cancelled(job)
            return
        with self._store.transaction():
            job = self._row(job_id)
            if job["state"] != "staging":
                return
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = NULL, finished_at = ? "
                "WHERE id = ?", (ERRORS["staging-failed"].uri, now(), job_id))
            # Before the transition, which lists the record as it then stands.
            self._note(job, [f"staging failed: {detail}"])
            self._transition(job_id, "staging", "failed", reason=_bounded(detail))
        logger.warning(f"{job_id}: staging failed: {detail}")

    def _note(self, job, lines) -> None:
        '''Lines of the job's `staging` record, each scrubbed like `detail`.'''
        record.note(self.job_root(job["user_id"], job["id"]), lines)

    def _keep_staging_record(self, job_id: str) -> None:
        '''Index the `staging` record as this pass leaves it, and the operators'
        record for a job that has ended.'''
        job = self._row(job_id)
        root = self.job_root(job["user_id"], job_id)
        try:
            with self._store.transaction():
                artifacts.collect_staging(self._store, self._storage, self._config, job,
                                          root)
                if job["state"] in TERMINAL_STATES:
                    artifacts.collect_diagnostics(self._store, self._storage,
                                                  self._config, job, root)
        except OSError as e:
            logger.warning(f"{job_id}: could not keep the staging record: {e}")

    def _fetch(self, source: str, ref: str, timeout: int) -> str:
        '''One source into this server's copy, or a permanent failure under
        `fetch_fails`.'''
        from siliconcompiler.remote.server.staging.sources import Permanent

        if self._config["fetch_fails"]:
            raise Permanent("this server fetches nothing (fetch_fails is set, as in "
                            "test mode 4)")
        return self._sources.fetch(source, ref, timeout)

    def _send_back(self, job, failed, python=()) -> None:
        '''`staging` back to `awaiting_input`, the one backwards edge (surface
        D130), asking for what failed and saying why for each.

        ``failed`` is ``(entry, why)`` for dataroots; ``python`` is
        ``(name, why)`` for packages the client answers with a wheel.

        ⚠️ The job counts against `pending_uploads` again, frees its
        `concurrent_jobs` slot, and its abandonment clock restarts.
        '''
        asked, reasons = [], []
        for entry, why in failed:
            if entry.wire not in asked:
                asked.append(entry.wire)
                reasons.append(f"the dataroot {owners.shown(entry.keypath)}: {why}")
        for name, why in python:
            wire = {"kind": "python", "name": name}
            if wire not in asked:
                asked.append(wire)
                reasons.append(f"the Python package {name}: {why}")
        reason = (f"{len(asked)} source(s) this server cannot supply, so the client "
                  "is asked to send them -- " + "; ".join(reasons))
        self._note(job, [f"sent back for {one}" for one in reasons])
        # 🔴 The wheel answering one replaces its entry, and alone may overlap.
        answered = sorted(set(json.loads(job["python_answered"] or "[]"))
                          | {name for name, _ in python})
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

        🔴 A job cancelled meanwhile stays `cancelled`, as its owner decided.
        '''
        current = self._row(job["id"])
        if current["state"] != "staging":
            raise _NoLongerStaging(job["id"])
        said = problem.members.get("reason")
        self._note(current, [f"refused: {problem.error.slug}"
                             + (f" ({said})" if said else "")
                             + (f": {problem.detail}" if problem.detail else "")])
        return self._refuse(current, problem)

    def _check_denied(self, job, summary) -> None:
        '''Refuse a run that uses a PDK, library or tool nobody may use.

        🔴 After the manifest's read and before image resolution: a denial is
        the answer that does not change when an image is added.

        ⚠️ The first found is named (one `resource`), the detail counting the
        rest. A lying summary can evade it, which widens nothing on this
        profile (contract §1, *The summary cannot widen access*).
        '''
        wanted = _resources(summary) + [("tool", name) for name in summary["tools"]]

        denied = [(kind, name) for kind, name in wanted
                  if self._config.denied(kind, name)]
        if not denied:
            return

        kind, name = denied[0]
        more = len(denied) - 1
        raise self._refuse(job, ProblemError(
            "entitlement-denied", resource_kind=kind, resource=name,
            detail=f"this flow uses a {kind} this deployment does not allow"
                   + (f", and {more} more" if more else "")))

    ######################################################################
    # The manifest's read (contract §1)
    ######################################################################

    def _read(self, job, root: Path) -> Dict[str, Any]:
        '''Read the uploaded manifest in a process of its own and act on what
        it says; returns :meth:`_summary`'s shape.

        🔴 Contract §1: `manifestread`, contained by `sandbox`, returns data
        that is validated here and stored. This, not the descriptor, is
        authoritative, which is why the checks run twice.
        '''
        unpacked = root / job["design"] / job["jobname"]
        if not (unpacked / f"{job['design']}.pkg.json").is_file():
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="missing_manifest",
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
            # 🔴 Out of the staging limit, not the read's own: `staging-timed-out`.
            if e.timed_out and self._staging_left(job["id"]) <= 1:
                raise _StagingTimedOut("reading the manifest") from None
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="invalid_manifest",
                detail=_bounded(f"the manifest has not been read: {e}"))) from None
        except OSError as e:
            raise _ServerFailure(f"this server could not start the manifest's read: "
                                 f"{e}") from None

        try:
            raw = manifestread.validate(raw)
        except manifestread.Invalid as e:
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="invalid_manifest",
                detail=_bounded(f"the manifest's read returned a summary this server "
                                f"cannot use: {e}"))) from None

        contained = raw.get("contained") or {}
        logger.info(f"{job['id']}: read its manifest in {raw.get('seconds')}s"
                    + ("" if contained.get("network") else ", with no network namespace")
                    + ("" if contained.get("limits") else ", with no resource limits"))
        nodes = raw.get("nodes") or []
        self._note(job, [
            f"read the manifest in {raw.get('seconds')}s: flow {raw.get('flow')}, "
            f"{len(nodes)} node(s), PDK {raw.get('pdk') or 'none'}"
            + (f", tools {', '.join(sorted({n['tool'] for n in nodes if n.get('tool')}))}"
               if any(n.get("tool") for n in nodes) else "")
            + (f"; it found {raw['outcome'].get('type', 'a refusal')}"
               if isinstance(raw.get("outcome"), dict) else "")])

        # 🔴 Above the upload's tree, so no upload can write it.
        runspec.write_json(root / runspec.SUMMARY_FILENAME, raw)
        try:
            return self._act_on(job, raw)
        except BaseException:
            if raw.get("credentials"):
                # 🔴 The extracted tree is a second copy of a credential.
                shutil.rmtree(root, ignore_errors=True)
            raise

    def _run_read(self, job, root: Path, asked) -> Any:
        '''The read: in the job's own image with containers, else on this host
        under this server's own SiliconCompiler (profile §5, D63).'''
        limits = dict(
            # Its own limit, or what is left of this pass of staging.
            timeout=max(1, min(self._config["manifest_read_timeout_seconds"],
                               self._staging_left(job["id"]))),
            alive=lambda: self._row(job["id"])["state"] == "staging",
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
                # 🔴 This server's failure, not the job's (database D145).
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
        '''The summary the job's last read stored, validated again, or a fresh
        read where none validates.'''
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

        # 🔴 Userinfo in a dataroot path (surface D302), named by keypath, never
        # value; before anything is fetched, and the upload is not kept (D307).
        found = raw.get("credentials") or []
        if found:
            named = ", ".join(owners.shown(keypath) for keypath in found)
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="credential", keypath=list(found[0]),
                detail=_bounded(
                    f"the manifest carries userinfo -- a user name, or a user name and "
                    f"a secret -- in the path of {len(found)} dataroot(s): {named}. A "
                    "client sends every dataroot's path without it, and this server "
                    "never uses one")))
        return self._summary(raw)

    @staticmethod
    def _summary(raw) -> Dict[str, Any]:
        '''A validated summary, as the checks read it; the tools are derived
        from the nodes, never the summary's own list.'''
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
            # Where the job's Python packages are installed.
            "python": [(entry["step"], entry["index"])
                       for entry in raw["nodes"] if entry["python"]],
            "tools": sorted({tool for tool in node_tools.values() if tool}),
            "pdk": raw["pdk"],
            "libraries": list(raw["libraries"]),
            "fpga": raw["fpga"],
            # What the flow reads (D129); None where the client could not say.
            "required": ({tuple(key) for key in raw["required"]}
                         if raw["required"] is not None else None),
            "upstream": [tuple(node) for node in raw["upstream"]],
            "values": raw["values"],
        }
