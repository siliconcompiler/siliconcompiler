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
it said it would* as well as *somebody removed this*. ``deleted_cause`` is what
tells them apart -- a closed enum, ``expired`` or ``removed`` -- and
``deleted_reason`` is the prose a person wrote, which this client repeats rather
than interprets.
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


# Which job a directory's results came from, written by this client when it
# created the job or fetched them -- and never read out of a manifest, which
# the server wrote and an upload can name anything in.
JOB_FILE = "sc_remote_job.json"


def record_job(directory: str, job_id: str) -> None:
    '''Record the job ``directory``'s results came from.'''
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, JOB_FILE)
    partial = f"{path}.part"
    with open(partial, "w") as f:
        json.dump({"job_id": job_id}, f)
    os.replace(partial, path)


def recorded_job(directory: str) -> Optional[str]:
    '''The job ``directory``'s results came from, as recorded, or None.'''
    try:
        with open(os.path.join(directory, JOB_FILE)) as f:
            job_id = json.load(f).get("job_id")
    except (OSError, ValueError, AttributeError):
        return None
    return job_id if isinstance(job_id, str) and job_id else None


# Kinds that arrive as a gzipped tar and expand in place. A kind this client
# does not recognise is listed and left alone rather than refused: the set is
# closed and published, so an unknown one means this client is older than the
# server.
_ARCHIVES = ("node", "outputs", "reports", "final", "logs")

# Kinds this client never takes, and never reports as left behind. `input` is
# what went IN -- each upload, and a node's inputs -- and this machine has the
# one and takes the other as its upstream's outputs. It is there to be looked
# at, in the portal. `diagnostics` is the deployment's operators' record, never
# handed over the API (surface D295), so it is no one's to fetch from here.
_NOT_TAKEN = ("input", "diagnostics")


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

# Where the server's record of the job lands (surface D295): what it did
# between create and dispatch, never inside the run's own log.
REMOTE_STAGING_LOG = "remote-staging.log"


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

        # The job-level manifest, once it has come from the server. Until then
        # the file at that path is the one this client wrote to upload, and
        # folding THAT back in would put the pre-run record over what the
        # nodes have since said.
        self._job_manifest = None

        # The server's download ceiling, read once and remembered. `False`
        # means not looked up yet; `None` means this server publishes none.
        self._ceiling: Any = False

        # Each terms document's title by id, which names a `blocked_by`
        # entry; None until something needs one.
        self._titles = None

    ######################################################################
    # What not to pull
    ######################################################################

    def _ours(self, items) -> List[Dict[str, Any]]:
        '''🔴 The rows this job's flow has. A node-bound row naming a node the
        flow does not -- `..` included -- is ignored, so nothing a listing says
        writes outside the job's local directory.'''
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
        '''The largest single object this server will hand over.

        🔴 **The server enforces it; reading it here is only so the refusal
        does not have to happen.** An over-ceiling fetch is answered
        `download-too-large` naming `max_download_bytes`, so a client that ignores
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
        '''Fetch what each node left, as that node finishes.

        🔴 Not at the end of the run. A node's archive carries its manifest,
        so taking it as it appears is what keeps the local record -- metrics,
        tool versions, node states -- current while the rest of the flow is
        still going. It is also what lets the dashboard show a finished node's
        real runtime rather than a timer that never stops.

        One listing per poll in which something finished rather than one
        request per node: a wide flow finishes many nodes between two polls.

        🔴 **Everything of that node's that may be had, by the same rule as
        the sweep at the end.** The node archive where it is fetchable, which
        holds the node's log, reports and manifest, so none of them is fetched
        twice; and where it is not, each of those on its own -- a deployment
        that withholds archives can still hand over the log a person wants to
        read and the manifest that keeps the record current, and waiting for the
        end of the run to fetch them is waiting for no reason.
        '''
        done = {(node.get("step"), node.get("index"))
                for node in job.get("nodes") or []
                if node.get("terminal") and node.get("step")
                and node.get("index") is not None}

        fresh = done - self._taken_nodes
        if not fresh:
            return 0

        try:
            # Every kind, because what a node can be taken by is only known
            # from the listing -- at the endpoint's largest page, since a wide
            # flow lists four objects per node.
            listed = self._ours(self.client.artifacts(job_id, limit=200))
        except Exception as e:                                   # noqa: BLE001
            # Nothing is lost by failing here: the sweep at the end asks again.
            logger.debug(f"could not list node results yet: {e}")
            return 0

        # 🔴 Oversized dropped BEFORE `_worth_fetching`, as the sweep does: an
        # archive that will not be fetched must not displace the objects inside
        # it that could be. Said once, by the sweep at the end -- here it would
        # be said again on every poll that found the node finished.
        #
        # ⚠️ Node-bound only: the job's own manifest and log are the run's, and
        # are not final until it is.
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
                # Counted where something landed: a kind with no home here
                # writes nothing, and is not "retrieved".
                self._landed += 1 if got else 0
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
        items = self._ours(self.client.artifacts(job_id))

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
        withheld = []
        for item in items:
            if item.get("id") in self._fetched:
                # Already taken while the run was going.
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
                # One object failing does not abort the others: a node whose
                # bytes went missing must not cost the caller the rest of the
                # run.
                self.logger.error(f"{self._name(item)}: {e}")

        self._report_withheld(withheld)
        self._report_oversized(oversized)
        # 🔴 A kind not in the listing was never indexed here: not an error and
        # not a retry, but this deployment saying it does not keep those. Only
        # worth a line for the manifest, the one a user most likely looks for.
        if not any(item.get("kind") == "manifest" for item in items):
            self.logger.info(
                "No manifest was kept for this run, so the metrics and the "
                "per-node record are not available. This server does not keep "
                "those; it is not an error and there is nothing to retry.")
        self._replay()

        # Counted across the whole run, not just this sweep: most of it
        # arrived as the nodes finished, and "2 of 26" reads like 24 failures.
        self.logger.info(f"Retrieved {self._landed} objects")
        return landed

    ######################################################################
    # The five sentences
    ######################################################################

    def _report_withheld(self, items: List[Dict[str, Any]]) -> None:
        '''One line per reason, not one per object.

        ⚠️ The five sentences stay five, and a run where every node's archive
        is withheld for the same reason says it once. A deployment that hands
        over only the manifest withholds three objects per node, and seventy
        lines of the same sentence is how the one that differs goes unread.
        '''
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
        '''*Ask*, where a person is at a terminal: each approval request's page,
        from `POST /v1/auth/browser` with the artifact's id, opened on a yes.'''
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

        # 🔴 Checked before the expiry, and the order is the point: an object
        # whose bytes are gone is also, usually, past its retention, and the
        # useful sentence is the one that says why they went.
        if item.get("deleted_at"):
            day = _day(item["deleted_at"])

            # 🔴 `deleted_cause` is what a client branches on, and it is the
            # only member that can say the reaper took these: retention
            # lapsing ends in `deleted_at` too. Anything but `expired` -- a
            # cause this client does not know included -- is somebody
            # deciding, which is the sentence that does not under-report it.
            if item.get("deleted_cause") == "expired":
                return (f"aged out on {day}. Retention on this server "
                        "passed for that kind and the bytes were reclaimed.")

            # Repeated, never interpreted. `deleted_reason` is prose a person
            # wrote and this client has no vocabulary to match it against.
            reason = item.get("deleted_reason")
            if reason:
                return f"deleted on {day} -- {reason}."
            return f"deleted on {day}."

        # 🔴 *Sign*: every grant is held and agreements stand in the way. Each
        # document is named by its title in GET /v1/me's `terms`, or by its id.
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
            # A node's own manifest goes where the node wrote it, which is
            # where the replay looks and where a node archive would have put it.
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
        '''A single-file artifact -- a manifest, the run's log -- gzipped, as
        every artifact is.'''
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

        Paths in a node-bound tar are relative to the node, and its links may
        point into a sibling node's ``outputs/`` -- a passed-through file is a
        link to the node that produced it -- so the archive is extracted
        against the job's local directory, each member's name and each hard
        link's target under ``<step>/<index>/``: the data filter then bounds
        links by the job, not the node, and nothing lands outside the job.'''
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
        '''Fold the retrieved manifests back into this project.

        What makes `summary()` work after a remote run: the record and the
        metrics are in the manifests, not in anything the poll loop saw.

        🔴 **Nothing a job returns is imported or executed** (surface §6): a
        node's journal is replayed only through the record-and-metric filter
        the job manifest goes through, and only for the nodes the job ran.
        '''
        from siliconcompiler.remote.runflow import runtime_nodes

        try:
            ran = set(runtime_nodes(self.project))
        except Exception:                                        # noqa: BLE001
            return

        for path in self._manifests():
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

    def _fold_in_final(self, path: str, ran=None) -> None:
        '''Copy the run's per-node record and metrics out of the job manifest.

        🔴 **Not a journal replay, because the job manifest has no journal.**
        It is the run's final state, written whole when the flow ended. Only
        values bound to a node the job ran, and only in `record` and `metric`:
        a global value in it is this server's setting for the run, and a run
        that starts part-way through marks every node it did not load pending.
        Loaded with the classes already here, importing nothing it names.
        '''
        from siliconcompiler import Project
        from siliconcompiler.remote.runflow import runtime_nodes
        from siliconcompiler.schema.baseschema import known_classes_only

        if ran is None:
            ran = set(runtime_nodes(self.project))
        with known_classes_only():
            final = Project.from_manifest(filepath=path)
        for group in ("record", "metric"):
            for key in final.getkeys(group):
                param = final.get(group, key, field=None)
                for value, step, index in param.getvalues(return_defvalue=False):
                    if value is None or not _folded((group, key), step, index, ran):
                        continue
                    self.project.set(group, key, value, step=step, index=index)

    def fetch_node(self, job_id: str, step: str, index: str) -> int:
        '''What is fetchable now of one node of another job -- the job a run
        continued from, which ran it. Returns the number of objects that
        landed.'''
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

    def _manifests(self) -> List[str]:
        '''Every node manifest on disk, whichever object brought it.'''
        found = []

        from siliconcompiler.remote.runflow import runtime_nodes

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

    The JOB's manifest is always kept: it is small, it is what the record is
    replayed from, and a client that relied on finding one inside the node
    archive would break on the deployment that indexes a manifest and no bulk
    output at all. A NODE's manifest is inside that node's archive, so it goes
    with the rest.

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
            if item.get("kind") in ("node", "final")
            or item.get("step") is None
            or not item.get("fetchable")
            or (item.get("step"), item.get("index")) not in covered]


def _folded(key, step, index, ran) -> bool:
    '''Whether one value from a returned manifest is folded in: a record or a
    metric, bound to a node the job ran -- and never the job id, which comes
    from the fetch.'''
    return (len(key) >= 2 and key[0] in ("record", "metric")
            and key != ("record", "remoteid")
            and step is not None and index is not None and (step, index) in ran)


def _day(timestamp: str) -> str:
    '''The date out of an RFC 3339 instant. A person reads a day, not a
    millisecond.'''
    return (timestamp or "")[:10] or "an unknown date"
