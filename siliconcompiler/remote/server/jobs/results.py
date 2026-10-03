'''
What a run left, as a caller reaches it: artifacts, their bytes, and node and
job logs, through the same ownership and approval checks.
'''

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.utils.units import format_binary
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs.common import (
    SURFACES, _ALERTED, _WITHOUT, _decode_cursor, _encode_cursor, _limit, logger)
from siliconcompiler.remote.server.outputs import artifacts, confine
from siliconcompiler.remote.server.state.store import TERMINAL_NODE_STATES, TERMINAL_STATES

# The kinds that are never a `node` archive's members.
_NOT_MEMBERS = ("node", "issue", "input", "staging", "diagnostics")
_NOT_A_MEMBER = f"kind NOT IN ({', '.join('?' * len(_NOT_MEMBERS))})"

# A node's states before it starts: nothing to stream yet.
_NOT_STARTED = ("pending", "queued", "preparing")


class ResultsMixin:
    '''What a run left, as a caller reaches it.'''

    def _surface_allows(self, surface: str, kind: str) -> bool:
        '''Whether ``surface`` hands over artifacts of ``kind``;
        `api_fetchable_kinds` binds the API only (see `artifact`).'''
        if surface not in SURFACES:
            raise ValueError(f"{surface} is not a surface")
        return surface == "portal" or self._config.api_fetchable(kind)

    def _members_refusal(self, row, surface: str) -> Optional[str]:
        '''Ladder row 4: a `node` archive holds every artifact at its
        coordinates, so it is fetchable only when they all are. Returns the
        WORST member's refusal (D120), or None.'''
        if row["kind"] != "node":
            return None
        members = self._store.all(
            'SELECT * FROM artifacts WHERE job_id = ? AND step = ? AND "index" = ? '
            f"AND {_NOT_A_MEMBER}", (row["job_id"], row["step"], row["index"], *_NOT_MEMBERS))
        refusals = [artifacts.ladder(member, self._surface_allows(surface, member["kind"]),
                                     admin=surface == "portal")
                    for member in members]
        if "not-found" in refusals and not row["deleted_at"]:
            # 🔴 A member deleted on its own (entitlements D41): handing the
            # archive over would undo the deletion. The state is a bug.
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
        '''Endpoint 21: what this run produced, for this caller.'''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            # The job stays readable and its subresources do not.
            raise ProblemError("not-found", detail="this job's data was deleted")

        # 🔴 Listed once described, a `node` archive once its members are
        # (surface D308).
        where = ["job_id = ?", "provenance <> 'pending'",
                 "NOT (kind = 'node' AND EXISTS (SELECT 1 FROM artifacts AS member "
                 "  WHERE member.job_id = artifacts.job_id AND member.step = artifacts.step "
                 '  AND member."index" = artifacts."index" '
                 f"  AND member.{_NOT_A_MEMBER} "
                 "  AND member.provenance = 'pending'))"]
        params: List[Any] = [job["id"], *_NOT_MEMBERS]

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

        🔴 `max_download_bytes` and `api_fetchable_kinds` bind the API, not the
        portal, and nothing on the API overrides them: the portal is a person
        clicking one object, and the ceiling stops an automated sweep.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        row = self._store.one(
            "SELECT * FROM artifacts WHERE id = ? AND job_id = ?",
            (artifact_id, job["id"]))
        if row is None:
            raise ProblemError("not-found", detail="no such artifact")

        self._refuse_by_ladder(row, surface)

        if surface == "api":
            self._check_download_ceiling(session, row)

        return row

    def _check_download_ceiling(self, session, row) -> None:
        '''Refuse one object that is larger than this caller may pull.

        🔴 The CALLER's number, which `user_limits` may override, not
        `config.limits`.
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
        '''Endpoint 20 for one node: whether its live stream may be opened;
        returns the node.

        🔴 `/logs` is live output only (surface §20): a finished node's stream
        ends at once, naming its `logs` artifact.
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

        if node["state"] in _NOT_STARTED:
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
            # The stream names it, so a caller who could not fetch it is refused.
            self._refuse_by_ladder(row, surface)

        return node

    def job_log(self, session, job_id: str):
        '''Endpoint 20 with no coordinates: the whole job's live stream;
        returns the job, or refuses.

        🔴 A missing capability is named at its broadest, or a client would fall
        back to per-node streams that fail too.

        ⚠️ A finished job is deliberately not refused: its stream sends `end` at
        once, as for a job that ends between the `303` and the connect.
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
            f"AND state NOT IN ({', '.join('?' * len(_NOT_STARTED))}) LIMIT 1",
            (job["id"], *_NOT_STARTED))
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
        '''What every node is doing NOW.'''
        return {(row["step"], row["index"]): row["state"] for row in self._store.all(
            'SELECT step, "index", state FROM job_nodes WHERE job_id = ?', (job_id,))}

    def job_over(self, job_id: str) -> bool:
        return self._row(job_id)["state"] in TERMINAL_STATES

    def node_logs(self, session, job_id: str, step: str, index: str):
        '''Every log one node left, as (name, path), from its working
        directory: SiliconCompiler's own record, and what the TOOL printed,
        where a synthesis error actually is. Only the first is indexed.'''
        job = self.owned(session, job_id)

        workdir = (self.job_root(job["user_id"], job["id"]) / job["design"] /
                   job["jobname"] / step / index)
        if not workdir.is_dir():
            return []

        # SiliconCompiler's own first: where to start when a node failed.
        own = f"sc_{step}_{index}.log"
        found = sorted(workdir.glob("*.log"),
                       key=lambda path: (path.name != own, path.name))
        return [(path.name, path) for path in found]

    def stream_index_path(self, job_id: str) -> Path:
        '''The job stream's event index (D121), outside the build directory an
        uploaded archive fills, so no member can pose as one.'''
        return self._datadir / "streams" / f"{job_id}.idx"

    def read_node_file(self, session, job_id: str, path) -> str:
        '''A regular file under one of this caller's job roots, as text,
        reached through no link: a node can leave a link to the host's files.
        Raises OSError otherwise.'''
        job = self.owned(session, job_id)
        with confine.open_inside(self.job_root(job["user_id"], job["id"]), path,
                                 "r", errors="replace") as handle:
            return handle.read()

    def node_log_path(self, job, step: str, index: str):
        '''Where the bytes a tail reads are.'''
        return (self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / step / index / f"sc_{step}_{index}.log")

    def node_state(self, job_id: str, step: str, index: str):
        '''What this node is doing NOW, read fresh each time.'''
        row = self._store.one(
            'SELECT state FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        return row["state"] if row else None

    def node_log_artifact(self, job_id: str, step: str, index: str):
        '''The archived log's id, indexing it first if it is not there yet.

        🔴 Called as a tail ends, so the `end` event never names an archive the
        next poll has not yet made.
        '''
        self._index_node(self._row(job_id), step, index)

        row = self._store.one(
            "SELECT id FROM artifacts WHERE job_id = ? AND step = ? "
            'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
            "ORDER BY created_at LIMIT 1", (job_id, step, index))
        return row["id"] if row else None
