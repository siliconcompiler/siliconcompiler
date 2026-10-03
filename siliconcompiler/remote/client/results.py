'''
Bring a finished run's results home: the listing is the answer even when the bytes are not.

🔴 A listing holding only a manifest is a SUCCESSFUL run, and no kind is
guaranteed, the manifest included: an empty listing is legal.

🔴 Five states stay five sentences: absent, blocked by an agreement, ungranted,
deleted and expired.
'''

import json
import logging
import os
import sys
import tarfile
import tempfile

from typing import Any, Dict, List, Optional

from siliconcompiler import utils
from siliconcompiler.remote.client.errors import RemoteError, clean
from siliconcompiler.utils.units import format_binary
from siliconcompiler.utils.paths import jobdir, workdir

__all__ = ["Results", "REMOTE_JOB_LOG", "REMOTE_STAGING_LOG", "JOB_FILE", "record_job",
           "recorded_job"]


logger = logging.getLogger(__name__)


# Which job a directory's results came from, written by this client: never read
# from a manifest, which the server wrote.
JOB_FILE = "sc_remote_job.json"


def record_job(directory: str, job_id: str) -> None:
    '''Record the job ``directory``'s results came from.'''
    from siliconcompiler.remote.client.credentials import _write_atomic

    os.makedirs(directory, exist_ok=True)
    # The mode `open()` would give it: a job id is no secret.
    _write_atomic(os.path.join(directory, JOB_FILE),
                  json.dumps({"job_id": job_id}).encode(), mode=0o666)


def recorded_job(directory: str) -> Optional[str]:
    '''The job ``directory``'s results came from, as recorded, or None.'''
    try:
        with open(os.path.join(directory, JOB_FILE)) as f:
            job_id = json.load(f).get("job_id")
    except (OSError, ValueError, AttributeError):
        return None
    return job_id if isinstance(job_id, str) and job_id else None


# Kinds that arrive as a gzipped tar and expand in place. An unknown kind is
# left alone, not refused: this client is older than the server.
_ARCHIVES = ("node", "outputs", "reports", "final", "logs")

# Never taken, never reported as left behind: `input` is what went in, and
# `diagnostics` is the operators' record (surface D295).
_NOT_TAKEN = ("input", "diagnostics")


# 🔴 Not `job.log`, which this process still has OPEN: downloading onto it
# truncates it. ⚠️ Nor `job.<x>.log`, a pattern SiliconCompiler rotates and prunes.
REMOTE_JOB_LOG = "remote-job.log"

# The server's record of create to dispatch (surface D295).
REMOTE_STAGING_LOG = "remote-staging.log"


class Results:
    '''One job's output, as far as this caller can have it.'''

    def __init__(self, project, client):
        self.project = project
        self.client = client
        self.logger = project.logger.getChild("remote")

        self._fetched: set = set()
        self._taken_nodes: set = set()
        self._landed = 0

        # Set only once the server's copy lands: until then the file at that
        # path is the pre-run upload, which must not be folded back in.
        self._job_manifest = None

        # `False`: not looked up yet; `None`: this server publishes none.
        self._ceiling: Any = False

        self._titles = None

    ######################################################################
    # What not to pull
    ######################################################################

    def _ours(self, items) -> List[Dict[str, Any]]:
        '''🔴 The rows for this job's flow: a row naming any other node, `..`
        included, is ignored, so nothing writes outside the job directory.'''
        from siliconcompiler.flowgraph import Flowgraph

        try:
            nodes = set(self.project.get_flow().get_nodes())
        except Exception:                                        # noqa: BLE001
            nodes = set()
        kept = []
        for item in [item for item in items or [] if item.get("kind") not in _NOT_TAKEN]:
            step, index = item.get("step"), item.get("index")
            if step is None and index is None:
                kept.append(item)
                continue
            try:
                Flowgraph.check_node_name(step, index)
            except (ValueError, TypeError):
                logger.warning(f"ignoring a listed {clean(str(item.get('kind')))} for a "
                               "node name that is not one")
                continue
            if (step, index) in nodes:
                kept.append(item)
            else:
                logger.debug(f"ignoring a listed object for {step}/{index}, not in this flow")
        return kept

    @property
    def ceiling(self):
        '''The largest single object this server will hand this account, or None.

        🔴 The server enforces it; knowing it turns forty refusals into one
        sentence. Read from `GET /v1/me`, not `GET /v1`: it can differ per account.
        '''
        if self._ceiling is False:
            self._ceiling = None
            try:
                limits = (self.client.me() or {}).get("limits") or {}
                self._ceiling = limits.get("max_download_bytes")
            except Exception as e:                               # noqa: BLE001
                # The server still refuses; each oversized object is reported alone.
                logger.debug(f"no download ceiling: {e}")
        return self._ceiling

    def _oversized(self, item: Dict[str, Any]) -> bool:
        ceiling = self.ceiling
        if not ceiling or not item.get("fetchable"):
            return False
        return (item.get("size_bytes") or 0) > ceiling

    def _report_oversized(self, items: List[Dict[str, Any]]) -> None:
        '''One line, naming what was left and how to get it: ⚠️ not one per object.'''
        if not items:
            return

        total = sum(item.get("size_bytes") or 0 for item in items)
        names = ", ".join(sorted(self._name(item) for item in items)[:6])
        if len(items) > 6:
            names += ", ..."

        left = format_binary(total, "B", digits=1, show_unit=True, compact=True, default="—")
        ceiling = format_binary(self.ceiling, "B", digits=1, show_unit=True, compact=True,
                                default="—")
        self.logger.warning(
            f"{len(items)} object(s) were left on the server ({left}), "
            f"each larger than the {ceiling} this account may "
            f"download over the API: {names}. The web portal is the way to "
            "get them -- sc-remote -portal opens it.")

    ######################################################################
    # During the run
    ######################################################################

    def take(self, job_id: str, job: Dict[str, Any]) -> int:
        '''Fetch what each node left as it finishes, one listing per poll.

        🔴 Not at the end: each node's manifest keeps the local record and the
        dashboard current. By the same rule as the final sweep: the node archive
        where fetchable, else its log, reports and manifest each on its own.
        '''
        done = {(node.get("step"), node.get("index"))
                for node in job.get("nodes") or []
                if node.get("terminal") and node.get("step")
                and node.get("index") is not None}

        fresh = done - self._taken_nodes
        if not fresh:
            return 0

        try:
            # The endpoint's largest page: a wide flow lists four objects per node.
            listed = self._ours(self.client.artifacts(job_id, limit=200))
        except Exception as e:                                   # noqa: BLE001
            # The final sweep asks again.
            logger.debug(f"could not list node results yet: {e}")
            return 0

        # 🔴 Oversized dropped BEFORE `_worth_fetching` (see `fetch`); reported
        # only by the final sweep. ⚠️ Node-bound only: the job's objects are not
        # final until the run is.
        listed = [item for item in listed if not self._oversized(item)]
        items = [item for item in _worth_fetching(listed)
                 if item.get("step") is not None]

        landed = 0
        for item in items:
            key = (item.get("step"), item.get("index"))
            if key not in fresh or not item.get("fetchable"):
                continue
            if item["id"] in self._fetched:
                continue

            try:
                got = self._retrieve(job_id, item)
                landed += got
                self._fetched.add(item["id"])
                self._landed += 1 if got else 0
            except Exception as e:                               # noqa: BLE001
                # The final sweep tries again.
                logger.debug(f"{self._name(item)} not taken yet: {e}")

        # 🔴 Recorded as LOOKED FOR, not found: a skipped node never has an
        # archive and would relist every poll. The final sweep catches late ones.
        self._taken_nodes |= fresh

        if landed:
            self._replay()

        return landed

    def fetch(self, job_id: str) -> int:
        '''Retrieve everything fetchable and say what was not; returns how many landed.'''
        items = self._ours(self.client.artifacts(job_id))

        if not items:
            self.logger.warning(
                "This server kept nothing from this run. The job's own record "
                "is all there is, and it is not an error.")
            return 0

        # 🔴 BEFORE `_worth_fetching`: an archive not being fetched must not
        # displace the node's log and reports inside it.
        oversized = [item for item in items if self._oversized(item)]
        items = _worth_fetching([item for item in items if not self._oversized(item)])

        landed = 0
        withheld = []
        for item in items:
            if item.get("id") in self._fetched:
                continue
            if not item.get("fetchable"):
                withheld.append(item)
                continue
            try:
                got = self._retrieve(job_id, item)
                landed += got
                self._fetched.add(item["id"])
                self._landed += 1 if got else 0
            except Exception as e:                               # noqa: BLE001
                # One object failing does not abort the others.
                self.logger.error(f"{self._name(item)}: {e}")

        self._report_withheld(withheld)
        self._report_oversized(oversized)
        # 🔴 An unlisted kind is not kept here: no error, no retry. Said only
        # for the manifest, the one a user looks for.
        if not any(item.get("kind") == "manifest" for item in items):
            self.logger.info(
                "No manifest was kept for this run, so the metrics and the "
                "per-node record are not available. This server does not keep "
                "those; it is not an error and there is nothing to retry.")
        self._replay()

        # The whole run's count: "2 of 26" would read like 24 failures.
        self.logger.info(f"Retrieved {self._landed} objects")
        return landed

    ######################################################################
    # The five sentences
    ######################################################################

    def _report_withheld(self, items: List[Dict[str, Any]]) -> None:
        '''One line per reason, ⚠️ not one per object, so the one that differs is read.'''
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            grouped.setdefault(self._why(item, many=True), []).append(item)

        for why, same in grouped.items():
            if len(same) == 1:
                self.logger.warning(f"{self._name(same[0])}: {self._why(same[0])}")
                continue

            counts: Dict[str, int] = {}
            for item in same:
                kind = item.get("kind", "artifact")
                counts[kind] = counts.get(kind, 0) + 1
            kinds = ", ".join(f"{kind} x{count}" for kind, count in counts.items())
            self.logger.warning(f"{len(same)} objects ({kinds}): {why}")

        self._offer_requests(items)

    def _offer_requests(self, items: List[Dict[str, Any]]) -> None:
        '''*Ask*, at a terminal: open each approval request's page on a yes.'''
        from siliconcompiler.remote.client import _ask

        ask = [item for item in items if item.get("can_request_access") is True
               and not item.get("access_requested_at") and item.get("id")]
        if not ask or not sys.stdin.isatty() or not self.client.may_open():
            return
        if _ask(f"Open the approval request for {len(ask)} of them in a browser? "
                "[y/N] ").strip().lower() not in ("y", "yes"):
            return
        for item in ask:
            self.client.open_page(f"the approval request for {self._name(item)}",
                                  artifact_id=item["id"])

    def _why(self, item: Dict[str, Any], many: bool = False) -> str:
        '''The reason alone, for one object or for several with the same one.'''
        this = "these" if many else "this"

        if item.get("deleted_at"):
            day = _day(item["deleted_at"])

            # 🔴 `deleted_at` covers retention too; only `deleted_cause` tells
            # them apart, and anything but `expired`, unknown included, is somebody's.
            if item.get("deleted_cause") == "expired":
                return (f"aged out on {day}. Retention on this server "
                        "passed for that kind and the bytes were reclaimed.")

            # Prose a person wrote: repeated, never interpreted.
            reason = item.get("deleted_reason")
            if reason:
                return f"deleted on {day} -- {reason}."
            return f"deleted on {day}."

        # 🔴 *Sign*: granted, but agreements stand in the way.
        blocked = item.get("blocked_by")
        if isinstance(blocked, list) and blocked:
            from siliconcompiler.remote.client.errors import blocked_lines

            return ("held back by agreements you have not signed: "
                    + "; ".join(blocked_lines(blocked, self._terms_titles())) + ".")

        # *Ask*: an approval is all that is missing.
        if item.get("can_request_access") is True:
            asked = item.get("access_requested_at")
            if asked:
                return f"access requested on {_day(asked)}; it has not been decided yet."
            return "it needs an approval. Ask for access on its page in this server's portal."

        return (f"you may not have {this}. Neither an agreement nor an approval "
                "is named, so it is not something asking would change.")

    def _terms_titles(self) -> Dict[str, str]:
        '''Each terms document's title, by id, from GET /v1/me -- read once.'''
        if self._titles is None:
            try:
                terms = self.client.me().get("terms") or []
            except RemoteError:
                terms = []
            self._titles = {entry.get("id"): entry.get("title")
                            for entry in terms if isinstance(entry, dict)
                            and entry.get("id") and entry.get("title")}
        return self._titles

    ######################################################################
    # Putting it back
    ######################################################################

    def _retrieve(self, job_id: str, item: Dict[str, Any]) -> int:
        kind = item.get("kind")
        step, index = item.get("step"), item.get("index")

        if step is None or index is None:
            if kind == "manifest":
                target = os.path.join(jobdir(self.project), f"{self.project.name}.pkg.json")
                self._gunzip(job_id, item, target)
                self._job_manifest = target
                return 1
            if kind == "logs":
                self._gunzip(job_id, item, os.path.join(jobdir(self.project), REMOTE_JOB_LOG))
                return 1
            if kind == "staging":
                self._gunzip(job_id, item,
                             os.path.join(jobdir(self.project), REMOTE_STAGING_LOG))
                return 1
            logger.debug(f"nothing to do with a job-level {kind}")
            return 0

        into = workdir(self.project, step=step, index=index)
        os.makedirs(into, exist_ok=True)

        if kind == "manifest":
            # Where the node wrote it, and the replay looks.
            outputs = os.path.join(into, "outputs")
            os.makedirs(outputs, exist_ok=True)
            self._gunzip(job_id, item, os.path.join(outputs, f"{self.project.name}.pkg.json"))
        elif kind in _ARCHIVES:
            self._unpack(job_id, item, into)
        else:
            logger.debug(f"no local home for a {kind} artifact")
            return 0

        record_job(into, job_id)
        return 1

    def _download(self, job_id: str, item: Dict[str, Any], tmpdir: str) -> str:
        '''The bytes, checked against the listing's `size_bytes` and `digest`
        before anything uses them; a mismatch is discarded.'''
        from siliconcompiler.utils import file_digest

        path = os.path.join(tmpdir, "artifact")
        self.client.fetch_artifact(job_id, item["id"], path)

        expected = item.get("digest")
        if (item.get("size_bytes") is not None and os.path.getsize(path) != item["size_bytes"]) \
                or (expected and f"sha256:{file_digest(path).hexdigest()}" != expected):
            os.remove(path)
            raise RemoteError(f"{self._name(item)} did not match its listed size and "
                              "digest, and was discarded")
        return path

    def _gunzip(self, job_id: str, item: Dict[str, Any], dest: str) -> None:
        '''Download and gunzip a single-file artifact to ``dest``.'''
        import gzip
        import shutil

        with tempfile.TemporaryDirectory(prefix="sc-artifact-") as tmpdir:
            path = self._download(job_id, item, tmpdir)
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            partial = f"{dest}.part"
            with gzip.open(path, "rb") as source, open(partial, "wb") as out:
                shutil.copyfileobj(source, out)
            os.replace(partial, dest)

    def _unpack(self, job_id: str, item: Dict[str, Any], into: str) -> None:
        '''Expand one archive into the node's working directory.

        Links may point into a sibling node, so members are rebased under
        ``<step>/<index>/`` and extracted against the job directory: the data
        filter bounds links by the job, and nothing lands outside it.'''
        root = jobdir(self.project)
        prefix = os.path.relpath(into, root).replace(os.sep, "/")
        with tempfile.TemporaryDirectory(prefix="sc-artifact-") as tmpdir:
            path = self._download(job_id, item, tmpdir)
            with tarfile.open(path, "r:*") as tar:
                members = []
                for member in tar.getmembers():
                    name = member.name
                    while name.startswith("./"):
                        name = name[2:]
                    member.name = prefix if name in ("", ".") else f"{prefix}/{name}"
                    if member.islnk():
                        target = member.linkname
                        while target.startswith("./"):
                            target = target[2:]
                        member.linkname = f"{prefix}/{target}"
                    members.append(member)
                utils.extract_safely(tar, root, members=members)

    def _replay(self) -> None:
        '''Fold the retrieved manifests' record and metrics into this project, for `summary()`.

        🔴 Nothing a job returns is imported or executed (surface §6): only
        `_folded` values, for nodes the job ran.
        '''
        from siliconcompiler.remote.runflow import runtime_nodes

        try:
            nodes = runtime_nodes(self.project)
        except Exception:                                        # noqa: BLE001
            return
        ran = set(nodes)

        for path in self._manifests(nodes):
            try:
                self._fold_in_journal(path, ran)
            except Exception as e:                               # noqa: BLE001
                logger.debug(f"could not replay {path}: {e}")

        if self._job_manifest and os.path.isfile(self._job_manifest):
            try:
                self._fold_in_final(self._job_manifest, ran)
            except Exception as e:                               # noqa: BLE001
                logger.debug(f"could not read {self._job_manifest}: {e}")

    def _fold_in_journal(self, path: str, ran) -> None:
        '''A node manifest's journal, read as data, through `_folded`.'''
        with open(path, encoding="utf-8") as f:
            journal = json.load(f).get("__journal__") or []
        for action in journal:
            if not isinstance(action, dict) or action.get("type") not in ("set", "add"):
                continue
            if action.get("field") not in (None, "value"):
                continue
            key = tuple(action.get("key") or ())
            step, index = action.get("step"), action.get("index")
            if not _folded(key, step, index, ran):
                continue
            write = self.project.set if action["type"] == "set" else self.project.add
            write(*key, action.get("value"), step=step, index=index)

    def _fold_in_final(self, path: str, ran) -> None:
        '''Copy the run's per-node record and metrics out of the job manifest.

        🔴 It has no journal, only final state: node-bound `record` and `metric`
        values only, since a global value is the server's setting. Imports nothing.
        '''
        from siliconcompiler.remote import manifests

        final = manifests.read(path)
        for group in ("record", "metric"):
            for key in final.getkeys(group):
                param = final.get(group, key, field=None)
                for value, step, index in param.getvalues(return_defvalue=False):
                    if value is None or not _folded((group, key), step, index, ran):
                        continue
                    self.project.set(group, key, value, step=step, index=index)

    def fetch_node(self, job_id: str, step: str, index: str) -> int:
        '''Fetch one node of the job a run continued from; returns how many landed.'''
        items = [item for item in self._ours(self.client.artifacts(job_id))
                 if item.get("step") == step and item.get("index") == index]
        landed = 0
        for item in _worth_fetching([item for item in items if not self._oversized(item)]):
            if not item.get("fetchable"):
                continue
            try:
                landed += self._retrieve(job_id, item)
            except Exception as e:                               # noqa: BLE001
                self.logger.error(f"{self._name(item)}: {e}")
        return landed

    def _manifests(self, nodes) -> List[str]:
        '''Every node manifest on disk, whichever object brought it.'''
        found = []
        for step, index in nodes:
            path = os.path.join(workdir(self.project, step=step, index=index),
                                "outputs", f"{self.project.name}.pkg.json")
            if os.path.isfile(path):
                found.append(path)
        return found

    @staticmethod
    def _name(item: Dict[str, Any]) -> str:
        kind = item.get("kind", "artifact")
        step, index = item.get("step"), item.get("index")
        if step is None:
            return kind
        return f"{kind} for {step}/{index}"


def _worth_fetching(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    '''Drop what a fetchable node archive already contains.

    🔴 A `node` artifact IS its node's results, so the objects inside it would
    download twice. Job-level objects are always kept, and a refused archive
    displaces nothing.
    '''
    covered = {(item.get("step"), item.get("index")) for item in items
               if item.get("kind") == "node" and item.get("fetchable")}
    if not covered:
        return items

    return [item for item in items
            if item.get("kind") in ("node", "final")
            or item.get("step") is None
            or not item.get("fetchable")
            or (item.get("step"), item.get("index")) not in covered]


def _folded(key, step, index, ran) -> bool:
    '''Whether a returned value is folded in: a node-bound record or metric of a
    node the job ran, never the job id.'''
    return (len(key) >= 2 and key[0] in ("record", "metric")
            and key != ("record", "remoteid")
            and step is not None and index is not None and (step, index) in ran)


def _day(timestamp: str) -> str:
    '''The date out of an RFC 3339 instant.'''
    return (timestamp or "")[:10] or "an unknown date"
