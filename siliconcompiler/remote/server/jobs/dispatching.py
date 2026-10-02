'''
Handing a staged job to the scheduler: its images resolved, the run file
written, and the submission recorded.

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json

from pathlib import Path
from typing import Dict, Optional

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    _NoLongerStaging, _ServerFailure, logger, requirements)
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.running.dispatch import DispatchError
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import now


class DispatchMixin:
    '''Handing a staged job to the scheduler.'''

    def _dispatch(self, job, summary, entries, plan=None) -> None:
        '''Resolve images, write the manifest the run will load, and hand
        the job to the scheduler. ``plan`` is the images already resolved
        while staging, with any the job's Python packages were built into.'''
        root = self.job_root(job["user_id"], job["id"])
        if plan is None:
            plan = self._resolve_images(job, summary)
        manifest = self._write_run(job, root, summary, plan, entries)

        try:
            bundle = self._framework_bundle(job, plan)
        except ProblemError as problem:
            raise self._refuse(job, problem) from None

        try:
            # The job's own root, so the batch script and the run's stdout land
            # beside what the run produced and go away with it when the job is
            # deleted.
            scheduler_job_id = self._dispatcher.submit(
                job["id"], root, manifest, image=bundle,
                queue=self._config["batch_queue"])
        except DispatchError as e:
            raise _ServerFailure(f"this server's scheduler refused the job: {e}") from None

        if not self._record_submission(job, summary, scheduler_job_id, plan):
            # Cancelled while it was handed over: the scheduler lets it go.
            self._dispatcher.cancel(scheduler_job_id)
            raise _NoLongerStaging(job["id"])
        logger.info(f"submitted {job['id']} as {scheduler_job_id}")

    def _resolve_images(self, job, summary):
        '''Which container every node of this job runs in.

        🔴 Before the dispatcher is called and after the archive is open, which
        is the only place both facts are in hand: the flow's real node list
        comes from the manifest, and nothing may be handed to the cluster that
        this server cannot place. A node whose tool this deployment tracks and
        has no image for fails the WHOLE submit here, rather than queueing and
        dying on node thirty-one with the cluster already paid for.

        ⚠️ Skipped entirely where the deployment runs no containers, and that
        answer is NULL rather than a default image -- `job_nodes.image_id` is
        *what that node actually ran in*, so writing one for a node that ran on
        the host would be a record of something that did not happen.
        '''
        if not self._config["containers"]:
            return images.Plan(None, {node: None for node in summary["nodes"]}, {})

        requires = requirements(json.loads(job["descriptor"]) or {})

        try:
            plan = images.plan_for_job(self._store, requires,
                                       summary["node_tools"], summary["inherits"],
                                       job_image_id=job["image_id"],
                                       python_nodes=summary["python"])
        except ProblemError as problem:
            # Its own slug, not a guessed one: `plan_for_job` refuses for more
            # than one reason and the job must record the one the caller was
            # given.
            raise self._refuse(job, problem) from None
        # Each image the job's nodes run in, in its `staging` record.
        placed: Dict[str, list] = {}
        for (step, index), image_id in sorted(plan.nodes.items()):
            if image_id in plan.refs:
                placed.setdefault(plan.refs[image_id], []).append(f"{step}/{index}")
        self._note(job, [f"{', '.join(nodes)} run(s) in {ref}"
                         for ref, nodes in sorted(placed.items())])
        return plan

    def _framework_bundle(self, job, plan) -> Optional[str]:
        '''The container the job's own orchestrating process runs in.

        🔴 This is what makes version matching real rather than half-done. The
        per-node images decide what each TOOL runs in; this decides what
        interprets the manifest -- and without it a job asking for
        SiliconCompiler 0.39 has its flow driven by whatever version the cluster
        installed, which is the question version-matched-images.md calls the
        real one.

        Staged here rather than on the compute node, because `sbatch
        --container` names a bundle that has to exist before the job starts and
        there is nothing running yet to unpack it. It is a no-op once staged, so
        the cost falls on the first submit after an operator registers an image
        -- and `registry add-image -stage` is how an operator keeps it off the
        request path entirely.
        '''
        if self._dispatcher.name != "slurm" or not plan.job:
            return None

        ref = plan.refs.get(plan.job)
        if not ref:
            return None

        try:
            common = images.stage_bundle(self.bundles_root(), ref, ref.split("@", 1)[1],
                                         mounts=self.container_mounts())
            self._note(job, [f"unpacked {ref} for the job's own process"])
            # This job's own view of it, beside its nodes' bundles.
            return str(images.job_bundle(
                common, self.job_bundles(job["id"]) / Path(common).name,
                self.framework_mounts(job)))
        except Exception as e:                                   # noqa: BLE001
            # Refused rather than dispatched without it. Dropping the image
            # silently would run the job against whatever SiliconCompiler this
            # cluster has, which is the thing the registry exists to stop --
            # and it would do it while the record said otherwise.
            raise _ServerFailure(f"this server could not unpack the image the job's "
                                 f"own process runs in: {e}") from None

    def _record_submission(self, job, summary, scheduler_job_id, plan) -> bool:
        '''`staging` to `queued`, now the scheduler holds it; False where the
        job left `staging` meanwhile, and stays as it is.'''
        with self._store.transaction():
            if self._row(job["id"])["state"] != "staging":
                return False
            self._store.execute(
                "UPDATE jobs SET manifest_flow = ?, manifest_node_count = ?, "
                "  manifest_tools = ?, manifest_pdk = ?, "
                "  scheduler_job_id = ?, image_id = ?, submitted_at = ? "
                "WHERE id = ?",
                (summary["flow"], len(summary["nodes"]),
                 json.dumps(summary["tools"]), summary["pdk"],
                 scheduler_job_id, plan.job, now(), job["id"]))
            self._transition(job["id"], "staging", "queued")

            for step, index in summary["nodes"]:
                self._store.execute(
                    'INSERT INTO job_nodes (job_id, step, "index", state, image_id) '
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (job["id"], step, index, plan.nodes.get((step, index))))
            for from_step, from_index, to_step, to_index in summary["edges"]:
                self._store.execute(
                    "INSERT INTO job_node_edges "
                    "(job_id, from_step, from_index, to_step, to_index) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (job["id"], from_step, from_index, to_step, to_index))
        return True

    def _write_run(self, job, root: Path, summary, plan, entries=()) -> Path:
        '''What the run needs from this server, as data beside the manifest;
        the manifest the run loads, which is the one uploaded.

        🔴 **Nothing here rewrites the manifest.** The runner loads it, in the
        job's own SiliconCompiler, and applies these overrides there
        (`runspec.apply_run`): the job id, the build and cache directories,
        each node's placement, the cluster, and where each dataroot is
        supplied. The list itself is `runspec.normalize`, the file both ends
        read.
        '''
        cache = self.cache_dir(job["user_id"])
        cache.mkdir(parents=True, exist_ok=True)

        # Where each node's image reaches it depends on what is scheduling: a
        # Slurm step names an unpacked bundle, and the docker scheduler pulls a
        # digest. The dispatcher is the only thing that knows which.
        placements = plan.placements()
        sources = {}

        shared = {}
        if self._dispatcher.name == "slurm":
            refs = placements
            placements = {}
            for node, ref in refs.items():
                # 🔴 The job's own bundle over the shared one: what a node sees
                # is its job's, never the data directory.
                common = images.bundle_path(self.bundles_root(), ref.split("@", 1)[1])
                bundle = str(self.job_bundles(job["id"]) / common.name)
                placements[node] = bundle
                sources[bundle] = ref
                shared[bundle] = str(common)

        # 🔴 Every dataroot points at the copy the run will actually read --
        # this job's upload, or this server's own supplied copy -- so the
        # manifest the run writes records which, and no dataroot is left
        # naming a path on the submitter's machine (D111, D112).
        unpacked = root / job["design"] / job["jobname"]
        runspec.write_run(
            root / runspec.RUN_FILENAME, job_id=job["id"], builddir=root, cachedir=cache,
            cluster=self._dispatcher.name, placements=placements,
            dataroots=runspec.dataroot_targets(entries, unpacked / "sc_collected_files",
                                               uploads=root / runspec.UPLOADS_DIRNAME),
            track=self._config["track_provenance"])

        # Only the bundles need a source: a digest the docker scheduler pulls
        # already says where it comes from.
        runspec.write_images(
            root / runspec.IMAGES_FILENAME,
            sources, self.container_mounts() if sources else [],
            shared=shared,
            job_mounts=self.job_mounts(job) if sources else [])

        return unpacked / f"{job['design']}.pkg.json"
