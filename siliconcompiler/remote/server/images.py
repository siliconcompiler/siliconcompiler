'''
What a version means, in containers.

🔴 **The submitter names a version and the operator names the image.** That
inversion is the whole safety argument, and it is why this is in the server at
all: a client that could name an image would choose what executes on the
cluster, which is a supply-chain hole on a deployment anyone can reach. A client
that names ``siliconcompiler==0.38.9`` is naming *data*, which either matches a
row an operator added on purpose or does not.

🔴 **The registry is also the switch.** A deployment that registers nothing runs
jobs the way it always has, with both ``image_id`` columns NULL for the life of
every job -- and a bare Slurm cluster with no container runtime is conforming,
not degraded. What turns the other behaviour on is ``containers`` in the
deployment's config, because whether the compute nodes can run a container is
not something the API process can find out by looking.

⚠️ **``image_contents`` is declared and unverified.** Nothing here opens an
image to check that what it claims to hold is inside it, so a wrong row means a
job runs in a container without what it asked for and fails at run time rather
than at submit. Saying so is what keeps the row from being read as a guarantee.
'''

import logging
import re

from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now

__all__ = ["PRIMARY", "Requirement", "Plan", "bundle_path", "catalogue",
           "live_images", "live_software", "pinned_ref", "plan_for_job",
           "register_image", "register_software", "register_version", "resolve",
           "retire_image", "retire_software", "retire_version"]


logger = logging.getLogger("sc-server")


# The distribution every node needs, whatever else it needs: the run is a
# SiliconCompiler process before it is anything else. It is also the key
# `GET /v1`'s `software` map is REQUIRED to carry, and the version whose
# `preference` breaks a tie between two images that both fit.
PRIMARY = "siliconcompiler"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class Requirement(NamedTuple):
    '''One thing an image has to hold.

    ``version`` is None for *any live version of this software*, which is the
    ordinary case for a tool: SiliconCompiler does not know which version of
    OpenROAD it will find until the node runs, so a submit that demanded an
    exact one could never resolve. A pinned requirement comes from what the
    client declared, where naming the version is the client's whole point.
    '''
    name: str
    version: Optional[str]
    kind: str               # 'library' or 'tool' -- what a refusal calls it

    def __str__(self) -> str:
        return self.name if self.version is None else f"{self.name}=={self.version}"


class Plan(NamedTuple):
    '''Which image each part of one job runs in.

    ``refs`` carries the pinned reference for every id the plan names, because
    the store records an id and the thing that has to be pulled is a repository
    at a digest. Resolving it once here is what keeps the runner from needing a
    database connection on a compute node.
    '''
    job: Optional[str]                              # images.id, or None
    nodes: Dict[Tuple[str, str], Optional[str]]     # (step, index) -> images.id
    refs: Dict[str, str]                            # images.id -> repository@digest

    def ref(self, image_id: Optional[str]) -> Optional[str]:
        return self.refs.get(image_id) if image_id else None

    def digests(self) -> Dict[Tuple[str, str], str]:
        '''Every node that has an image, as the digest that identifies it.

        Taken back off the pinned reference rather than carried separately: the
        reference IS repository-at-digest, so a second copy could only ever
        disagree with it.
        '''
        return {node: self.refs[image].split("@", 1)[1]
                for node, image in self.nodes.items()
                if image and image in self.refs}

    def placements(self) -> Dict[Tuple[str, str], str]:
        '''Every node that has an image, as the reference to pull.

        What goes into the manifest the compute node loads. Empty on a
        deployment that runs no containers, which is what leaves every node
        running the way it always did.
        '''
        return {node: self.refs[image]
                for node, image in self.nodes.items()
                if image and image in self.refs}


######################################################################
# Reading the registry
######################################################################

def live_images(store) -> List[Dict[str, Any]]:
    '''Every image this deployment may run, with what it declares it holds.

    Two queries and the join in Python rather than one query per resolution.
    A registry is tens of rows read once per submit, and the matching rule below
    -- exact where a version was named, any live version where one was not --
    is a dynamic ``HAVING`` in SQL and four readable lines here. This is the
    most dangerous data in the schema; being able to read the rule matters more
    than the query plan.
    '''
    rows = store.all(
        "SELECT id, registry_ref, digest, note FROM images "
        "WHERE retired_at IS NULL ORDER BY registry_ref")

    contents: Dict[str, List[Tuple[str, str, int]]] = {}
    for row in store.all(
            "SELECT c.image_id, c.software_name, c.version, sv.preference "
            "FROM image_contents c "
            "JOIN software s ON s.name = c.software_name AND s.retired_at IS NULL "
            "JOIN software_versions sv "
            "  ON sv.software_name = c.software_name AND sv.version = c.version "
            " AND sv.retired_at IS NULL "
            "JOIN images i ON i.id = c.image_id AND i.retired_at IS NULL"):
        contents.setdefault(row["image_id"], []).append(
            (row["software_name"], row["version"], row["preference"]))

    return [{"id": row["id"], "registry_ref": row["registry_ref"],
             "digest": row["digest"], "note": row["note"],
             "contents": contents.get(row["id"], [])}
            for row in rows]


def catalogue(store, include_retired: bool = False) -> Dict[str, Any]:
    '''The whole registry, for an operator to look at.

    Read by the ``registry`` command and, when it arrives, by the portal's
    images screen -- which is why it is here and not in either of them.
    '''
    where = "" if include_retired else " WHERE retired_at IS NULL"

    software = [dict(row) for row in store.all(
        f"SELECT * FROM software{where} ORDER BY name")]
    versions = [dict(row) for row in store.all(
        f"SELECT * FROM software_versions{where} "
        "ORDER BY software_name, preference DESC, version")]
    images = [dict(row) for row in store.all(
        f"SELECT * FROM images{where} ORDER BY registry_ref")]

    holds: Dict[str, List[str]] = {}
    for row in store.all("SELECT * FROM image_contents "
                         "ORDER BY software_name, version"):
        holds.setdefault(row["image_id"], []).append(
            f"{row['software_name']}=={row['version']}")
    for image in images:
        image["contents"] = holds.get(image["id"], [])

    return {"software": software, "versions": versions, "images": images}


def live_software(store) -> Dict[str, List[str]]:
    '''Which distributions this deployment tracks, and at which versions.

    🔴 The test a requirement is generated by. A tool nobody registered raises
    no requirement at all, so a deployment that curates images for the framework
    and says nothing about OpenROAD is not claiming to have an OpenROAD image
    and is not refused for lacking one. Registering the name is how an operator
    takes that claim on.

    ⚠️ **Keyed on the software rather than on its versions**, so a name whose
    every version has been retired is still tracked, with an empty list. The
    claim belongs to the name: retiring a version says *not this one*, and
    retiring the software is how an operator says *not any more*. Collapsing
    the two would make withdrawing the last version silently hand every job
    back to the host it was meant to stop running on.
    '''
    tracked: Dict[str, List[str]] = {
        row["name"]: []
        for row in store.all("SELECT name FROM software WHERE retired_at IS NULL")}

    for row in store.all(
            "SELECT sv.software_name AS name, sv.version FROM software_versions sv "
            "JOIN software s ON s.name = sv.software_name "
            "WHERE s.retired_at IS NULL AND sv.retired_at IS NULL "
            "ORDER BY sv.software_name, sv.preference DESC, sv.version DESC"):
        tracked[row["name"]].append(row["version"])

    return tracked


######################################################################
# The resolution
######################################################################

def resolve(store_or_images, requirements: Sequence[Requirement]):
    '''The one image that fits, or None.

    Ranked, because more than one image may satisfy a job:

    1. 🔴 **The `preference` of its `siliconcompiler` version**, which is the
       operator's own ordering. ⚠️ Newest-wins is the tempting default and it is
       wrong: a rebuilt image is newer and not necessarily preferred.
    2. 🔴 **The fewest declared contents.** The most specific image that still
       fits wins, which is what gets an `import` node into a python-only image
       instead of a twelve-gigabyte OpenROAD one -- with no `python_only` flag
       to drift, because a python-only image is one whose contents are
       framework distributions and no tool.
    3. The registry reference, so the answer is the same every time.
    '''
    images = (store_or_images if isinstance(store_or_images, list)
              else live_images(store_or_images))

    fits = [image for image in images if _satisfies(image, requirements)]
    if not fits:
        return None

    return min(fits, key=_rank)


def _satisfies(image, requirements: Sequence[Requirement]) -> bool:
    held = image["contents"]
    for want in requirements:
        if want.version is None:
            if not any(name == want.name for name, _, _ in held):
                return False
        elif not any(name == want.name and version == want.version
                     for name, version, _ in held):
            return False
    return True


def _rank(image):
    preference = max((pref for name, _, pref in image["contents"]
                      if name == PRIMARY), default=None)
    # An image holding no framework at all ranks below every one that does,
    # rather than being excluded: it can still be the only thing that fits a
    # requirement set which never mentioned the framework.
    return (-preference if preference is not None else 1,
            len(image["contents"]), image["registry_ref"])


def plan_for_job(store, declared: Dict[str, Any],
                 node_tools: Dict[Tuple[str, str], Optional[str]]) -> Plan:
    '''Which image every node of this job runs in.

    🔴 **N images, not one.** A forty-node flow over six tools resolves six, and
    a node whose tool this deployment tracks but has no image for fails the
    WHOLE submit -- before anything runs, which is the correct direction. The
    alternative is a job that queues, dispatches, and dies on node thirty-one
    with the cluster already paid for.

    ⚠️ **Called only where the deployment runs containers**, so an empty
    registry here is a misconfiguration and not the bare-Slurm case: that one
    never reaches this function. A server whose last image was retired under it
    refuses submits rather than quietly running them on the host, which is what
    the operator turned the switch off to get.
    '''
    images = live_images(store)
    if not images:
        raise ProblemError(
            "unsatisfiable-request", resource_kind="library", resource=PRIMARY,
            detail="this server runs jobs in containers and has no image "
                   "registered")

    refs = {image["id"]: pinned_ref(image["registry_ref"], image["digest"])
            for image in images}

    tracked = live_software(store)

    # What the run's own Python process needs, and therefore what every node
    # needs: the framework, plus any library the client pinned. A name this
    # deployment does not track is not a requirement -- it is a version of
    # something nobody here curates, and `version-skew` at create is where that
    # is answered if it is answered at all.
    pinned = [Requirement(name, str(version), "library")
              for name, version in sorted((declared or {}).items())
              if name in tracked and isinstance(version, (str, int, float))]

    if PRIMARY in tracked and not any(want.name == PRIMARY for want in pinned):
        # The client named no framework version. The deployment's own
        # preference order picks, which is what `preference` is for.
        pinned.append(Requirement(PRIMARY, None, "library"))

    job_image = resolve(images, pinned)
    if job_image is None:
        raise _unsatisfiable(pinned, images)

    nodes: Dict[Tuple[str, str], Optional[str]] = {}
    for node, tool in node_tools.items():
        if not tool or tool not in tracked or any(want.name == tool for want in pinned):
            # No tool, a tool nobody registered, or one the client already
            # pinned and the job image therefore already holds.
            nodes[node] = job_image["id"]
            continue

        wants = list(pinned) + [Requirement(tool, None, "tool")]
        found = resolve(images, wants)
        if found is None:
            raise _unsatisfiable(wants, images, blame=tool)
        nodes[node] = found["id"]

    return Plan(job_image["id"], nodes, refs)


def _unsatisfiable(requirements: Sequence[Requirement], images,
                   blame: Optional[str] = None) -> ProblemError:
    '''No live image holds all of this.

    🔴 `unsatisfiable-request` rather than `entitlement-denied`: the same
    catalogue and a different question. *This deployment does not have it*, not
    *you may not use it* -- and waiting will not change it.
    '''
    culprit = next((want for want in requirements if want.name == blame),
                   requirements[-1] if requirements else None)

    return ProblemError(
        "unsatisfiable-request",
        resource_kind=culprit.kind if culprit else "tool",
        resource=str(culprit) if culprit else "unknown",
        detail=f"no image on this server holds "
               f"{', '.join(str(want) for want in requirements)}; "
               f"{len(images)} image(s) are registered")


######################################################################
# Naming an image
######################################################################

def pinned_ref(registry_ref: str, digest: str) -> str:
    '''What actually gets pulled: the repository at a digest, never a tag.

    🔴 `registry_ref` is only what a human typed. Rebuilding
    `sc-runtime:0.39.1` must not change what runs -- that takes a
    re-registration, which is a write somebody made on purpose. Two jobs a month
    apart silently running different code is the failure the stored digest
    exists to prevent, and it only prevents it if this is the string that is
    used.
    '''
    return f"{_repository(registry_ref)}@{digest}"


def bundle_path(root, digest: str):
    '''Where the OCI bundle for one image lives.

    Content-addressed and shared: two jobs naming the same digest are the same
    bytes, so they unpack once and every later run finds it. It sits beside the
    store rather than under a user's tree for the same reason -- a root
    filesystem is read-only and identical for everybody, and per-user copies of
    a twelve-gigabyte image would be the one cost this design exists to avoid.
    '''
    from pathlib import Path

    return Path(root) / digest.replace("sha256:", "")


def _repository(registry_ref: str) -> str:
    '''The reference with any tag or digest taken off.'''
    ref = registry_ref.split("@", 1)[0]

    # A colon before the last slash is a registry port, not a tag:
    # `localhost:5000/sc` has no tag at all.
    head, sep, tail = ref.rpartition(":")
    if sep and "/" not in tail:
        return head
    return ref


######################################################################
# Writing it
######################################################################

def register_software(store, name: str, display_name: str, actor: str) -> None:
    '''Declare that this deployment curates images for a distribution.

    ⚠️ It is a claim with teeth: from here on, a job whose flow needs this tool
    and finds no image holding it is refused at submit. That is the point --
    the alternative is a job that dispatches into a container without the tool
    it needs.
    '''
    with store.transaction():
        store.execute(
            "INSERT INTO software (name, display_name, added_by) VALUES (?, ?, ?) "
            "ON CONFLICT (name) DO UPDATE SET display_name = excluded.display_name, "
            "  retired_at = NULL, retired_by = NULL",
            (name, display_name or name, actor))


def register_version(store, name: str, version: str, actor: str,
                     preference: int = 0) -> None:
    '''One exact version, and exact is the rule.

    🔴 No ranges. A range needs a version-comparison grammar both ends
    implement identically -- PEP 440 against semver against whatever a tool
    calls its releases -- and two implementations disagreeing about what
    ``>=0.38`` means is a job dispatched into the wrong container. An exact
    version is a row somebody added on purpose.
    '''
    if store.one("SELECT name FROM software WHERE name = ?", (name,)) is None:
        raise ValueError(f"{name} is not registered software; add it first")

    with store.transaction():
        store.execute(
            "INSERT INTO software_versions (software_name, version, preference, added_by) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT (software_name, version) DO UPDATE SET "
            "  preference = excluded.preference, retired_at = NULL, retired_by = NULL",
            (name, version, preference, actor))


def register_image(store, registry_ref: str, digest: str,
                   contents: Sequence[Tuple[str, str]], actor: str,
                   note: Optional[str] = None) -> str:
    '''Register a container this deployment may run.

    🔴 **The most dangerous write in this schema: it chooses what code executes
    on the cluster.** Higher stakes than any read permission -- a grant decides
    who may see something, this decides what runs as the account the job maps
    to. So it takes a person, every time: ``registered_via`` is the CI path and
    it does not exist here.
    '''
    if not _DIGEST.match(digest or ""):
        raise ValueError(f"{digest!r} is not a sha256 digest")
    if not contents:
        raise ValueError("an image with no declared contents can satisfy nothing")

    for name, version in contents:
        if store.one("SELECT version FROM software_versions "
                     "WHERE software_name = ? AND version = ?",
                     (name, version)) is None:
            raise ValueError(f"{name}=={version} is not a registered version")

    existing = store.one("SELECT id FROM images WHERE digest = ?", (digest,))
    image_id = existing["id"] if existing else str(uuid7())

    with store.transaction():
        if existing:
            # Re-registering the same bytes under a new tag or a new content
            # list. The digest is the identity, so this is an update rather than
            # a second row claiming to be the same image.
            store.execute(
                "UPDATE images SET registry_ref = ?, resolved_at = ?, note = ?, "
                "  registered_by = ?, retired_at = NULL, retired_by = NULL "
                "WHERE id = ?",
                (registry_ref, now(), note, actor, image_id))
            store.execute("DELETE FROM image_contents WHERE image_id = ?", (image_id,))
        else:
            store.execute(
                "INSERT INTO images (id, registry_ref, digest, resolved_at, "
                "                    registered_by, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (image_id, registry_ref, digest, now(), actor, note))

        for name, version in contents:
            store.execute(
                "INSERT INTO image_contents (image_id, software_name, version) "
                "VALUES (?, ?, ?)", (image_id, name, version))

    logger.info(f"registered {registry_ref} as {digest}")
    return image_id


def retire_image(store, image_id: str, actor: str) -> None:
    '''Stop dispatching into it, and keep the row.

    ⚠️ Images are never deleted. A job from last year names one, and *what did
    this run in* has to stay answerable after the image stops being used.
    '''
    _retire(store, "images", "id = ?", (image_id,), actor)


def retire_version(store, name: str, version: str, actor: str) -> None:
    _retire(store, "software_versions",
            "software_name = ? AND version = ?", (name, version), actor)


def retire_software(store, name: str, actor: str) -> None:
    _retire(store, "software", "name = ?", (name,), actor)


def _retire(store, table: str, where: str, params, actor: str) -> None:
    '''Set the pair of columns every one of these tables carries.

    ``retired_at`` and ``retired_by`` are written together or not at all: each
    table CHECKs that they agree, so a retirement with no actor is refused by
    the store rather than recorded as a fact nobody owns.
    '''
    with store.transaction():
        store.execute(
            f"UPDATE {table} SET retired_at = ?, retired_by = ? "
            f"WHERE {where} AND retired_at IS NULL",
            (now(), actor, *params))
