'''
A run that starts part-way through its flow: each node it reads and does not
run, from the archive or the job that ran it (surface D175).

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import gzip
import json
import os
import shutil

from pathlib import Path
from typing import List, Set, Tuple

from siliconcompiler.remote import runflow
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    _ServerFailure, _extract_outputs, _link_home, logger)
from siliconcompiler.remote.server.staging import archive


class ContinuationsMixin:
    '''A run that starts part-way through its flow.'''

    ######################################################################
    # A run that starts part-way through its flow (surface D175)
    ######################################################################

    def _account_upstream(self, session, job, summary, unpacked: Path):
        '''Every node the run reads and does not run: in the archive, or
        copied from the job `continues_from` names -- and none in neither.
        Returns the nodes to copy, as ``((step, index), from_job)``.

        A node in both is taken from the archive, and an entry for a node the
        run does not read is not copied. What is copied is checked again, and
        so is what it was built from.
        '''
        continued = {(step, index): from_job
                     for step, index, from_job in self._continuations_of(job["id"])}
        copies = []
        for step, index in summary["upstream"]:
            if runflow.outputs_present(unpacked / step / index, job["design"]):
                continue
            if (step, index) not in continued:
                raise self._refuse(session, job, ProblemError(
                    "archive-rejected", reason="missing_member",
                    detail=f"the run reads the results of {step}/{index}, which it does "
                           "not run, and they are neither in the archive nor named in "
                           "continues_from"))
            copies.append(((step, index), continued[(step, index)]))
        try:
            self._check_continuations(
                job["user_id"], [(step, index, from_job) for (step, index), from_job in copies])
        except ProblemError as problem:
            raise self._refuse(session, job, problem) from None
        return copies

    def _copy_results(self, job, unpacked: Path, copies) -> None:
        '''Each node's outputs and manifest from the job that ran it, into
        ``<step>/<index>/outputs/`` -- where uploaded results land, so the run
        needs no change. The copied node gets no row and no artifacts here.

        🔴 **The archive is read as untrusted**, like every read of a job's
        tree: an upload's rules (`archive.extract`), links included, and only
        under ``outputs/``. A link to a passed-through file's home is then
        resolved from the earlier job's own archives (:meth:`_resolve_links`),
        and no bytes pass to or from the user.
        '''
        for (step, index), from_job in copies:
            held = {row["kind"]: row for row in self._store.all(
                'SELECT kind, storage_key, withheld_at FROM artifacts WHERE job_id = ? '
                "AND step = ? AND \"index\" = ? AND kind IN ('node', 'manifest') "
                "AND deleted_at IS NULL", (from_job, step, index))}
            withheld = [kind for kind, row in held.items() if row["withheld_at"]]
            if withheld:
                raise self._refuse_staging(job, ProblemError(
                    "prior-results-unavailable", step=step, index=index,
                    job_id=from_job, reason="withheld",
                    detail=f"the {withheld[0]} artifact of {step}/{index} in job "
                           f"{from_job} was withheld before it could be copied"))
            target = unpacked / step / index
            try:
                _extract_outputs(self._storage.artifact_path(held["node"]["storage_key"]),
                                 unpacked, step, index, self._config.limits)
                with gzip.open(self._storage.artifact_path(
                        held["manifest"]["storage_key"])) as source, \
                        open(target / "outputs" / f"{job['design']}.pkg.json", "wb") as out:
                    shutil.copyfileobj(source, out)
            except (KeyError, FileNotFoundError):
                raise self._refuse_staging(job, ProblemError(
                    "prior-results-unavailable", step=step, index=index, job_id=from_job,
                    reason="expired",
                    detail=f"the results of {step}/{index} in job {from_job} went before "
                           "they could be copied")) from None
            except archive.ArchiveRejected as e:
                raise _ServerFailure(f"the results of {step}/{index} in job {from_job} "
                                     f"could not be copied: {e.detail}") from None
            except OSError as e:
                raise _ServerFailure(f"this server's store did not answer the copy of "
                                     f"{step}/{index} from job {from_job}: {e}") from None
            logger.info(f"{job['id']}: copied {step}/{index} from {from_job}")

        in_place = {node for node, _ in copies} | {
            node for node in self._upstream_uploaded(job, unpacked)}
        for (step, index), from_job in copies:
            self._resolve_links(job, unpacked, (step, index), from_job, in_place)

    # How many earlier jobs a passed-through file's home is looked for through.
    CONTINUATION_DEPTH = 8

    def _upstream_uploaded(self, job, unpacked: Path):
        '''The nodes whose outputs arrived in the upload.'''
        for top in sorted(unpacked.iterdir()):
            if not top.is_dir() or top.is_symlink():
                continue
            for node in sorted(top.iterdir()):
                if (node / "outputs").is_dir() and not (node / "outputs").is_symlink() \
                        and runflow.outputs_present(node, job["design"]):
                    yield (top.name, node.name)

    def _resolve_links(self, job, unpacked: Path, node, from_job: str, in_place) -> None:
        '''Every link in a copied node's ``outputs/`` to a file whose home is
        not in place in this job's tree: the file itself, from the home node's
        archive in the earlier job (surface *Passed-through files are resolved
        while staging*).

        Where the home is copied or uploaded, the link stays. Where the earlier
        job itself took the home from another job, it has no archive of it:
        its continuations are followed to the job that ran it.
        '''
        outputs = unpacked / node[0] / node[1] / "outputs"
        for dirpath, dirnames, filenames in os.walk(outputs, followlinks=False):
            for name in sorted(dirnames + filenames):
                path = Path(dirpath) / name
                if not path.is_symlink():
                    continue
                home = _link_home(unpacked, path)
                if home is None or home[0] == node or home[0] in in_place:
                    continue
                self._place_from_home(job, path, home, from_job, depth=0)

    def _place_from_home(self, job, path: Path, home, from_job: str, depth: int) -> None:
        '''The file ``home`` names, from its node's archive in ``from_job``
        -- or through ``from_job``'s own continuations -- at ``path``, in
        place of the link.'''
        (step, index), member = home
        if depth > self.CONTINUATION_DEPTH:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="expired",
                detail=f"{step}/{index}'s results, which a copied node links to, are "
                       f"more than {self.CONTINUATION_DEPTH} jobs back"))

        row = self._store.one(
            'SELECT storage_key, withheld_at, deleted_at FROM artifacts WHERE job_id = ? '
            "AND step = ? AND \"index\" = ? AND kind = 'node'", (from_job, step, index))
        if row is None:
            earlier = self._store.one(
                'SELECT from_job_id FROM job_continuations WHERE job_id = ? AND step = ? '
                'AND "index" = ?', (from_job, step, index))
            if earlier is not None:
                return self._place_from_home(job, path, home, earlier["from_job_id"],
                                             depth + 1)
        if row is None or row["deleted_at"]:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="expired",
                detail=f"the node artifact of {step}/{index} in job {from_job}, the home "
                       "of a file a copied node links to, is gone"))
        if row["withheld_at"]:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="withheld",
                detail=f"the node artifact of {step}/{index} in job {from_job}, the home "
                       "of a file a copied node links to, is withheld"))

        import tempfile
        try:
            with tempfile.TemporaryDirectory(dir=str(path.parent)) as scratch:
                scratch = Path(scratch)
                _extract_outputs(self._storage.artifact_path(row["storage_key"]),
                                 scratch, step, index, self._config.limits,
                                 only=member)
                found = scratch / step / index / member
                if found.is_symlink():
                    # The home's own pass-through: its home, in turn.
                    onward = _link_home(scratch, found)
                    if onward is None:
                        raise _ServerFailure(f"a link in {step}/{index} of job "
                                             f"{from_job} leads nowhere")
                    path.unlink()
                    return self._place_from_home(job, path, onward, from_job, depth + 1)
                if not found.exists():
                    raise self._refuse_staging(job, ProblemError(
                        "prior-results-unavailable", step=step, index=index,
                        job_id=from_job, reason="expired",
                        detail=f"{member} is not in the node artifact of {step}/{index} "
                               f"in job {from_job}"))
                path.unlink()
                os.replace(found, path)
        except archive.ArchiveRejected as e:
            raise _ServerFailure(f"the results of {step}/{index} in job {from_job} could "
                                 f"not be read: {e.detail}") from None
        except OSError as e:
            raise _ServerFailure(f"this server's store did not answer for {step}/{index} "
                                 f"of job {from_job}: {e}") from None

    def _skipped_upstream(self, job) -> Set[Tuple[str, str]]:
        '''The nodes skipped in the jobs this one continues from, by those jobs'
        own recorded states -- never the upload's say-so.'''
        return {(row["step"], row["index"]) for row in self._store.all(
            'SELECT n.step, n."index" FROM job_nodes n JOIN job_continuations c '
            "ON n.job_id = c.from_job_id WHERE c.job_id = ? AND n.state = 'skipped'",
            (job["id"],))}

    def _continuations_of(self, job_id: str) -> List[Tuple[str, str, str]]:
        return [(row["step"], row["index"], row["from_job_id"]) for row in self._store.all(
            'SELECT step, "index", from_job_id FROM job_continuations WHERE job_id = ? '
            'ORDER BY step, "index"', (job_id,))]

    def _check_continuations(self, user_id: str, continuations) -> None:
        '''Every entry's results are usable, and none was built from something
        nobody here may use -- at create before the upload, and again at
        submit.'''
        for step, index, from_job in continuations:
            refused = self._continuation_refused(user_id, step, index, from_job)
            if refused:
                reason, detail = refused
                raise ProblemError("prior-results-unavailable", step=step, index=index,
                                   job_id=from_job, reason=reason, detail=detail)

        # 🔴 The job's resource set includes what it copies: without this a
        # job could name a PDK the caller may use and continue from results
        # built on one they may not. This profile's gate is `denied_resources`.
        for step, index, from_job in continuations:
            for kind, name in self._resources_of(from_job):
                if self._config.denied(kind, name):
                    raise ProblemError(
                        "entitlement-denied", resource_kind=kind, resource=name,
                        detail=f"the results of {step}/{index} this job would continue "
                               f"from were built from a {kind} this deployment does not "
                               "allow")

    def _continuation_refused(self, user_id, step, index, from_job):
        '''Why one entry's results cannot be used, as (reason, detail), or None.'''
        row = self._store.one("SELECT deleted_at FROM jobs "
                              "WHERE id = ? AND user_id = ?", (from_job, user_id))
        where = f"{step}/{index} of job {from_job}"
        if row is None:
            # 🔴 One answer for none and for somebody else's: it confirms nothing.
            return "not_found", f"no job of yours has that id, for {step}/{index}"
        if row["deleted_at"]:
            return "deleted", f"job {from_job} is deleted"
        # An archived job may be continued from: `archived` is never raised.
        node = self._store.one('SELECT state FROM job_nodes WHERE job_id = ? AND step = ? '
                               'AND "index" = ?', (from_job, step, index))
        if node is not None and node["state"] == "skipped":
            # Nothing to copy: the run looks through it to what fed it.
            return None
        if node is None or node["state"] != "completed":
            return "not_completed", (f"job {from_job} did not complete {step}/{index}: a job "
                                     "that only copied a node in did not run it")
        held = {row["kind"]: row for row in self._store.all(
            'SELECT kind, deleted_at, withheld_at FROM artifacts WHERE job_id = ? '
            "AND step = ? AND \"index\" = ? AND kind IN ('node', 'manifest')",
            (from_job, step, index))}
        # On this profile the artifact holding a node's outputs is its `node`
        # archive: it keeps no `outputs` kind.
        for kind in ("node", "manifest"):
            if kind not in held or held[kind]["deleted_at"]:
                return "expired", f"the {kind} artifact of {where} is gone"
        for kind in ("node", "manifest"):
            if held[kind]["withheld_at"]:
                return "withheld", f"the {kind} artifact of {where} is withheld"
        return None

    def _resources_of(self, job_id: str) -> List[Tuple[str, str]]:
        '''What one job's results were built from: its PDK and libraries as
        its manifest's read found them, and its tools.'''
        row = self._store.one("SELECT manifest_resources, manifest_pdk, manifest_tools "
                              "FROM jobs WHERE id = ?", (job_id,))
        if row is None:
            return []
        found = [tuple(pair) for pair in json.loads(row["manifest_resources"] or "[]")]
        if not found and row["manifest_pdk"] and row["manifest_pdk"] != "none":
            found.append(("pdk", row["manifest_pdk"]))
        found += [("tool", name) for name in json.loads(row["manifest_tools"] or "[]")]
        return found
