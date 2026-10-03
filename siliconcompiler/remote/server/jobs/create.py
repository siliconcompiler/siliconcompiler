'''
Creating a job: the create body checked, a reused job found, and what the
server cannot supply asked for.
'''

import hashlib
import json
import uuid

from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.remote import environment, owners
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    CREATE_MEMBERS, DESCRIPTOR_MEMBERS, REUSABLE_STATES, _continuations, _declared_sources,
    _expired_key, _name, _only, _python_packages, _run_hash, logger, requirements)
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import ACTIVE_STATES, PENDING_STATES


class CreateMixin:
    '''Creating a job.'''

    def create(self, session, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Tuple[Dict[str, Any], int]:
        '''Returns the job object and the status to serve it with.

        Top-level members are authoritative; `descriptor` is advisory, checked
        again against the manifest's read while staging.
        '''
        with self._keyed(session.user_id, "create", idempotency_key):
            return self._create(session, body, idempotency_key)

    def _create(self, session, body, idempotency_key):
        _only(body, CREATE_MEMBERS, "the create body")

        if body.get("project") is not None:
            # Refused, not ignored: dropping it makes a job the caller believes
            # is shared and nobody else can see.
            raise ProblemError(
                "feature-unsupported", feature="projects",
                detail="this deployment has no projects; every job is personal")

        design = _name(body.get("design"), "design")
        jobname = _name(body.get("jobname"), "jobname")

        descriptor = body.get("descriptor")
        if descriptor is None:
            descriptor = {}
        if not isinstance(descriptor, dict):
            raise ProblemError("invalid-request", detail="descriptor must be an object")
        _only(descriptor, DESCRIPTOR_MEMBERS, "descriptor")
        # Top level, never recomputed. Always validated; used only where
        # `jobs.reuse` is advertised.
        run_hash = _run_hash(body.get("run_hash"))
        reuses = "jobs.reuse" in (self._config["features"] or ())
        # Authoritative: no job id is read out of the upload.
        continuations = _continuations(body.get("continues_from"))
        # Authoritative: nothing in the manifest records it.
        packages = _python_packages(body.get("python_packages"))

        # Credentials out of every source URL before anything is compared,
        # stored or logged.
        declared = _declared_sources(descriptor)
        if declared is not None:
            descriptor = dict(descriptor, sources=declared)
        requires = requirements(descriptor)
        self._check_needs(descriptor)
        if packages is not None and "python.env" not in (self._config["features"] or ()):
            # Whether or not `needs` said so.
            raise ProblemError(
                "feature-unsupported", feature="python.env",
                detail="this job lists Python packages to install, and this deployment "
                       "does not install a job's Python packages")
        stored_packages = json.dumps(packages.wire()) if packages is not None else None

        if idempotency_key is not None:
            existing = self._store.one(
                "SELECT * FROM jobs WHERE user_id = ? AND create_idempotency_key = ?",
                (session.user_id, idempotency_key))
            if existing is not None and _expired_key(existing["created_at"]):
                # Forgetting a key clears its column, so the index accepts it again.
                with self._store.transaction():
                    self._store.execute("UPDATE jobs SET create_idempotency_key = NULL "
                                        "WHERE id = ?", (existing["id"],))
                existing = None
            if existing is not None:
                # The same key with a different body: returning the first job
                # would answer a question not asked.
                if (existing["design"], existing["jobname"], existing["run_hash"],
                        json.loads(existing["descriptor"]),
                        self._continuations_of(existing["id"]),
                        existing["python_packages"]) != \
                        (design, jobname, run_hash, descriptor, sorted(continuations),
                         stored_packages):
                    raise ProblemError(
                        "idempotency-key-reuse",
                        detail="this Idempotency-Key was used for a different request")
                # The original answer, status and body.
                return (json.loads(existing["create_reply"]) if existing["create_reply"]
                        else self.wire(existing)), 201

        # Before the reuse lookup, which is keyed on it, and before the
        # upload it exists to save.
        image = images.job_image_for(self._store, requires) \
            if reuses and run_hash and self._config["containers"] else None
        identity = self._identity(run_hash, requires, stored_packages, image) \
            if reuses else None

        if identity:
            hit = self._reuse(session.user_id, identity)
            if hit is not None:
                # 200, not 201: a 201 with an old job's id looks like a new one.
                logger.info(f"run_hash hit for {session.user_id}: {hit['id']}")
                return self.wire(hit), 200

        self._check_concurrent_jobs(session.user_id)
        self._check_pending_uploads(session.user_id)
        self._check_descriptor(descriptor, requires)
        # Before anything is uploaded.
        self._check_continuations(session.user_id, continuations)

        asked = self._look_up(declared) if declared is not None else None

        # The job's own image, from `requested_versions.python` alone, before
        # the upload. Node images wait for the manifest's read, which says
        # which tools the nodes run.
        if image is None and self._config["containers"]:
            image = images.job_image_for(self._store, requires)
        image_id = image["id"] if image else None

        job_id = str(uuid.uuid4())
        device_id = session.device_id

        # The wheel answering a `python` ask replaces its listed entry.
        # Create asks only for dataroots today, so none is.
        answered = sorted({environment.canonical(item["name"]) for item in asked or []
                           if item.get("kind") == "python" and item.get("name")})

        def admit():
            # Counted again inside the inserting transaction, which holds the
            # ceiling against concurrent creates (`Store.admission`).
            self._check_concurrent_jobs(session.user_id)
            self._check_pending_uploads(session.user_id)
            self._store.execute(
                "INSERT INTO jobs (id, user_id, device_id, state, design, jobname, "
                "                  descriptor, create_idempotency_key, run_hash, "
                "                  job_identity, upload_sources, image_id, python_packages, "
                "                  python_answered) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, session.user_id, device_id, design, jobname,
                 json.dumps(descriptor), idempotency_key, run_hash, identity,
                 json.dumps(asked) if asked else None, image_id, stored_packages,
                 json.dumps(answered) if answered else None))
            for step, index, from_job in continuations:
                self._store.execute(
                    'INSERT INTO job_continuations (job_id, step, "index", from_job_id) '
                    "VALUES (?, ?, ?, ?)", (job_id, step, index, from_job))
            self._transition(job_id, None, "created", actor=session.user_id)

        self._store.admission(admit)

        reply = self.wire(self._row(job_id))
        if idempotency_key is not None:
            with self._store.transaction():
                self._store.execute("UPDATE jobs SET create_reply = ? WHERE id = ?",
                                    (json.dumps(reply), job_id))
        return reply, 201

    def _check_needs(self, descriptor) -> None:
        '''`needs`: every feature the job relies on must be advertised;
        refused at create, not after the upload.'''
        needs = descriptor.get("needs")
        if needs is None:
            return
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            raise ProblemError("invalid-request", detail="needs is a list of feature strings")
        advertised = set(self._config["features"] or ())
        for feature in needs:
            if feature not in advertised:
                raise ProblemError(
                    "feature-unsupported", feature=feature,
                    detail=f"this job needs {feature}, which this deployment does "
                           "not offer")

    def _look_up(self, declared) -> List[Dict[str, Any]]:
        '''What of the declared sources this server cannot supply, to list in
        `upload_sources`: a LOOKUP, never a fetch. Held, allowlisted and
        installed-package sources are supplied; a private one none of those
        covers is `resource-unavailable`.

        No network: probing hundreds of dataroots inside a request would
        meet gateway timeouts and multiply one `POST` into hundreds.
        '''
        asked = []
        for item in declared:
            keypath = item["keypath"]
            source, ref = item.get("source"), item.get("ref")
            if item["private"]:
                # Never asked for; one nothing here can supply is refused
                # before a byte moves.
                if self._supply.private_root(keypath) or \
                        self._supply.held(source, ref) or \
                        self._supply.allowlisted(source, ref):
                    continue
                raise ProblemError(
                    "resource-unavailable", resource=owners.keypath_owner(keypath),
                    keypath=list(keypath),
                    detail=f"the private dataroot {owners.shown(keypath)} is not held "
                           "by this server, and it cannot fetch it either: a private "
                           "source is never uploaded or asked for")
            if self._supply.held(source, ref) or self._supply.allowlisted(source, ref):
                continue
            if source and source.startswith("python://") and \
                    self._supply.package(source[len("python://"):].split("/")[0]):
                continue
            asked.append({"kind": "dataroot", "keypath": list(keypath)})
        return asked

    def _identity(self, run_hash: Optional[str], requires,
                  packages: Optional[str] = None, image=None) -> Optional[str]:
        '''``H(client hash, the digests it resolved to, python_packages, the
        interpreter it asked for, the index configuration)``, or None.

        The client hashes the work; this server chooses what runs it, so the
        digests are folded in and re-registering an image invalidates reuse.

        From the descriptor and registry only, so it is computed at create,
        before the upload, and written once.

        None where the client sent no hash, as SiliconCompiler does today.
        '''
        if not run_hash:
            return None

        digests = [image["digest"]] if image else []

        # What else decides what the install gives the run, which the
        # client's hash may not cover.
        indexes = {"indexes": list(self._config["package_indexes"] or []),
                   "source_builds": bool(self._config["python_source_builds"])} \
            if packages else None
        payload = json.dumps({"run_hash": run_hash, "digests": sorted(digests),
                              "python_packages": packages,
                              "interpreter": requires.get("interpreter") or {},
                              "indexes": indexes}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _reuse(self, user_id: str, identity: str):
        '''The caller's own newest job with this identity, if it may be handed
        back.

        Owner-scoped, the whole safety argument: a wrong client hash hands a
        user their own stale job, not a disclosure. Archiving a job is how a
        person stops it being handed back.
        '''
        placeholders = ", ".join("?" * len(REUSABLE_STATES))
        candidate = self._store.one(
            "SELECT * FROM jobs WHERE user_id = ? AND job_identity = ? "
            f"  AND state IN ({placeholders}) "
            "  AND deleted_at IS NULL AND archived_at IS NULL "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (user_id, identity, *REUSABLE_STATES))

        if candidate is None or self._still_current(candidate):
            return candidate

        logger.info(f"{candidate['id']} matches, and the images it ran in have "
                    "been superseded; running it again")
        return None

    def _still_current(self, job) -> bool:
        '''Whether the images this job actually ran in are still live.

        The identity can only fold in the DECLARED versions' digests, since
        node images need the manifest; this catches a re-registered tool image.
        A job that ran in no image stays reusable.
        '''
        rows = self._store.all(
            "SELECT DISTINCT image_id FROM job_nodes "
            "WHERE job_id = ? AND image_id IS NOT NULL", (job["id"],))

        ran_in = {row["image_id"] for row in rows}
        if job["image_id"]:
            ran_in.add(job["image_id"])
        if not ran_in:
            return True

        live = {row["id"] for row in self._store.all(
            "SELECT id FROM images WHERE retired_at IS NULL")}
        return ran_in <= live

    def _check_pending_uploads(self, user_id: str) -> None:
        '''`pending_uploads`, a hard ceiling where not `null`.'''
        ceiling = self._config.limits["pending_uploads"]
        if ceiling is None:
            return
        held = [row["id"] for row in self._store.all(
            "SELECT id FROM jobs WHERE user_id = ? "
            f"AND state IN ({', '.join('?' * len(PENDING_STATES))}) ORDER BY created_at",
            (user_id, *PENDING_STATES))]
        if len(held) >= ceiling:
            # Which jobs hold the slots, so the client can cancel one it abandoned.
            raise ProblemError(
                "limit-exceeded", limit="pending_uploads", job_ids=held,
                detail=f"{len(held)} jobs are already waiting for their upload",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    def _check_descriptor(self, descriptor: Dict[str, Any], requires) -> None:
        '''The early reject, on whatever is present: a hint to save an upload,
        not a boundary, so a missing field skips its check.'''
        limits = self._config.limits

        flow = descriptor.get("flow")
        if flow is not None and not isinstance(flow, str):
            raise ProblemError("invalid-request",
                               detail="descriptor.flow is the flowgraph's name, a string")
        count = descriptor.get("node_count")
        if count is not None:
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ProblemError("invalid-request",
                                   detail="descriptor.node_count is a whole number of nodes")
            if count > limits["max_job_nodes"]:
                raise ProblemError(
                    "node-limit-exceeded", limit="max_job_nodes",
                    detail=f"{count} nodes, and this server runs at most "
                           f"{limits['max_job_nodes']}")

        # The early entitlement check, re-derived at submit. A task's dataroot
        # needs its tool; a library's owner may be any resource kind.
        wanted = []
        for item in descriptor.get("sources") or []:
            keypath, name = item["keypath"], owners.keypath_owner(item["keypath"])
            wanted += [("tool", name)] if keypath[0] == "tool" else \
                [(kind, name) for kind in owners.RESOURCE_KINDS]
        wanted += [("tool", name) for name in sorted(requires["tools"])]
        for kind, name in wanted:
            if self._config.denied(kind, name):
                raise ProblemError(
                    "entitlement-denied", resource_kind=kind, resource=name,
                    detail=f"this job names a {kind} this deployment does not allow")

        self._check_versions(requires)

    def _check_versions(self, requires: Dict[str, Dict[str, Any]]) -> None:
        '''Refuse a client this deployment cannot run: the cheap check, before
        the upload.

        A requirement is a PEP 440 specifier and the SERVER resolves it: a
        client sees a flat list per name, not which combinations one image
        holds. A bare version means `==`.

        The per-name check, giving a name-specific answer; whether ONE image
        holds them all is `images.job_image_for`.

        A name present with no reported version gets its own answer, not *no
        image matches*, which would send the user looking for what is installed.
        '''
        from siliconcompiler.remote.server.routes.meta import (
            advertised_reported, advertised_software)

        available = advertised_software(self._store, self._config)
        reported = advertised_reported(self._store, self._config)

        for bucket, wanted in requires.items():
            here = available.get(bucket) or {}
            said = reported.get(bucket) or {}

            for name, asked in wanted.items():
                if name not in here:
                    # A listed name is never ignored.
                    if bucket == images.BUCKETS["python"]:
                        self._check_untracked_python(name, asked)
                    elif bucket == images.BUCKETS["interpreter"]:
                        raise ProblemError(
                            "software-unavailable", reason="unavailable",
                            detail=f"the job's own Python needs {', '.join(asked)}, and "
                                   "no image this server runs records its Python: the "
                                   "operator would have to register one",
                            unresolved=[{"kind": bucket, "name": name,
                                         "requirement": list(asked or ()),
                                         "available": []}])
                    continue

                spec = images.specifiers(asked)
                if any(images.matches(version, "reported", spec)
                       for version in said.get(name, ())):
                    continue

                # Software no image holds, SiliconCompiler included.
                if bucket == images.BUCKETS["interpreter"]:
                    # The friction is the point: said before the upload
                    # rather than failing a test later.
                    detail = (f"the job's own Python needs {', '.join(asked)}, and this "
                              f"server's images run Python {', '.join(here[name])}: the "
                              "operator would have to add an image with that Python")
                elif here[name] and not said.get(name):
                    detail = (f"this server has {name}, and reports no version for "
                              "it -- so nothing here can be matched against a "
                              f"version requirement. Ask for {name} without one")
                else:
                    detail = (f"this server runs {name} {', '.join(here[name])}, "
                              f"and you asked for {asked}")
                raise ProblemError(
                    "software-unavailable", reason="unavailable", detail=detail,
                    unresolved=[{"kind": bucket, "name": name,
                                 "requirement": list(asked or ()),
                                 "available": sorted(said.get(name, ()))}])

    def _check_untracked_python(self, name: str, asked) -> None:
        '''A `requested_versions.python` name the registry does not track:
        refused with containers, else answered from this server's own Python.'''
        from importlib import metadata

        spec = images.specifiers(asked)
        available = []
        if not self._config["containers"]:
            try:
                version = metadata.version(name)
            except metadata.PackageNotFoundError:
                version = None
            if version is not None:
                if images.matches(version, "reported", spec):
                    return
                available = [version]

        where = "no image this server runs holds it" if self._config["containers"] \
            else (f"this server runs {name} {available[0]}" if available
                  else f"this server's Python has no {name}")
        raise ProblemError(
            "software-unavailable", reason="unavailable",
            detail=f"the job needs {name} {', '.join(asked) or '(any version)'}, and {where}",
            unresolved=[{"kind": "python", "name": name, "requirement": list(asked or ()),
                         "available": available}])

    def _check_concurrent_jobs(self, user_id: str) -> None:
        '''`concurrent_jobs`, a hard ceiling where not `null`.'''
        ceiling = self._config.limits["concurrent_jobs"]
        if ceiling is None:
            return
        active = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            f"AND state IN ({', '.join('?' * len(ACTIVE_STATES))})",
            (user_id, *ACTIVE_STATES))["n"]
        if active >= ceiling:
            raise ProblemError(
                "limit-exceeded", limit="concurrent_jobs",
                detail=f"{active} of your jobs are already running",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})
