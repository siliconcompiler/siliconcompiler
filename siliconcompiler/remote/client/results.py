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
fits none of the cases. ⚠️ **Never say *expired* for a ``deleted_at``**:
retention lapsing is the system doing what it said, a deletion is somebody
deciding.
'''

import logging
import os
import tarfile
import tempfile

from typing import Any, Dict, List

from siliconcompiler import utils
from siliconcompiler.schema import Journal
from siliconcompiler.utils.paths import jobdir, workdir

__all__ = ["Results"]


logger = logging.getLogger(__name__)


# What this client knows how to put back on disk. A kind it does not recognise
# is listed and left alone rather than refused: the set is closed and published,
# so an unknown one means this client is older than the server.
_ARCHIVES = ("outputs", "reports")


class Results:
    '''One job's output, as far as this caller can have it.'''

    def __init__(self, project, client):
        self.project = project
        self.client = client
        self.logger = project.logger.getChild("remote")

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

        landed = 0
        for item in items:
            if not item.get("fetchable"):
                self.logger.warning(self._explain(item))
                continue
            try:
                landed += self._retrieve(job_id, item)
            except Exception as e:                               # noqa: BLE001
                # One object failing does not abort the others: a node whose
                # bytes went missing must not cost the caller the rest of the
                # run.
                self.logger.error(f"{self._name(item)}: {e}")

        self._report_absent(items)
        self._replay()

        self.logger.info(f"Retrieved {landed} of {len(items)} objects")
        return landed

    ######################################################################
    # The five sentences
    ######################################################################

    def _explain(self, item: Dict[str, Any]) -> str:
        '''Why this object is not coming, in the words that fit its case.'''
        name = self._name(item)

        # 🔴 Checked before the expiry, and the order is the point: a deleted
        # object may also be past its retention, and saying it expired would
        # tell a user the system aged out data that somebody removed.
        if item.get("deleted_at"):
            return f"{name}: deleted on {_day(item['deleted_at'])}."

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


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _day(timestamp: str) -> str:
    '''The date out of an RFC 3339 instant. A person reads a day, not a
    millisecond.'''
    return (timestamp or "")[:10] or "an unknown date"
