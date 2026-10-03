'''
Handing a staged job to the scheduler: its images resolved, the run file
written, and the submission recorded.
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
        '''Resolve images, write the run file, and hand the job to the
        scheduler. ``plan`` is any image plan staging already resolved.'''
        root = self.job_root(job["user_id"], job["id"])
        if plan is None:
            plan = self._resolve_images(job, summary)
        manifest = self._write_run(job, root, summary, plan, entries)

        try:
            bundle = self._framework_bundle(job, plan)
        except ProblemError as problem:
            raise self._refuse(job, problem) from None

        try:
            # The job's own root, so the batch script and stdout go with the job.
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

        🔴 After the manifest's read gives the real node list and before
        dispatch: a tracked tool with no image fails the WHOLE job here, not on
        node thirty-one with the cluster already paid for.

        ⚠️ Without containers every node is NULL, never a default image:
        `job_nodes.image_id` records what the node actually ran in.
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
            # The refusal's own slug: `plan_for_job` refuses for several reasons.
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

        🔴 Node images decide what each TOOL runs in; this decides which
        SiliconCompiler drives the flow, or the cluster's own would.

        Staged here, since `sbatch --container` needs the bundle before the job
        starts; `registry add-image -stage` keeps it off the request path.
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
            # Refused rather than run on the cluster's SiliconCompiler while the
            # record says otherwise.
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
        '''Write what the run needs from this server beside the manifest, and
        return the uploaded manifest the run loads.

        🔴 Nothing here rewrites the manifest: the runner applies these
        overrides in the job's own SiliconCompiler (`runspec.apply_run`).
        '''
        cache = self.cache_dir(job["user_id"])
        cache.mkdir(parents=True, exist_ok=True)

        # A Slurm step names an unpacked bundle; the docker scheduler pulls a
        # digest.
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

        # 🔴 Every dataroot points at the copy the run reads, the upload or a
        # supplied copy, never the submitter's path (D111, D112).
        unpacked = root / job["design"] / job["jobname"]
        runspec.write_run(
            root / runspec.RUN_FILENAME, job_id=job["id"], builddir=root, cachedir=cache,
            cluster=self._dispatcher.name, placements=placements,
            dataroots=runspec.dataroot_targets(entries, unpacked / "sc_collected_files",
                                               uploads=root / runspec.UPLOADS_DIRNAME),
            track=self._config["track_provenance"])

        # Only the bundles need a source; a pulled digest says where it is from.
        runspec.write_images(
            root / runspec.IMAGES_FILENAME,
            sources, self.container_mounts() if sources else [],
            shared=shared,
            job_mounts=self.job_mounts(job) if sources else [])

        return unpacked / f"{job['design']}.pkg.json"
