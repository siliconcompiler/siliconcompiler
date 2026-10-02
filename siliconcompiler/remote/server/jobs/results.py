'''
What a run left, as a caller reaches it: artifacts, their bytes, and node and
job logs, through the same ownership and approval checks.

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.utils.units import format_binary
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    SURFACES, TERMINAL_NODE_STATES, TERMINAL_STATES, _ALERTED, _WITHOUT, _decode_cursor,
    _encode_cursor, _limit, logger)
from siliconcompiler.remote.server.outputs import artifacts, confine


class ResultsMixin:
    '''What a run left, as a caller reaches it.'''

    ######################################################################
    # Artifacts
    ######################################################################

    def _surface_allows(self, surface: str, kind: str) -> bool:
        '''Whether ``surface`` hands over artifacts of ``kind``.

        🔴 **`api_fetchable_kinds` binds the API and not the portal**, for the
        reason `max_download_bytes` does: the portal is a person choosing one
        object. Both disagreements between the surfaces are decided from the
        one ``surface`` argument so that they are written down in one place.
        '''
        if surface not in SURFACES:
            raise ValueError(f"{surface} is not a surface")
        return surface == "portal" or self._config.api_fetchable(kind)

    def _members_refusal(self, row, surface: str) -> Optional[str]:
        '''Row 4: a `node` archive is fetchable only when every artifact at its
        coordinates is -- other `node` rows and `issue` excepted -- because it
        holds them all, and handing it over would hand over any one that is
        not. Returns the WORST member's refusal (D120), or None.'''
        if row["kind"] != "node":
            return None
        # `input` is not a member either: the node archive leaves `inputs/`
        # out. Nor the server's own records, which are never in a node's tree.
        members = self._store.all(
            'SELECT * FROM artifacts WHERE job_id = ? AND step = ? AND "index" = ? '
            "AND kind NOT IN ('node', 'issue', 'input', 'staging', 'diagnostics')",
            (row["job_id"], row["step"], row["index"]))
        refusals = [artifacts.ladder(member, self._surface_allows(surface, member["kind"]),
                                     admin=surface == "portal")
                    for member in members]
        if "not-found" in refusals and not row["deleted_at"]:
            # 🔴 A member deleted on its own, under a live node archive
            # (entitlements D41). Handing the archive over would undo the
            # deletion, so it is `artifact-not-approved` -- and the state should
            # not exist, since a node is reaped with its first member, so an
            # operator is told: reaching it is a bug.
            if row["id"] not in _ALERTED:
                _ALERTED.add(row["id"])
                logger.error(f"node archive {row['id']} of job {row['job_id']} "
                             f"({row['step']}/{row['index']}) has a member deleted on "
                             "its own; a node is reaped as a whole, so this is a bug")
            refusals = ["artifact-not-approved" if refusal == "not-found" else refusal
                        for refusal in refusals]
        return artifacts.worst(refusals)

    def _refuse_by_ladder(self, row, surface: str) -> None:
        '''Raise the refusal the ladder's deciding row names, if any.'''
        refusal = artifacts.ladder(row, self._surface_allows(surface, row["kind"]),
                                   self._members_refusal(row, surface),
                                   admin=surface == "portal")
        if refusal is None:
            return
        if refusal == "not-found":
            raise ProblemError("not-found", detail="these bytes were deleted")
        if refusal == "not-ready":
            # Transient: it is still being described.
            raise ProblemError(
                "not-ready", artifact_kind=row["kind"],
                detail="this artifact is still being described",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})
        raise ProblemError(
            "artifact-not-approved",
            detail="this artifact is not handed over here; the web portal has it"
            if not self._surface_allows(surface, row["kind"])
            else "this artifact is held back from download")

    def artifacts(self, session, job_id: str, args, surface: str = "api"):
        '''Endpoint 21: what this run produced, as far as this caller is
        concerned.'''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            # The job stays readable and its subresources do not.
            raise ProblemError("not-found", detail="this job's data was deleted")

        # 🔴 Listed once described (surface D308): never an artifact still
        # being described, nor a `node` archive with such a member, so a client
        # fetching at `terminal` misses nothing it could have had.
        where = ["job_id = ?", "provenance <> 'pending'",
                 "NOT (kind = 'node' AND EXISTS (SELECT 1 FROM artifacts AS member "
                 "  WHERE member.job_id = artifacts.job_id AND member.step = artifacts.step "
                 '  AND member."index" = artifacts."index" '
                 "  AND member.kind NOT IN ('node', 'issue', 'input', 'staging', 'diagnostics') "
                 "  AND member.provenance = 'pending'))"]
        params: List[Any] = [job["id"]]

        kind = args.get("kind")
        if kind:
            if self._store.one("SELECT 1 FROM artifact_kinds WHERE kind = ?",
                               (kind,)) is None:
                raise ProblemError("invalid-request", detail=f"no such kind: {kind}")
            where.append("kind = ?")
            params.append(kind)

        if args.get("step"):
            where.append("step = ?")
            params.append(args["step"])
        if args.get("index"):
            where.append('"index" = ?')
            params.append(args["index"])

        cursor = args.get("cursor")
        if cursor:
            created_at, artifact_id = _decode_cursor(cursor)
            where.append("(created_at > ? OR (created_at = ? AND id > ?))")
            params.extend([created_at, created_at, artifact_id])

        limit = _limit(args.get("limit"))
        rows = self._store.all(
            f"SELECT * FROM artifacts WHERE {' AND '.join(where)} "
            "ORDER BY created_at, id LIMIT ?", (*params, limit + 1))

        more = len(rows) > limit
        rows = rows[:limit]

        items = [artifacts.wire(row, self._surface_allows(surface, row["kind"]),
                                self._members_refusal(row, surface),
                                admin=surface == "portal")
                 for row in rows]
        return items, (_encode_cursor(rows[-1]) if more and rows else None)

    def artifact(self, session, job_id: str, artifact_id: str,
                 surface: str = "api"):
        '''Endpoint 22's row, with the refusals it can make.

        ``surface`` is what the two surfaces disagree about, and it is a
        parameter rather than two code paths so that the disagreement is
        written down in one place: ``"api"`` or ``"portal"``. 🔴
        **`max_download_bytes` and `api_fetchable_kinds` bind the API and not
        the portal.** There is no API override for it -- no query
        parameter, no header -- because a limit a caller can switch off is not
        a limit. The portal is the way past it, and it is allowed to be because
        it is a different surface with a person on it who has just clicked the
        object: a browser download is somebody deciding, one object at a time,
        and the ceiling exists to stop an automated sweep pulling gigabytes
        nobody asked for.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        row = self._store.one(
            "SELECT * FROM artifacts WHERE id = ? AND job_id = ?",
            (artifact_id, job["id"]))
        if row is None:
            raise ProblemError("not-found", detail="no such artifact")

        if row["deleted_at"]:
            # The bytes are gone. 404 rather than 403: there is nothing to be
            # entitled to.
            raise ProblemError("not-found", detail="these bytes were deleted")

        self._refuse_by_ladder(row, surface)

        if surface == "api":
            self._check_download_ceiling(session, row)

        return row

    def _check_download_ceiling(self, session, row) -> None:
        '''Refuse one object that is larger than this caller may pull.

        🔴 The CALLER's number and not the deployment's: `max_download_bytes`
        is the one limit a `user_limits` row may override, so reading
        `config.limits` here would enforce a ceiling the account was
        deliberately lifted above. `None` is unlimited, which is the wire's
        meaning for it everywhere.

        🔴 `403 download-too-large` (D117), not `429 limit-exceeded`: that one
        means *refills*, and a client obeying its `Retry-After` on a ceiling
        that never refills would retry for ever. The download side of
        `upload-too-large`.
        '''
        from siliconcompiler.remote.server.identity import accounts

        allowed = accounts.effective_limits(
            self._store, self._config, session.user_id)["max_download_bytes"]
        if allowed is None:
            return

        stored = row["size_bytes"] or 0
        if stored <= allowed:
            return

        stored = format_binary(stored, "B", digits=1, show_unit=True, compact=True, default="—")
        allowed = format_binary(allowed, "B", digits=1, show_unit=True, compact=True,
                                default="—")
        raise ProblemError(
            "download-too-large", limit="max_download_bytes",
            detail=f"{stored} is larger than the {allowed} this account may download over "
                   "the API; open it from the web portal instead")

    def node_log(self, session, job_id: str, step: str, index: str,
                 surface: str = "api"):
        '''Endpoint 20 for one node: whether its live stream may be opened.

        🔴 **`/logs` is live output only** (surface §20). A running node
        streams; a finished one streams too, and its stream ends at once
        naming its `logs` artifact, which is fetched through endpoint 22. A
        node not started is `409 not-ready`, and a finished node that kept no
        log is `404`. Returns the node.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        if surface == "api" and "logs.stream" not in self._config["features"]:
            raise ProblemError(
                "feature-unsupported", feature="logs.stream",
                detail=_WITHOUT["logs.stream"])

        node = self._store.one(
            'SELECT * FROM job_nodes WHERE job_id = ? AND step = ? AND "index" = ?',
            (job["id"], step, index))
        if node is None:
            raise ProblemError("not-found", detail=f"no node {step}/{index} in this job")

        if node["state"] in ("pending", "queued", "preparing"):
            raise ProblemError(
                "not-ready", artifact_kind="logs",
                detail=f"{step}/{index} has not started",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

        if node["state"] in TERMINAL_NODE_STATES:
            self._index_node(job, step, index)
            row = self._store.one(
                "SELECT * FROM artifacts WHERE job_id = ? AND step = ? "
                'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
                "ORDER BY created_at LIMIT 1", (job["id"], step, index))
            if row is None:
                raise ProblemError("not-found", detail=f"no log was kept for {step}/{index}")
            # The stream names this artifact: a caller who could not fetch it
            # is not handed it by asking for the log.
            self._refuse_by_ladder(row, surface)

        return node

    def job_log(self, session, job_id: str):
        '''Endpoint 20 with no coordinates: the whole job's live stream.

        Returns the job when the answer is a stream -- which it is for a job
        that is running AND for one that is over, whose stream sends `end` at
        once. Everything else is a refusal.

        🔴 **A missing capability is named at its broadest**: `logs.stream`,
        then `logs.stream.job`. A client told only that the job stream is
        missing, on a deployment that serves no live log at all, would fall
        back to per-node requests that fail too.

        ⚠️ The terminal answer is deliberately not a refusal. A job can end
        between the `303` and the connect, and the stream already answers that
        with `end`; a request that arrives after the end is the same case
        arriving late, and gets the same path.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        features = self._config["features"]
        for feature in ("logs.stream", "logs.stream.job"):
            if feature not in features:
                raise ProblemError(
                    "feature-unsupported", feature=feature,
                    detail=_WITHOUT[feature])

        if job["state"] in TERMINAL_STATES:
            return job

        started = self._store.one(
            "SELECT 1 FROM job_nodes WHERE job_id = ? "
            "AND state NOT IN ('pending', 'queued', 'preparing') LIMIT 1",
            (job["id"],))
        if started is None:
            # The same answer a node gives before it starts: transient.
            raise ProblemError(
                "not-ready", artifact_kind="logs",
                detail="no node of this job has started",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

        return job

    def job_nodes(self, job_id: str) -> List[Tuple[str, str]]:
        '''Every node of a job, in the one order a job stream's id relies on.'''
        return [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? '
            'ORDER BY step, "index"', (job_id,))]

    def node_states(self, job_id: str) -> Dict[Tuple[str, str], str]:
        '''What every node is doing NOW, read fresh for a stream that asks
        over and over.'''
        return {(row["step"], row["index"]): row["state"] for row in self._store.all(
            'SELECT step, "index", state FROM job_nodes WHERE job_id = ?', (job_id,))}

    def job_over(self, job_id: str) -> bool:
        row = self._store.one("SELECT state FROM jobs WHERE id = ?", (job_id,))
        return row is None or row["state"] in TERMINAL_STATES

    def node_logs(self, session, job_id: str, step: str, index: str):
        '''Every log one node left, as (name, path).

        🔴 A node writes more than one and they answer different questions.
        `sc_<step>_<index>.log` is SiliconCompiler's own record of the node --
        setup, inputs, timing -- and `<step>.log` is what the TOOL printed,
        which is where a synthesis error actually is. Offering only the first
        sends somebody looking for OpenROAD's complaint to a file that does not
        contain it.

        Read from the node's working directory rather than from the indexed
        artifact, because only one of them is indexed. Ownership was decided
        above, by the same predicate the API evaluates.
        '''
        job = self.owned(session, job_id)

        workdir = (self.job_root(job["user_id"], job["id"]) / job["design"] /
                   job["jobname"] / step / index)
        if not workdir.is_dir():
            return []

        # SiliconCompiler's own first: it is the one that says what the node
        # was asked to do, which is where to start when a node failed.
        own = f"sc_{step}_{index}.log"
        found = sorted(workdir.glob("*.log"),
                       key=lambda path: (path.name != own, path.name))
        return [(path.name, path) for path in found]

    def stream_index_path(self, job_id: str) -> Path:
        '''The job stream's event index (D121).

        Outside the job's build directory, which an uploaded archive fills: an
        index is the server's record of what it streamed, and a member could
        otherwise be one.
        '''
        return self._datadir / "streams" / f"{job_id}.idx"

    def read_node_file(self, session, job_id: str, path) -> str:
        '''A file out of one of this caller's job trees, as text -- a regular
        file under the job's root reached through no link. Raises OSError
        otherwise: a node's code can leave a link in its own tree, and reading
        through it would show the caller the host's files.'''
        job = self.owned(session, job_id)
        with confine.open_inside(self.job_root(job["user_id"], job["id"]), path,
                                 "r", errors="replace") as handle:
            return handle.read()

    def node_log_path(self, job, step: str, index: str):
        '''Where the bytes a tail reads are.'''
        return (self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / step / index / f"sc_{step}_{index}.log")

    def node_state(self, job_id: str, step: str, index: str):
        '''What this node is doing NOW.

        Read fresh every time rather than captured, because a stream asks over
        and over across the hours it may be open.
        '''
        row = self._store.one(
            'SELECT state FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        return row["state"] if row else None

    def node_log_artifact(self, job_id: str, step: str, index: str):
        '''The archived log's id, indexing it first if it is not there yet.

        🔴 Called as a tail reaches the end of a node. The alternative is
        waiting for the next poll to reconcile, which leaves a window where the
        stream has said `terminal` and the archive it names does not exist --
        so a client that follows the `end` event straight to `/logs` is told
        there is no log for a node whose log it has just finished reading.
        '''
        job = self._row(job_id)
        if job is not None:
            self._index_node(job, step, index)

        row = self._store.one(
            "SELECT id FROM artifacts WHERE job_id = ? AND step = ? "
            'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
            "ORDER BY created_at LIMIT 1", (job_id, step, index))
        return row["id"] if row else None
