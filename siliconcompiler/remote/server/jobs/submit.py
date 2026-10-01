'''
The upload: its grant, the submit that checks the digest before anything is
opened, and the archive checked against the manifest's read (surface §14, §15).

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json
import os
import shutil

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote import environment, owners
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    _RESOURCE_KINDS, _SHA256, _bounded, _epoch, _expired_key, _from_epoch, _only,
    _python_names, _resources, _same_version, logger)
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.staging import archive
from siliconcompiler.remote.server.state.storage import grant_seconds
from siliconcompiler.remote.server.state.store import now


class SubmitMixin:
    '''The upload.'''

    ######################################################################
    # 14. upload-grant
    ######################################################################

    def grant(self, session, job_id: str, url_root: str,
              body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        '''Endpoint 14: a grant for the archive about to be uploaded.

        🔴 **`size_bytes` and `digest` are REQUIRED, and the first grant for
        each archive fixes both** (D125); a re-issue must repeat them. Submit
        runs only bytes matching the bound digest, so nothing written to the
        upload location afterwards changes what runs. `max_upload_bytes`
        bounds a job's archives together.
        '''
        job = self.owned(session, job_id)

        if job["state"] not in ("created", "awaiting_input"):
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} takes no upload")

        body = body if isinstance(body, dict) else {}
        _only(body, ("size_bytes", "digest"), "the grant request")
        size = body.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ProblemError("invalid-request",
                               detail="size_bytes is required: the size of the archive "
                                      "to upload")
        digest = body.get("digest")
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise ProblemError("invalid-request",
                               detail="digest is required and is 'sha256:<hex>'")

        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}")

        if job["grant_bytes"] is not None and (
                job["grant_bytes"] != size or job["grant_digest"] != digest):
            # A re-issue cannot widen -- or narrow -- what the first grant bound.
            raise ProblemError(
                "job-state-conflict",
                detail="this archive's first grant fixed its size and digest; a "
                       "re-issue must repeat both")

        expires = int(_epoch()) + grant_seconds(self._config.limits["max_upload_bytes"])
        signature = self._storage.sign_upload(job["id"], size, expires)
        ceiling = size

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_storage_key = ?, upload_location_id = ?, grant_bytes = ?, "
                "  grant_digest = ?, upload_grant_expires_at = ?, upload_revoked_at = NULL "
                "WHERE id = ?",
                (job["id"], self._config["storage_location_id"], size, digest,
                 _from_epoch(expires), job["id"]))
            if job["state"] == "created":
                self._transition(job["id"], "created", "awaiting_input",
                                 actor=session.user_id)

        url = (f"{url_root.rstrip('/')}/storage/upload/{job['id']}"
               f"?max_bytes={ceiling}&expires={expires}&sig={signature}")

        return {
            "method": "PUT",
            "url": url,
            # The size the first grant of this archive fixed, and the
            # signature carries the same number, so a re-issue cannot widen it.
            # What the bytes actually are is settled by the digest at submit.
            "headers": {"content-length": str(ceiling)},
            "expires_at": _from_epoch(expires),
        }

    ######################################################################
    # 15. submit
    ######################################################################

    def submit(self, session, job_id: str, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Dict[str, Any]:
        '''Endpoint 15: `202` in `staging`, once the upload matches the digest.

        🔴 **Nothing here opens the archive** (surface §15). It is kept, the job
        stages, and extraction, the manifest's read and every check run there. A
        refusal of the request itself -- the digest, the job's state,
        `concurrent_jobs` -- leaves the job `awaiting_input` with its upload
        where the grant put it, so the client may submit again.
        '''
        with self._keyed(session.user_id, "submit", idempotency_key):
            return self._submit(session, job_id, body, idempotency_key)

    def _submit(self, session, job_id, body, idempotency_key):
        job = self.owned(session, job_id)

        if idempotency_key is not None and job["submit_idempotency_key"] == idempotency_key \
                and not _expired_key(job["submit_key_at"]):
            # The original answer, whatever the job has done since.
            return json.loads(job["submit_reply"]) if job["submit_reply"] else self.wire(job)

        if job["state"] != "awaiting_input":
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} cannot be submitted")

        # 🔴 No body (surface §15; D277): the grant bound the size and the
        # digest, storage enforced the size on the PUT, and the upload is
        # checked against the digest the grant bound. A body with a member is
        # refused under the strict rule, never ignored.
        _only(body if isinstance(body, dict) else {}, (), "the submit request")
        digest = job["grant_digest"]
        if not digest:
            raise ProblemError(
                "job-state-conflict",
                detail="no upload grant has been issued for this job; ask for one and "
                       "PUT to it")

        reported = self._storage.stat_upload(job["id"])
        if reported is None:
            raise ProblemError(
                "job-state-conflict",
                detail="no upload has arrived for this job; ask for a grant and PUT to it")
        size, reported_digest = reported

        # Only bytes matching the digest the grant bound are ever extracted, so
        # nothing written to the upload location after this changes what runs.
        if reported_digest != digest:
            raise ProblemError(
                "upload-digest-mismatch",
                detail=f"storage holds {size} bytes, {reported_digest}, and the grant "
                       f"bound {digest}")

        # Every archive of the job together (D125): a follow-up cannot carry
        # what the first was refused for being too large.
        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}")

        self._check_concurrent_jobs(session.user_id)

        if idempotency_key is not None:
            other = self._store.one(
                "SELECT id, submit_key_at FROM jobs WHERE user_id = ? "
                "AND submit_idempotency_key = ? AND id <> ?",
                (session.user_id, idempotency_key, job["id"]))
            if other is not None and not _expired_key(other["submit_key_at"]):
                raise ProblemError(
                    "idempotency-key-reuse",
                    detail="this Idempotency-Key was used to submit a different job")
            if other is not None:
                with self._store.transaction():
                    self._store.execute(
                        "UPDATE jobs SET submit_idempotency_key = NULL, submit_reply = NULL "
                        "WHERE id = ?", (other["id"],))

        # 🔴 Kept from here on, as its own `input`, whatever staging finds:
        # every upload the job took can be looked at afterwards -- a refused one
        # most of all (surface D133).
        def admit():
            # 🔴 `concurrent_jobs` counted again inside the transaction that
            # moves the job into `staging`, which is what it counts, and the
            # job's own state with it: two submits cannot both take the last
            # slot (`Store.admission`). Before anything is moved, so a refusal
            # leaves the upload where the grant put it.
            if self._row(job["id"])["state"] != "awaiting_input":
                raise ProblemError(
                    "job-state-conflict",
                    detail="this job was submitted or ended meanwhile")
            self._check_concurrent_jobs(session.user_id)
            artifacts.record_upload(
                self._store, self._storage, self._config, job,
                self._storage.upload_path(job["id"]), reported_digest, size)
            self._store.execute(
                "UPDATE jobs SET archives_bytes = archives_bytes + ?, grant_bytes = NULL, "
                "  grant_digest = NULL, upload_digest = ?, upload_size_bytes = ?, "
                "  unpack_pending = 1, submit_idempotency_key = ?, submit_key_at = ?, "
                "  submit_reply = NULL WHERE id = ?",
                (size, digest, size, idempotency_key,
                 now() if idempotency_key is not None else None, job["id"]))
            self._transition(job["id"], "awaiting_input", "staging",
                             actor=session.user_id, state_reason="unpacking the upload")

        self._store.admission(admit)
        # Only what is left of it: an interrupted PUT's partial file.
        self._storage.discard_upload(job["id"])

        reply = self.wire(self._row(job["id"]))
        if idempotency_key is not None:
            with self._store.transaction():
                self._store.execute("UPDATE jobs SET submit_reply = ? WHERE id = ?",
                                    (json.dumps(reply), job["id"]))
        self._start_preparing(job["id"])
        return reply

    def _unpack(self, job):
        '''Staging's first phase: the newest upload extracted, the manifest
        read again over every archive, and every check re-run against the read.
        Returns ``(summary, entries)``.'''
        root = self.job_root(job["user_id"], job["id"])

        # The archive is the contents of one job directory, so it expands at
        # `<build root>/<design>/<jobname>/` -- where SiliconCompiler will look
        # for it once `option,builddir` is the job root. Both segments are the
        # DECLARED names, checked at create; the manifest's own copies are
        # checked against them, so an archive cannot name its way into another
        # job's tree.
        unpacked = root / job["design"] / job["jobname"]
        latest = self._store.one(
            "SELECT storage_key, upload_seq FROM artifacts WHERE job_id = ? "
            "AND kind = 'input' ORDER BY upload_seq DESC LIMIT 1", (job["id"],))
        follow_up = latest["upload_seq"] > 1

        # 🔴 A follow-up archive may hold only the dataroots that were asked
        # for (D124), so it cannot replace what the first archive carried after
        # the server checked it -- decided from the last read, before this
        # archive is opened.
        allowed = self._requested_members(job, root) if follow_up else None
        tally: Dict[str, Any] = {}
        try:
            archive.extract(self._storage.artifact_path(latest["storage_key"]),
                            unpacked, self._config.limits, allowed=allowed, tally=tally)
        except archive.ArchiveRejected as rejected:
            if not follow_up:
                shutil.rmtree(root, ignore_errors=True)
            # Kept, and never opened again: see `artifacts.UNOPENED`.
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason=rejected.reason,
                detail=rejected.detail)) from None

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET unpack_pending = 0, upload_sources = NULL WHERE id = ?",
                (job["id"],))
        self._phase(job["id"], "checking the manifest")
        job = self._row(job["id"])

        # Read again over the union of every archive, never from `sources`.
        summary = self._read(job, root)
        if not follow_up:
            self._check_members(job, summary, unpacked)
        self._check_wheels(None, job, unpacked, tally)
        self._check_denied(None, job, summary)
        entries = self._account(None, job, summary, unpacked)
        asked = [entry for entry in entries if entry.status == owners.ASK]
        self._check_owed(None, job, summary, asked)

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET manifest_pdk = ?, manifest_resources = ? WHERE id = ?",
                (summary["pdk"], json.dumps([list(pair) for pair in _resources(summary)]),
                 job["id"]))
        return summary, entries

    def _check_members(self, job, summary, unpacked: Path) -> None:
        '''🔴 The first archive holds only the manifest at its root,
        `sc_collected_files/` -- the job's wheels among it -- and
        `<step>/<index>/outputs/` for each node the run reads and does not
        run; anything else is `unrequested_member` (surface *What the archive
        carries, and who decides*).'''
        upstream = set(summary["upstream"])
        allowed = {f"{job['design']}.pkg.json", "sc_collected_files"}

        def refuse(member):
            return self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="unrequested_member",
                detail=f"{member} is not something a first archive carries: the "
                       "manifest, sc_collected_files/ and the outputs of each node "
                       "the run reads and does not run"))

        def real_dir(path):
            return path.is_dir() and not path.is_symlink()

        outputs = []
        for top in sorted(unpacked.iterdir()):
            if top.name in allowed:
                continue
            if not real_dir(top) or not any(step == top.name for step, _ in upstream):
                raise refuse(top.name)
            for node in sorted(top.iterdir()):
                if (top.name, node.name) not in upstream or not real_dir(node):
                    raise refuse(f"{top.name}/{node.name}")
                for member in sorted(node.iterdir()):
                    if member.name != "outputs" or not real_dir(member):
                        raise refuse(f"{top.name}/{node.name}/{member.name}")
                outputs.append(member)

        # 🔴 A link in an upstream node's `outputs/` points at a file's home in
        # another node's `outputs/` in this archive, or at its own node's: a
        # passed-through file, packed once (contract.md, *An upload keeps
        # links*). A link carries no bytes, so it counts as a member and not
        # toward the expanded size.
        homes = [os.path.realpath(str(path)) for path in outputs]
        for here in outputs:
            for dirpath, dirnames, filenames in os.walk(here, followlinks=False):
                for name in dirnames + filenames:
                    path = os.path.join(dirpath, name)
                    if not os.path.islink(path):
                        continue
                    real = os.path.realpath(path)
                    if not any(real == home or real.startswith(home + os.sep)
                               for home in homes):
                        raise self._refuse_staging(job, ProblemError(
                            "archive-rejected", reason="unrequested_member",
                            detail=f"{os.path.relpath(path, str(unpacked))} is a link "
                                   "outside the outputs of the nodes this archive "
                                   "carries"))

    ######################################################################
    # What a run's files are, and where the server's copies come from
    ######################################################################

    def _account(self, session, job, summary, unpacked: Path):
        '''Every file the manifest names, as how it reaches the run; refuse
        what nobody can supply.

        🔴 **No path the job names is read** (D112) -- see `owners.account`.
        `resource-unavailable` is raised only for what the caller could not
        send either (D127): a private dataroot this server has no copy of and
        cannot fetch, or a path that escapes the root it is supplied under.

        🔴 **A private value the archive carries is refused first**, not used
        (surface D299): `archive-rejected`, `unrequested_member`, its `detail`
        naming the dataroot and the member -- the first archive's rule, since it may not
        carry it, and the one a follow-up is held to already.
        '''
        collection = unpacked / "sc_collected_files"
        carried = owners.uploaded_private(summary["values"], collection)
        if carried:
            keypath, member = carried[0]
            more = len(carried) - 1
            raise self._refuse(session, job, ProblemError(
                "archive-rejected", reason="unrequested_member", keypath=list(keypath),
                detail=f"{member} is under the private dataroot {owners.shown(keypath)}, "
                       "which never leaves the submitter's machine: this server "
                       "supplies it itself" + (f", and {more} more" if more else "")))
        entries = owners.account_records(summary["values"], collection,
                                         self._supply, summary["required"])
        for entry in entries:
            if entry.status != owners.UNAVAILABLE:
                continue
            # `resource_kind` only where the read names a resource kind: never
            # the design, which is no resource (surface D285).
            kind = entry.kind if entry.kind in _RESOURCE_KINDS else None
            # A dataroot's refusal says which of its owner's (surface D298).
            where = f" in the dataroot {owners.shown(entry.keypath)}" \
                if entry.keypath else ""
            raise self._refuse(session, job, ProblemError(
                "resource-unavailable",
                resource=owners.keypath_owner(entry.keypath) if entry.keypath
                else entry.name or "",
                **({"keypath": list(entry.keypath)} if entry.keypath else {}),
                **({"resource_kind": kind} if kind else {}),
                detail=f"this flow needs {f'a {kind}' if kind else 'a file'}{where} "
                       f"this server cannot supply: {entry.why}"))
        for entry in entries:
            if entry.status == owners.UPLOADED:
                continue
            if entry.status == owners.SUPPLIED and entry.root:
                logger.info(f"{job['id']} is supplied "
                            f"{owners.shown(entry.keypath or (entry.name or '',))} "
                            "from this server")
        return entries

    def _check_wheels(self, session, job, unpacked: Path, tally=None) -> None:
        '''The job's wheels, under `sc_collected_files/python/`, every archive
        (surface *Uploaded wheels*): each pure and well formed, one per
        distribution, none for a distribution `python_packages` or
        `requested_versions.python` names -- but the one this job was sent back for,
        which replaces its listed entry -- and none at all where this
        deployment does not install a job's Python packages.

        `archive-rejected`, `reason: "python_package"`: the client builds every
        wheel, so each of these is a client bug.

        🔴 **A wheel's own members are held as any member is** (surface D292),
        and to the same limits, counted together with the archive's own: the
        ``tally`` its extraction filled, for each wheel this archive wrote.
        '''
        top = unpacked / environment.wheels_path()
        if not top.exists() and not top.is_symlink():
            return

        def refuse(detail):
            return self._refuse(session, job, ProblemError(
                "archive-rejected", reason="python_package", detail=_bounded(detail)))

        if "python.env" not in (self._config["features"] or ()):
            raise refuse(f"this job uploads {environment.wheels_path()}/, and this "
                         "deployment does not install a job's Python packages")
        if top.is_symlink() or not top.is_dir():
            raise refuse(f"{environment.wheels_path()} is not a directory of wheels")

        packages = environment.parse(json.loads(job["python_packages"])) \
            if job["python_packages"] else environment.Packages()
        listed = {environment.canonical(pin.name): pin.version
                  for pin in packages.requirements + packages.constraints}
        answered = set(json.loads(job["python_answered"] or "[]"))
        framework = {environment.canonical(name) for name in _python_names(job)}
        seen: Dict[str, str] = {}
        for path in sorted(top.iterdir()):
            name = f"{environment.wheels_path()}/{path.name}"
            if path.is_symlink() or not path.is_file():
                raise refuse(f"{name} is not a wheel file")
            try:
                wheel = environment.check_wheel(path)
            except environment.WheelError as e:
                raise refuse(f"{name}: {e}") from None
            if tally is not None and name in (tally.get("wheels") or ()):
                try:
                    archive.check_inside(tally, self._config.limits, name,
                                         wheel.members, wheel.expanded)
                except archive.ArchiveRejected as rejected:
                    raise self._refuse(session, job, ProblemError(
                        "archive-rejected", reason=rejected.reason,
                        detail=rejected.detail)) from None
            if wheel.name in seen:
                raise refuse(f"{seen[wheel.name]} and {path.name} are both wheels for "
                             f"{wheel.name}, and a job uploads one per distribution")
            seen[wheel.name] = path.name
            if wheel.name in framework:
                raise refuse(f"{name} is {wheel.name}, which the job's requested_versions.python "
                             "names: the image holds it, and it is never installed")
            if wheel.name in listed and wheel.name not in answered:
                raise refuse(f"{name} is {wheel.name}, which python_packages also lists: "
                             "a distribution travels as a wheel or in the lists, not both")
            if wheel.name in listed and not _same_version(wheel.version, listed[wheel.name]):
                # 🔴 The wheel the job was sent back for replaces its entry,
                # and so is at the entry's version (surface D286).
                raise refuse(f"{name} is {wheel.name} {wheel.version}, sent for an entry "
                             f"python_packages lists at {listed[wheel.name]}: the wheel "
                             "that answers an entry is at its version")

    def _check_owed(self, session, job, summary, asked) -> None:
        '''Refuse a required value the client should have sent and did not.

        🔴 **Before anything dispatches (D129)**, rather than a node failing
        on a missing file. *Should have sent* is the design, anything local or
        editable, and anything this job already asked for; the rest the server
        can still ask for. Only a flow whose set is known is checked: without it
        there is no telling a missing file from one nothing reads -- but a file
        in no dataroot is always the client's to have sent, since nothing names
        it to be asked for (surface D298).
        '''
        before = {tuple(item.get("keypath") or ())
                  for item in json.loads(job["upload_sources"] or "[]")
                  if item.get("kind") == "dataroot"}
        for entry in asked:
            if entry.keypath is not None and (
                    summary["required"] is None
                    or not (entry.kind == owners.DESIGN
                            or entry.origin in (owners.LOCAL, owners.EDITABLE)
                            or entry.keypath in before)):
                continue
            where = f" ({entry.dataroot})" if entry.dataroot else ""
            raise self._refuse(session, job, ProblemError(
                "archive-rejected", reason="missing_member",
                detail=f"the flow reads [{','.join(entry.key or ())}] of {entry.kind} "
                       f"{entry.name}{where}, {entry.path}, and the archive does "
                       "not carry it"))

    def _requested_members(self, job, root: Path):
        '''What a follow-up archive may hold: the collected files of the
        dataroots this job asked for that the flow reads, the wheel of each
        Python package it asked for, and nothing else -- a dataroot asked for
        selects its required values, never all of it.

        🔴 **Per value**, as the client collects it (`owners.collection`): a
        value asked for brings nothing else of its ``(key, step, index)``, so
        another value of that parameter is `unrequested_member`.'''
        entries = json.loads(job["upload_sources"] or "[]")
        # 🔴 By keypath: a member under another task's dataroot of the same
        # name was not asked for (surface D298).
        asked = {tuple(item.get("keypath") or ())
                 for item in entries if item.get("kind") == "dataroot"}
        packages = {environment.canonical(item.get("name") or "")
                    for item in entries if item.get("kind") == "python"}
        summary = self._stored_summary(job, root)
        paths = {record["collected_path"] for record in summary["values"]
                 if tuple(record.get("keypath") or ()) in asked
                 and record["origin"] != owners.PRIVATE
                 and owners.needed(tuple(record["key"]), summary["required"])}
        paths.discard(None)

        def allowed(member: str) -> bool:
            parts = member.split("/")
            if parts[0] != "sc_collected_files":
                return False
            if len(parts) > 1 and parts[1] == environment.WHEELS:
                # The wheels folder, and in it only a wheel asked for.
                return (len(parts) == 2 and bool(packages)) or \
                    (len(parts) == 3 and environment.wheel_name(parts[2]) in packages)
            inside = "/".join(parts[1:])
            # The collection directory, a bucket holding a requested file, the
            # file, or what a requested directory holds.
            return not inside or any(
                inside == path or inside.startswith(f"{path}/")
                or path.startswith(f"{inside}/") for path in paths)
        return allowed

    def _forget_upload(self, job, slug: str = "upload-forbidden") -> None:
        '''🔴 Delete an upload refused for what it must not carry: restricted
        material, `upload-forbidden` on either detection (surface D133), or a
        credential or a private dataroot's value (surface D307, D308) -- each
        is not kept. The row and the tree it expanded into go too: what
        remains is the job, its reason and the transition, which name the
        member; the refusal's `detail` is where the raiser puts it.'''
        row = self._store.one(
            "SELECT id, storage_key FROM artifacts WHERE job_id = ? AND upload_seq = "
            "(SELECT max(upload_seq) FROM artifacts WHERE job_id = ?)",
            (job["id"], job["id"]))
        shutil.rmtree(self.job_root(job["user_id"], job["id"]) / job["design"] / job["jobname"],
                      ignore_errors=True)
        if row is None:
            return
        self._storage.artifact_path(row["storage_key"]).unlink(missing_ok=True)
        with self._store.transaction():
            self._store.execute("DELETE FROM artifacts WHERE id = ?", (row["id"],))
        logger.warning(f"{job['id']}: deleted an upload refused as {slug}")
