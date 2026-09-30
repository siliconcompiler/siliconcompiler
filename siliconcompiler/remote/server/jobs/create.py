'''
Creating a job: the create body checked, a reused job found, and what the
server cannot supply asked for (surface §13).

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import hashlib
import json
import uuid

from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    CREATE_MEMBERS, DESCRIPTOR_MEMBERS, REUSABLE_STATES, _continuations, _declared_sources,
    _expired_key, _name, _only, _python_packages, _retention, _run_hash, logger, requirements)
from siliconcompiler.remote.server.software import images


class CreateMixin:
    '''Creating a job.'''

    ######################################################################
    # 13. create
    ######################################################################

    def create(self, session, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Tuple[Dict[str, Any], int]:
        '''Returns the job object and the status it should be served with.

        The top-level members are authoritative; everything under `descriptor`
        is advisory, checked again against the manifest's read while staging, and
        stored as `jobs.descriptor`.
        🔴 Strict, like every request body: an unknown member is refused, never
        ignored.
        '''
        with self._keyed(session.user_id, "create", idempotency_key):
            return self._create(session, body, idempotency_key)

    def _create(self, session, body, idempotency_key):
        if not isinstance(body, dict):
            raise ProblemError("invalid-request", detail="the body must be a JSON object")
        _only(body, CREATE_MEMBERS, "the create body")

        if body.get("project") is not None:
            # Refused rather than ignored: silently dropping it creates a job
            # the caller believes is shared and nobody else can see, which is a
            # failure invisible from both ends. Permanent, so a client stops
            # offering the picker.
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
        # 🔴 Top level, beside `design` and `jobname` (surface D160, job-reuse
        # D15): `descriptor` holds what submit re-derives, and nothing
        # recomputes this. Validated always; USED only where this deployment
        # advertises `jobs.reuse` -- elsewhere it is recorded and ignored, and
        # create is always a 201.
        run_hash = _run_hash(body.get("run_hash"))
        reuses = "jobs.reuse" in (self._config["features"] or ())
        # Authoritative, like run_hash: the server never reads a job id out of
        # the upload (surface D175).
        continuations = _continuations(body.get("continues_from"))
        # Authoritative too, and never re-derived: nothing in the manifest
        # records it (surface *What the create body lists*).
        packages = _python_packages(body.get("python_packages"))

        # 🔴 Credentials out of every source URL before anything is compared,
        # stored or logged -- the descriptor is kept whole in `jobs.descriptor`.
        declared = _declared_sources(descriptor)
        if declared is not None:
            descriptor = dict(descriptor, sources=declared)
        requires = requirements(descriptor)
        self._check_needs(descriptor)
        if packages is not None and "python.env" not in (self._config["features"] or ()):
            # 🔴 Relied on whether `needs` said so or not: a stale `GET /v1`,
            # or a client that forgot the string.
            raise ProblemError(
                "feature-unsupported", feature="python.env",
                detail="this job lists Python packages to install, and this deployment "
                       "does not install a job's Python packages")
        stored_packages = json.dumps(packages.wire()) if packages is not None else None

        if idempotency_key is not None:
            existing = self._store.one(
                "SELECT * FROM jobs WHERE user_id = ? AND idempotency_key = ?",
                (session.user_id, idempotency_key))
            if existing is not None and _expired_key(existing["created_at"]):
                # Forgetting a key clears its column, so the index accepts it again.
                with self._store.transaction():
                    self._store.execute("UPDATE jobs SET idempotency_key = NULL "
                                        "WHERE id = ?", (existing["id"],))
                existing = None
            if existing is not None:
                # The same key with a different body is the caller having reused
                # a key they should have rotated. Returning the first job would
                # answer a question they did not ask.
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

        # 🔴 Before the reuse lookup, because the answer is part of what the
        # lookup is keyed on -- and before the upload, which is the whole point
        # of resolving here at all.
        identity = self._identity(run_hash, requires, stored_packages) if reuses else None

        if identity:
            hit = self._reuse(session.user_id, identity)
            if hit is not None:
                # 200 rather than 201: a 201 carrying an old job's id is
                # indistinguishable from a new one. The body is the job object
                # either way, so a client that ignores the status is still
                # correct.
                logger.info(f"run_hash hit for {session.user_id}: {hit['id']}")
                return self.wire(hit), 200

        self._check_concurrent_jobs(session.user_id)
        self._check_pending_uploads(session.user_id)
        self._check_descriptor(descriptor, requires)
        # Before anything is uploaded: every earlier result this run would
        # take, and what those results were built from.
        self._check_continuations(session.user_id, continuations)

        asked = self._look_up(declared) if declared is not None else None

        # 🔴 The job's own image, from `requires.python` alone, before anything
        # is uploaded (surface §13; database D145): whether ONE image holds the
        # python set together is only the join's to say. Node images wait for
        # the manifest's read, which is what says which tools the nodes run.
        image_id = images.job_image_for(self._store, requires)["id"] \
            if self._config["containers"] else None

        job_id = str(uuid.uuid4())
        device_id = session.device_id

        def admit():
            # 🔴 Counted again, inside the transaction that inserts: the
            # checks above answer early, and these are what hold the ceiling
            # when several creates arrive at once (`Store.admission`).
            self._check_concurrent_jobs(session.user_id)
            self._check_pending_uploads(session.user_id)
            self._store.execute(
                "INSERT INTO jobs (id, user_id, device_id, state, design, jobname, "
                "                  descriptor, idempotency_key, run_hash, "
                "                  job_identity, retention_until, upload_sources, image_id, "
                "                  python_packages) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, session.user_id, device_id, design, jobname,
                 json.dumps(descriptor), idempotency_key, run_hash, identity,
                 _retention(self._config.limits["job_retention_days"]),
                 json.dumps(asked) if asked else None, image_id, stored_packages))
            for step, index, from_job in continuations:
                self._store.execute(
                    'INSERT INTO job_continuations (job_id, step, "index", from_job_id) '
                    "VALUES (?, ?, ?, ?)", (job_id, step, index, from_job))
            self._transition(job_id, None, "created", actor=session.user_id)

        self._store.admission(admit)

        # The job object, in `created`: `upload_sources` is on it where the
        # server is asking, and absent where there is nothing to send.
        reply = self.wire(self._row(job_id))
        if idempotency_key is not None:
            with self._store.transaction():
                self._store.execute("UPDATE jobs SET create_reply = ? WHERE id = ?",
                                    (json.dumps(reply), job_id))
        return reply, 201

    def _check_needs(self, descriptor) -> None:
        '''🔴 `needs`: every feature the job relies on must be one this server
        advertises -- refused at create, naming the first it lacks, rather than
        at submit after the upload. A string it does not know is refused the
        same way.'''
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
        '''What of the declared sources this server cannot supply: a LOOKUP,
        never a fetch (D124).

        =================================  =================================
        A source that is                   Answer
        =================================  =================================
        private, and not in the map        `resource-unavailable`, by name
        private, and in the map            supplied -- not listed
        held                               supplied -- not listed
        an installed package held here     supplied -- not listed
        on the allowlist, not held         assumed fetchable -- not listed
        anything else                      listed in `upload_sources`
        =================================  =================================

        🔴 No network: probing hundreds of dataroots against a slow git host
        put latency inside a request behind gateway timeouts, and turned one
        `POST` into hundreds of outbound requests.
        '''
        asked = []
        for item in declared:
            name, dataroot = item["name"], item["dataroot"]
            if item["private"]:
                # 🔴 Refused before a byte moves, by name alone (surface D285):
                # `sources` carries no kind, this server has no catalogue to
                # find one in, and a name is unique across kinds, so `resource`
                # says which and `resource_kind` is left out. The manifest's
                # read refuses one the descriptor never listed, while staging.
                if not self._supply.private_root(name, dataroot):
                    raise ProblemError(
                        "resource-unavailable", resource=name,
                        detail=f"{name} ({dataroot}) is marked private, and this "
                               "server holds no copy of it: a private source is "
                               "never uploaded, and only this server's operator can "
                               "supply one, by name")
                continue
            source, ref = item.get("source"), item.get("ref")
            if self._supply.held(source, ref) or self._supply.allowlisted(source, ref):
                continue
            if source and source.startswith("python://") and \
                    self._supply.package(source[len("python://"):].split("/")[0]):
                continue
            asked.append({"kind": "dataroot", "name": name, "dataroot": dataroot})
        return asked

    def _identity(self, run_hash: Optional[str], requires,
                  packages: Optional[str] = None) -> Optional[str]:
        '''``H(client hash || the digests it resolved to || python_packages)``,
        or None.

        🔴 **The client's hash alone is not the job's identity, and treating it
        as one hands back a result produced by different code.** The client
        hashes the work; this server chooses what runs it. Folding in the
        digests means two runs asking for the same thing but resolved to
        different images are correctly different jobs -- and re-registering an
        image invalidates reuse exactly when it should, because a new digest is
        precisely *the code changed*.

        🔴 **Computed from the descriptor and the registry only.** No uploaded
        bytes are involved, which is what lets this happen at create and save
        the upload. It is therefore the same value at create and at submit for
        the same declared versions, and it is written once.

        ⚠️ None where the client sent no hash, which is every SiliconCompiler
        client today: what SC should hash is a decision that lives elsewhere,
        and this half is proven by the conformance fixtures rather than left as
        dead code.
        '''
        if not run_hash:
            return None

        digests: List[str] = []
        if self._config["containers"]:
            digests = images.digests_for(self._store, requires)

        # The job's Python packages decide what the install gives the run,
        # and the client's hash may not cover them.
        payload = "\n".join([run_hash, *sorted(digests), *([packages] if packages else [])])
        return hashlib.sha256(payload.encode()).hexdigest()

    def _reuse(self, user_id: str, identity: str):
        '''The caller's own newest job with this identity, if it may be handed
        back.

        🔴 Owner-scoped, and that is the whole safety argument. Half of the
        identity is the client's own hash, which this server never recomputes
        or normalises, so a wrong one hands a user their own stale job --
        confusing, and not a disclosure. An archived job is excluded, which is
        how a person says *stop handing me that result* without an endpoint for
        it.

        🔴 And a candidate is checked against the registry as it is NOW --
        see `_still_current`. Matching is not enough: an image the job ran in
        may have been superseded since, and handing back a result produced by
        code that is gone is the thing reuse must not do.
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

        🔴 **What closes the gap the identity cannot.** The identity folds in
        the digests the DECLARED versions resolve to, because that is all there
        is at create -- the per-node tool images need the flow, which needs the
        manifest, which needs the upload the check exists to avoid. So
        re-registering an image that only ever served a TOOL leaves the
        identity unchanged, and the candidate would be handed back although the
        code that produced it is gone.

        ✅ A finished job records what its nodes RAN IN, so the question can be
        asked the other way round: are those images still live? It is
        computable at create, deterministic, and it invalidates only the jobs
        whose images actually changed.

        ⚠️ A job that ran in no image -- a deployment that runs on the host --
        has nothing to check and stays reusable.
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
        '''`pending_uploads`, where numeric: a hard ceiling on the caller's
        jobs in `created` or `awaiting_input`. `null` is unenforced.'''
        ceiling = self._config.limits["pending_uploads"]
        if ceiling is None:
            return
        held = [row["id"] for row in self._store.all(
            "SELECT id FROM jobs WHERE user_id = ? "
            "AND state IN ('created', 'awaiting_input') ORDER BY created_at", (user_id,))]
        if len(held) >= ceiling:
            # Which jobs hold the slots, so the client can cancel one it abandoned.
            raise ProblemError(
                "limit-exceeded", limit="pending_uploads", job_ids=held,
                detail=f"{len(held)} jobs are already waiting for their upload",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    def _check_descriptor(self, descriptor: Dict[str, Any], requires) -> None:
        '''The early reject, on whatever is present.

        Client-asserted, so this is a hint and not a boundary -- every value is
        checked again against the manifest's read. It exists to save an upload, and it
        never refuses
        a descriptor for being sparse: a missing field skips the check it would
        have answered.
        '''
        limits = self._config.limits

        flow = descriptor.get("flow")
        if flow is not None:
            if not isinstance(flow, dict):
                raise ProblemError("invalid-request", detail="descriptor.flow must be an object")
            _only(flow, ("name", "nodes"), "descriptor.flow")
        flow = flow or {}
        if isinstance(flow.get("nodes"), int):
            if flow["nodes"] > limits["max_job_nodes"]:
                raise ProblemError(
                    "node-limit-exceeded", limit="max_job_nodes",
                    detail=f"{flow['nodes']} nodes, and this server runs at most "
                           f"{limits['max_job_nodes']}")

        # The early entitlement check: the tools `requires` names and the
        # resources `sources` names, against what nobody here may use.
        # Re-derived at submit, where the manifest is the answer.
        # A source names no kind: the name finds it (entitlements D75).
        wanted = [(self._config.denied_kind(item["name"]), item["name"])
                  for item in descriptor.get("sources") or []]
        wanted += [("tool", name) for name in sorted(requires["tools"])]
        for kind, name in wanted:
            if kind is not None and self._config.denied(kind, name):
                raise ProblemError(
                    "entitlement-denied", resource_kind=kind, resource=name,
                    detail=f"this job names a {kind} this deployment does not allow")

        self._check_versions(requires)

    def _check_versions(self, requires: Dict[str, Dict[str, Any]]) -> None:
        '''Refuse a client this deployment cannot run.

        The cheap check, before the upload -- but only the cheap one: a client
        that declares nothing reaches the binding check at submit instead,
        after the whole archive has moved.

        🔴 **A requirement is a PEP 440 specifier and the SERVER resolves it.**
        A client cannot: `GET /v1`'s `software` is flat per name within a
        bucket while the image join is over combinations, so a client resolving
        each requirement on its own can name a set no single image holds --
        every version published, every one satisfiable, and nothing to run them
        in. ⚠️ A bare version means `==`, which is what every client sent
        before the wire carried ranges.

        ⚠️ **This is the per-name check and not the resolution.** It answers
        *does this server have anything matching* for each name on its own;
        *does ONE image hold all of them* is `digests_for`, which runs beside
        it at create. Both are needed: this one gives a name-specific
        `software-unavailable` where the join could only say the combination
        failed.

        🔴 **A name that is present and reports no version gets its own
        answer.** A tool recorded from its image's publish date is in
        `software`, which has nowhere to carry the mark, so a client's
        preflight says yes and this says no. Telling them *no image matches*
        would send them looking for a version that is already installed; the
        true answer is that nothing here can be matched against a range.
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
                    # 🔴 A listed name is never ignored: a python name nothing
                    # here tracks is checked against what jobs would run in.
                    if bucket == images.BUCKETS["python"]:
                        self._check_untracked_python(name, asked)
                    continue

                spec = images.specifiers(asked)
                if any(images.matches(version, "reported", spec)
                       for version in said.get(name, ())):
                    continue

                # Software no image holds, SiliconCompiler's own version
                # included (surface §7), whose answer names what is available.
                if here[name] and not said.get(name):
                    detail = (f"this server has {name}, and reports no version for "
                              "it -- so nothing here can be matched against a "
                              f"version requirement. Ask for {name} without one")
                else:
                    detail = (f"this server runs {name} {', '.join(here[name])}, "
                              f"and you asked for {asked}")
                raise ProblemError(
                    "software-unavailable", reason="unavailable", detail=detail,
                    unresolved=[{"name": name, "requirement": list(asked or ()),
                                 "available": sorted(said.get(name, ()))}])

    def _check_untracked_python(self, name: str, asked) -> None:
        '''A `requires.python` name the registry does not track: refused where
        nodes run in containers, since no live image holds it, and answered
        from this server's own Python where they run on the host.'''
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
            unresolved=[{"name": name, "requirement": list(asked or ()),
                         "available": available}])

    def _check_concurrent_jobs(self, user_id: str) -> None:
        '''`concurrent_jobs`, where numeric: a hard ceiling on the caller's
        jobs in `staging`, `queued`, `running` or `cancelling`. `null` is
        unenforced.'''
        ceiling = self._config.limits["concurrent_jobs"]
        if ceiling is None:
            return
        active = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            "AND state IN ('staging', 'queued', 'running', 'cancelling')", (user_id,))["n"]
        if active >= ceiling:
            raise ProblemError(
                "limit-exceeded", limit="concurrent_jobs",
                detail=f"{active} of your jobs are already running",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})
