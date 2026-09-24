'''
Bringing a finished run home.

🔴 **This is a different model from the one it replaces, not a tolerance check
bolted onto it.** The old client fetched one ``result.tar.gz`` per node and had
a single message -- *"Could not fetch results for node"* -- for every way that
could go wrong. Under ``v1`` results are a listing, and the listing is the
answer even when the bytes are not there.

Two rules follow from that and they are the whole of this file:

🔴 **A listing holding only a manifest is a SUCCESSFUL run.** The manifest
carries the record -- node states, metrics, tool versions -- so *what happened*
is answerable with nothing else on disk. And no kind is guaranteed, the manifest
included: an empty listing is a legal answer, and a client that requires one
kind to be present has the same bug one kind further along.

🔴 **Five states stay five sentences.** Absent, blocked by an agreement,
ungranted, deleted and expired are five different things to tell a person, and
collapsing them answers *where did my results go* with the one sentence that
fits none of the cases.

⚠️ **``deleted_at`` alone does not say which of the last two it is.** A server's
reaper sets it when retention lapses -- it has to, because ``fetchable`` asks
first whether the bytes are there -- so the column covers *the system did what
it said it would* as well as *somebody removed this*. ``deleted_reason`` is what
tells them apart, and this client repeats it rather than guessing.
'''

import logging
import os
import tarfile
import tempfile

from typing import Any, Dict, List

from siliconcompiler import utils
from siliconcompiler.remote.units import size
from siliconcompiler.schema import Journal
from siliconcompiler.utils.paths import jobdir, workdir

__all__ = ["Results", "REMOTE_JOB_LOG"]


logger = logging.getLogger(__name__)


# Kinds that arrive as a gzipped tar and expand in place. A kind this client
# does not recognise is listed and left alone rather than refused: the set is
# closed and published, so an unknown one means this client is older than the
# server.
_ARCHIVES = ("node", "outputs", "reports")

# Where the run's own log lands. It belongs to no node, so it goes beside them
# in the job directory.
#
# 🔴 **Not `job.log`, which is the local run's own file and is OPEN.** A remote
# run is still a `Scheduler` run -- that is what makes a flow that does not
# resolve fail here rather than on somebody else's machine -- so `job.log` is
# being written by a live handler for the whole of it, and downloading onto it
# truncates a file this process is still appending to.
#
# ⚠️ And not `job.<something>.log` either: that is the pattern SiliconCompiler
# rotates its own backups under, and it prunes all but the most recent few.
REMOTE_JOB_LOG = "remote-job.log"


class Results:
    '''One job's output, as far as this caller can have it.'''

    def __init__(self, project, client):
        self.project = project
        self.client = client
        self.logger = project.logger.getChild("remote")

        # What has already landed, so the sweep at the end of the run does not
        # fetch it a second time.
        self._fetched: set = set()
        self._taken_nodes: set = set()
        self._landed = 0

        # The server's download ceiling, read once and remembered. `False`
        # means not looked up yet; `None` means this server publishes none.
        self._ceiling: Any = False

    ######################################################################
    # What not to pull
    ######################################################################

    @property
    def ceiling(self):
        '''The largest single object this server will hand over.

        🔴 **The server enforces it; reading it here is only so the refusal
        does not have to happen.** An over-ceiling fetch is answered
        `limit-exceeded` naming `max_download_bytes`, so a client that ignores
        this number does not get more -- it gets the same results plus a
        failed request per oversized object. Knowing the number in advance is
        what turns forty refusals into one sentence.

        🔴 The server's number and not the client's. A deployment knows what
        its link and its disks are for; a client picking its own threshold
        means every client picks a different one and the operator can set no
        policy at all.

        🔴 **Read from `GET /v1/me` and not from `GET /v1`, because it can
        differ per account.** `GET /v1` carries no credential, so it cannot
        vary by caller -- it publishes the deployment's default and nothing
        more. The ceiling that applies to THIS caller is in the identity block,
        which is the only place a per-user override can be seen.

        A server that publishes neither leaves this `None`, and everything is
        fetched exactly as before.
        '''
        if self._ceiling is False:
            self._ceiling = None
            try:
                limits = (self.client.me() or {}).get("limits") or {}
                self._ceiling = limits.get("max_download_bytes")
            except Exception as e:                               # noqa: BLE001
                # Not knowing it is not the same as there not being one: the
                # server still refuses. What is lost is the single tidy
                # sentence, and each oversized object is reported on its own.
                logger.debug(f"no download ceiling: {e}")
        return self._ceiling

    def _oversized(self, item: Dict[str, Any]) -> bool:
        ceiling = self.ceiling
        if not ceiling or not item.get("fetchable"):
            return False
        return (item.get("size_bytes") or 0) > ceiling

    def _report_oversized(self, items: List[Dict[str, Any]]) -> None:
        '''One line, naming what was left and how to get it.

        ⚠️ Not a warning per object. A wide flow can leave forty of them, and
        forty lines saying the same thing is how somebody stops reading the
        ones that matter.
        '''
        if not items:
            return

        total = sum(item.get("size_bytes") or 0 for item in items)
        names = ", ".join(sorted(self._name(item) for item in items)[:6])
        if len(items) > 6:
            names += ", ..."

        self.logger.warning(
            f"{len(items)} object(s) were left on the server ({size(total)}), "
            f"each larger than the {size(self.ceiling)} this account may "
            f"download over the API: {names}. The web portal is the way to "
            "get them -- sc-remote -portal opens it.")

    ######################################################################
    # During the run
    ######################################################################

    def take(self, job_id: str, job: Dict[str, Any]) -> int:
        '''Fetch what each node left, as that node finishes.

        🔴 Not at the end of the run. A node's archive carries its manifest,
        so taking it as it appears is what keeps the local record -- metrics,
        tool versions, node states -- current while the rest of the flow is
        still going. It is also what lets the dashboard show a finished node's
        real runtime rather than a timer that never stops.

        One listing per poll in which something finished, filtered to the
        `node` kind, rather than one request per node: a wide flow finishes
        many nodes between two polls.
        '''
        done = {(node.get("step"), node.get("index"))
                for node in job.get("nodes") or []
                if node.get("terminal") and node.get("step")
                and node.get("index") is not None}

        fresh = done - self._taken_nodes
        if not fresh:
            return 0

        try:
            items = self.client.artifacts(job_id, kind="node")
        except Exception as e:                                   # noqa: BLE001
            # Nothing is lost by failing here: the sweep at the end asks again.
            logger.debug(f"could not list node archives yet: {e}")
            return 0

        landed = 0
        for item in items:
            key = (item.get("step"), item.get("index"))
            if key not in fresh or not item.get("fetchable"):
                continue
            if item["id"] in self._fetched:
                continue
            if self._oversized(item):
                # Said once, by the sweep at the end. Here it would be said
                # again on every poll that found this node finished.
                continue

            try:
                landed += self._retrieve(job_id, item)
                self._fetched.add(item["id"])
                self._landed += 1
            except Exception as e:                               # noqa: BLE001
                # It will be tried again by the sweep at the end of the run.
                logger.debug(f"{self._name(item)} not taken yet: {e}")

        # 🔴 Every node that had just finished has now been LOOKED FOR, and
        # that is what is recorded -- not which ones were found.
        #
        # Recording only the ones that were found meant a terminal node with no
        # archive stayed outstanding for ever, and a node the run skipped never
        # has one: it produces no working directory, so there is nothing to
        # archive. Three skipped nodes were enough to make this listing happen
        # on every single poll for the length of the run, per client. On a
        # server with a few hundred of those, that is the whole cost of
        # watching a job.
        #
        # Anything that appears late is picked up by the sweep at the end,
        # which is what that sweep is for.
        self._taken_nodes |= fresh

        if landed:
            self._replay()

        return landed

    def fetch(self, job_id: str) -> int:
        '''Retrieve everything fetchable and say what was not. Returns the
        number of objects that landed.'''
        items = self.client.artifacts(job_id)

        if not items:
            # A legal answer, and three deployments reach it by different
            # routes -- one that indexes the manifest and stores no bulk
            # output, one whose pipeline does not run here at all, and one
            # where retention has taken everything.
            self.logger.warning(
                "This server kept nothing from this run. The job's own record "
                "is all there is, and it is not an error.")
            return 0

        # 🔴 Taken out BEFORE `_worth_fetching`, and the order is the point: a
        # node archive displaces the objects inside it only because fetching it
        # gets you them. One that is not being fetched displaces nothing, so
        # the node's log and reports still come back -- which is the case this
        # ceiling exists to produce.
        oversized = [item for item in items if self._oversized(item)]
        items = _worth_fetching([item for item in items if not self._oversized(item)])

        landed = 0
        for item in items:
            if item.get("id") in self._fetched:
                # Already taken while the run was going.
                continue
            if not item.get("fetchable"):
                self.logger.warning(self._explain(item))
                continue
            try:
                landed += self._retrieve(job_id, item)
                self._fetched.add(item["id"])
                self._landed += 1
            except Exception as e:                               # noqa: BLE001
                # One object failing does not abort the others: a node whose
                # bytes went missing must not cost the caller the rest of the
                # run.
                self.logger.error(f"{self._name(item)}: {e}")

        self._report_oversized(oversized)
        self._report_absent(items)
        self._replay()

        # Counted across the whole run, not just this sweep: most of it
        # arrived as the nodes finished, and "2 of 26" reads like 24 failures.
        self.logger.info(f"Retrieved {self._landed} objects")
        return landed

    ######################################################################
    # The five sentences
    ######################################################################

    def _explain(self, item: Dict[str, Any]) -> str:
        '''Why this object is not coming, in the words that fit its case.'''
        name = self._name(item)

        # 🔴 Checked before the expiry, and the order is the point: an object
        # whose bytes are gone is also, usually, past its retention, and the
        # useful sentence is the one that says why they went.
        if item.get("deleted_at"):
            day = _day(item["deleted_at"])
            reason = item.get("deleted_reason")
            # Repeated, never interpreted. The reason is prose a deployment
            # chose and this client has no vocabulary to match it against --
            # which is the point: a server that grows a new one is understood
            # by a client that shipped before it.
            if reason:
                return f"{name}: gone on {day} -- {reason}."
            return f"{name}: deleted on {day}."

        blocked = item.get("blocked_by")
        if blocked:
            where = item.get("access_request_url")
            ask = f" Ask for access at {where}" if where else ""
            return (f"{name}: held back by an agreement you have not accepted "
                    f"({blocked}).{ask}")

        expires = item.get("expires_at")
        if expires and expires <= _now():
            return (f"{name}: aged out on {_day(expires)}. Retention on this "
                    "server has passed for that kind.")

        return (f"{name}: you may not have this. No agreement is named, so it "
                "is not something asking would change.")

    def _report_absent(self, items: List[Dict[str, Any]]) -> None:
        '''A kind that is not in the listing was never indexed here.

        🔴 Not an error and not a retry -- it is this deployment saying it does
        not keep those. Only worth a line for the manifest, because that is the
        one a user is most likely to be looking for.
        '''
        if not any(item.get("kind") == "manifest" for item in items):
            self.logger.info(
                "No manifest was kept for this run, so the metrics and the "
                "per-node record are not available. This server does not keep "
                "those; it is not an error and there is nothing to retry.")

    ######################################################################
    # Putting it back
    ######################################################################

    def _retrieve(self, job_id: str, item: Dict[str, Any]) -> int:
        kind = item.get("kind")

        if kind == "manifest":
            target = os.path.join(jobdir(self.project),
                                  f"{self.project.name}.pkg.json")
            self.client.fetch_artifact(job_id, item["id"], target)
            return 1

        step, index = item.get("step"), item.get("index")

        if step is None or index is None:
            if kind == "logs":
                self.client.fetch_artifact(
                    job_id, item["id"],
                    os.path.join(jobdir(self.project), REMOTE_JOB_LOG))
                return 1
            logger.debug(f"nothing to do with a job-level {kind}")
            return 0

        into = workdir(self.project, step=step, index=index)
        os.makedirs(into, exist_ok=True)

        if kind == "logs":
            self.client.fetch_artifact(
                job_id, item["id"], os.path.join(into, f"sc_{step}_{index}.log"))
            return 1

        if kind in _ARCHIVES:
            self._unpack(job_id, item, into)
            return 1

        logger.debug(f"no local home for a {kind} artifact")
        return 0

    def _unpack(self, job_id: str, item: Dict[str, Any], into: str) -> None:
        '''Expand one archive into the node's working directory.

        Relative to that directory, which is why the contract has no
        per-artifact path: the client knows the step, the index and the kind,
        and that is enough to put it back where it came from.
        '''
        with tempfile.TemporaryDirectory(prefix="sc-artifact-") as tmpdir:
            downloaded = os.path.join(tmpdir, "artifact.tar.gz")
            self.client.fetch_artifact(job_id, item["id"], downloaded)

            with tarfile.open(downloaded, "r:*") as tar:
                # The same extraction filter the rest of SiliconCompiler uses.
                # These bytes came from a server this machine chose to trust,
                # which is a reason to check them rather than a reason not to.
                tar.extractall(path=into, **utils.tar_extract_kwargs())

    def _replay(self) -> None:
        '''Fold the retrieved manifests back into this project.

        What makes `summary()` work after a remote run: the record, the metrics
        and the tool versions are in the manifests, not in anything the poll
        loop saw.
        '''
        for path in self._manifests():
            try:
                Journal.replay_file(self.project, path)
            except Exception as e:                               # noqa: BLE001
                # A manifest this client cannot read is one node's detail, not
                # the run. It has already been reported as a state.
                logger.debug(f"could not replay {path}: {e}")

    def _manifests(self) -> List[str]:
        found = []

        job_manifest = os.path.join(jobdir(self.project),
                                    f"{self.project.name}.pkg.json")
        if os.path.isfile(job_manifest):
            found.append(job_manifest)

        from siliconcompiler.remote.server.runspec import runtime_nodes

        try:
            nodes = runtime_nodes(self.project)
        except Exception:                                        # noqa: BLE001
            return found

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
    '''Drop what a node archive already contains.

    🔴 A `node` artifact IS that node's results, so fetching it and then
    fetching the objects inside it downloads everything twice. It covers only
    its own node -- it is always bound to a step and an index, and there is no
    job-level one -- so a node whose archive is missing or refused keeps every
    object it has.

    The manifest is always kept: it is small, it is what the record is replayed
    from, and a client that relied on finding one inside the node archive would
    break on the deployment that indexes a manifest and no bulk output at all.

    Only a FETCHABLE node archive displaces anything. One that is present and
    refused -- withheld, or over this account's download ceiling -- leaves
    every other object exactly as it was, and the caller is told why it could
    not have it.
    '''
    covered = {(item.get("step"), item.get("index")) for item in items
               if item.get("kind") == "node" and item.get("fetchable")}
    if not covered:
        return items

    return [item for item in items
            if item.get("kind") in ("node", "manifest")
            or not item.get("fetchable")
            or (item.get("step"), item.get("index")) not in covered]


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _day(timestamp: str) -> str:
    '''The date out of an RFC 3339 instant. A person reads a day, not a
    millisecond.'''
    return (timestamp or "")[:10] or "an unknown date"
