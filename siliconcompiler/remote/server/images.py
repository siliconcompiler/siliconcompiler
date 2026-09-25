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

__all__ = ["BUCKETS", "PRIMARY", "Held", "Requirement", "Plan", "bundle_path",
           "catalogue", "contents_of", "declared_requirements", "digests_for",
           "sweep_bundles", "matches", "normalize", "specifiers",
           "is_staged", "live_images", "live_software", "pinned_ref",
           "plan_for_job", "register_image", "register_software",
           "register_version", "how_to_ask", "resolve",
           "resolve_declared", "retire_image",
           "retire_software", "retire_version", "stage_bundle", "tracks"]


logger = logging.getLogger("sc-server")


# The distribution every node needs, whatever else it needs: the run is a
# SiliconCompiler process before it is anything else. It is also the key
# `GET /v1`'s `software` map is REQUIRED to carry, and the version whose
# `preference` breaks a tie between two images that both fit.
PRIMARY = "siliconcompiler"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

# 🔴 A CLOSED set, and both keys are always present on the wire -- a client
# branches on them. A bucket may be `{}`: a deployment running no containers
# publishes no tools.
#
# ⚠️ The kind is singular and the bucket is a collection, which is why the two
# are spelled differently and why the mapping is written down rather than
# derived by adding an "s".
BUCKETS = {"python": "python", "tool": "tools"}


class Requirement(NamedTuple):
    '''One thing an image has to hold.

    ``wanted`` is a tuple of **PEP 440 specifier sets, any one of which will
    do** -- ``(">=0.38,<0.40",)``, ``("==2.0", ">=26Q3")`` -- and empty for
    *any live version of this software*, which is the ordinary case for a tool:
    SiliconCompiler does not know which version of OpenROAD it will find until
    the node runs.

    🔴 **A list rather than one string, because that is what SiliconCompiler
    already means by a version requirement.** `Task.get('version')` is a list
    of specifier sets and `check_exe_version` accepts a tool that matches ANY
    of them -- so a flow with two tasks of the same tool has two lists, and
    collapsing them to one string would either lose one or invent an
    intersection nobody asked for. ⚠️ Alternatives are OR; a single set's
    commas are still AND.

    🔴 **A range on the wire and never in storage.** The *no ranges* rule is
    about what a row records -- a stored range is a promise nobody can check --
    and the client half is the opposite problem: ``GET /v1``'s ``software`` map
    is flat per name, while the image join is over combinations, so a client
    resolving each requirement on its own can name a set no single image holds,
    with every version published and satisfiable and nothing to run them in.
    Only the server can answer *which image has both*, so only the server
    resolves.
    '''
    name: str
    wanted: Tuple[str, ...]
    kind: str               # 'library' or 'tool' -- what a refusal calls it

    def __str__(self) -> str:
        if not self.wanted:
            return self.name
        return f"{self.name}{' or '.join(self.wanted)}"


# A specifier begins with an operator; anything else is a bare version, and a
# bare version means `==`. The same leniency `Task.check_version` has, for the
# same reason: it is what people write.
_HAS_OPERATOR = re.compile(r"^\s*(===|==|!=|~=|<=|>=|<|>)")


def specifiers(declared) -> Tuple[str, ...]:
    '''What the client asked for, as PEP 440 specifier sets. Empty is *any*.

    Takes one string or a list of them, because a requirement is a list and
    one alternative is the ordinary case. ⚠️ A bare ``0.38.9`` becomes
    ``==0.38.9`` rather than being refused: it is what every client sent before
    the wire carried ranges, and it is what a person writes.
    '''
    if declared is None:
        return ()

    given = declared if isinstance(declared, (list, tuple)) else [declared]

    wanted = []
    for one in given:
        text = str(one).strip()
        if not text:
            # An empty string is how a client says *any version of this*, which
            # is not the same as not naming the tool at all.
            continue
        wanted.append(text if _HAS_OPERATOR.match(text) else f"=={text}")
    return tuple(wanted)


def normalize(version: str) -> str:
    '''One version, in PEP 440's own spelling, or unchanged.

    🔴 **At registration and not at request time.** It keeps per-tool version
    handling out of the request path, and it removes a skew risk that would
    otherwise be invisible: a client and a server on different SC releases
    normalising the same string differently would disagree about whether an
    image matched, and neither would say so.

    A value that is not PEP 440 comes back unchanged -- a `published_date`
    row, or an image's declared contents being looked up. A `reported` one is
    never stored that way: :func:`register_version` refuses it.
    '''
    from packaging.version import InvalidVersion, Version

    try:
        return str(Version(version))
    except InvalidVersion:
        return version


def _is_pep440(version: str) -> bool:
    from packaging.version import InvalidVersion, Version

    try:
        Version(version)
        return True
    except InvalidVersion:
        return False


def matches(version: str, source: str, wanted: Sequence[str]) -> bool:
    '''Whether one registered version answers one requirement.

    ⚠️ **Any alternative will do**, which is `Task.check_exe_version`'s rule
    one level up: a requirement is a list of specifier sets and a tool that
    matches one of them is acceptable. An empty list is *any version*.

    🔴 **`published_date` never answers, whatever the numbers say.** A tool
    that reports no version is recorded with the date its image was published
    -- a complete tool list beats a partial one -- but `20260924` beats `2.0.1`
    under every comparison there is, so an unversioned build from years ago
    would outrank a current release for ever. The mark exists for exactly this
    check, and it is made before any comparison.
    '''
    if not wanted:
        return True
    if source != "reported":
        return False

    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version

    for one in wanted:
        try:
            # prereleases=True: a server that registered 1.0rc1 registered it
            # on purpose, and silently skipping it would refuse a job for a
            # version the catalogue lists.
            if Version(version) in SpecifierSet(one, prereleases=True):
                return True
        except (InvalidSpecifier, InvalidVersion):
            # Either side unparsable falls back to the only comparison that is
            # always defined: the exact string somebody registered.
            if one.lstrip("=") == version:
                return True
    return False


class Held(NamedTuple):
    '''One distribution an image declares, as the resolution reads it.

    A named tuple rather than a bare one because it grew past two members and a
    positional unpack of five is how the wrong field gets compared.
    '''
    name: str
    version: str
    preference: int
    source: str             # 'reported' or 'published_date'
    kind: str               # 'python' or 'tool'


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
        "SELECT id, registry_ref, digest, note, built_at FROM images "
        "WHERE retired_at IS NULL ORDER BY registry_ref")

    contents: Dict[str, List[Held]] = {}
    for row in store.all(
            "SELECT c.image_id, c.software_name, c.version, sv.preference, "
            "       sv.version_source, s.kind "
            "FROM image_contents c "
            "JOIN software s ON s.name = c.software_name AND s.retired_at IS NULL "
            "JOIN software_versions sv "
            "  ON sv.software_name = c.software_name AND sv.version = c.version "
            " AND sv.retired_at IS NULL "
            "JOIN images i ON i.id = c.image_id AND i.retired_at IS NULL"):
        contents.setdefault(row["image_id"], []).append(
            Held(row["software_name"], row["version"], row["preference"],
                 row["version_source"], row["kind"]))

    return [{"id": row["id"], "registry_ref": row["registry_ref"],
             "digest": row["digest"], "note": row["note"],
             "built_at": row["built_at"],
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
        "ORDER BY software_name, "
        "         CASE version_source WHEN 'reported' THEN 0 ELSE 1 END, "
        "         preference DESC, version")]
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


def how_to_ask(store) -> Dict[str, Dict[str, Optional[str]]]:
    '''Every tool, and how its version is read: a driver, or a package.

    What a probe has to be handed. It is a different interpreter with different
    packages, so *where the driver is* and *which distribution carries the
    version* are both data rather than things it can work out -- and the second
    is not derivable at all, because `slang`'s version is `pyslang`'s.
    '''
    return {row["name"]: {"driver": row["driver"],
                          "version_package": row["version_package"]}
            for row in store.all(
                "SELECT name, driver, version_package FROM software "
                "WHERE kind = 'tool' AND retired_at IS NULL")}


def live_software(store) -> Dict[str, Dict[str, List[str]]]:
    '''Which distributions this deployment tracks, at which versions, in two
    buckets.

    🔴 **`python` and `tools`, and the split is structural rather than
    cosmetic: the two are satisfied differently.** Everything in `python`
    shares one interpreter, so ONE image has to hold all of it -- which is what
    `jobs.image_id` has always meant. A tool is satisfied PER NODE, by an image
    holding the python set and that tool, which is `job_nodes.image_id`.
    Flattened, you cannot tell which names have to land together, and that is
    the question the join asks.

    🔴 **The test a requirement is generated by.** A tool nobody registered
    raises no requirement at all, so a deployment that curates images for the
    framework and says nothing about OpenROAD is not claiming to have an
    OpenROAD image and is not refused for lacking one. Registering the name is
    how an operator takes that claim on.

    ⚠️ **Keyed on the software rather than on its versions**, so a name whose
    every version has been retired is still tracked, with an empty list. The
    claim belongs to the name: retiring a version says *not this one*, and
    retiring the software is how an operator says *not any more*. Collapsing
    the two would make withdrawing the last version silently hand every job
    back to the host it was meant to stop running on.

    🔴 **A `reported` version sorts above a `published_date` one whatever the
    numbers say.** That is the whole reason the mark exists: a tool recorded
    from its image's publish date is `20260924`, which beats `2.0.1` under
    every comparison there is, so without the ordering an unversioned build
    from years ago would head this list for ever.

    ⚠️ **Both kinds appear here, and `GET /v1`'s `software` has nowhere to
    carry the mark**, so a client's preflight can say yes to a version
    requirement this server will then refuse. Accepted: the preflight is
    advisory and the server is binding. The condition is that the refusal says
    *present but reports no version* rather than *no image matches* -- see
    `_unsatisfiable`.
    '''
    tracked: Dict[str, Dict[str, List[str]]] = {"python": {}, "tools": {}}

    for row in store.all("SELECT name, kind FROM software WHERE retired_at IS NULL"):
        tracked[BUCKETS[row["kind"]]][row["name"]] = []

    for row in store.all(
            "SELECT sv.software_name AS name, sv.version, s.kind "
            "FROM software_versions sv "
            "JOIN software s ON s.name = sv.software_name "
            "WHERE s.retired_at IS NULL AND sv.retired_at IS NULL "
            "ORDER BY sv.software_name, "
            "         CASE sv.version_source WHEN 'reported' THEN 0 ELSE 1 END, "
            "         sv.preference DESC, sv.version DESC"):
        tracked[BUCKETS[row["kind"]]][row["name"]].append(row["version"])

    return tracked


def tracks(software: Dict[str, Dict[str, List[str]]], name: str) -> bool:
    '''Whether this deployment curates images for a name, in either bucket.'''
    return any(name in bucket for bucket in software.values())


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
        if not any(entry.name == want.name
                   and matches(entry.version, entry.source, want.wanted)
                   for entry in held):
            return False
    return True


def _rank(image):
    '''Lower sorts first: preference, specificity, build time, then the name.

    🔴 **`preference` first, and NOT the newest version** -- the schema already
    refuses newest-wins, because a rebuilt image is newer and is not
    necessarily preferred. Where no requirement names a version this is the
    whole answer.

    🔴 **Then the fewest declared contents, and this is the rule that makes the
    buckets pay.** Every image holds `siliconcompiler`, the twelve-gigabyte
    tool image included, so a framework node's requirement set is satisfied by
    all of them -- and they usually carry the SAME version, so preference ties
    and decides nothing. The most specific image that still fits is what gets
    an import node into the python-only image. There is no `python_only` flag:
    an image whose contents are all `kind = 'python'` already is one, and a
    boolean beside a derivable fact is a second source that drifts.

    🆕 **Then `built_at`, newest first**, which is the tie two images carrying
    identical versions leave -- same preference, same contents, nothing left to
    choose by. ⚠️ `built_at` and never `resolved_at`: the latter records when
    the operator pinned the tag, so registering a two-year-old image today
    would make it the newest, and pinning an old image on purpose is a
    reproducibility case rather than a mistake. An image whose manifest said
    nothing sorts last among its ties.
    '''
    preference = max((entry.preference for entry in image["contents"]
                      if entry.name == PRIMARY), default=None)
    # An image holding no framework at all ranks below every one that does,
    # rather than being excluded: it can still be the only thing that fits a
    # requirement set which never mentioned the framework.
    return (-preference if preference is not None else 1,
            len(image["contents"]),
            _newest_first(image["built_at"]),
            image["registry_ref"])


def _newest_first(built_at: Optional[str]) -> str:
    '''A sort key that puts the newest build first and an unknown one last.

    RFC 3339 sorts as a string, so inverting it is a character-wise complement
    rather than a parse -- and an unknown build time gets a key that sorts
    after every real one instead of being treated as the oldest, which would
    be a claim the row does not make.
    '''
    if not built_at:
        return "~"                      # after every digit, dash and colon
    return "".join(chr(0x7e - (ord(c) - 0x20)) if 0x20 <= ord(c) < 0x7f else c
                   for c in built_at)


def plan_for_job(store, requires: Dict[str, Any],
                 node_tools: Dict[Tuple[str, str], Optional[str]],
                 inherits=None) -> Plan:
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
    software = live_software(store)

    # 🔴 The python set alone decides the JOB image, because those names share
    # one interpreter and one container therefore has to hold all of them.
    pinned = declared_requirements(software, requires)
    job_image = resolve_declared(images, pinned)

    refs = {image["id"]: pinned_ref(image["registry_ref"], image["digest"])
            for image in images}

    inherits = inherits or {}
    held = software["tools"]

    nodes: Dict[Tuple[str, str], Optional[str]] = {}
    for node, tool in node_tools.items():
        if not tool:
            # 🆕 A node that declares nothing but says it follows its input
            # runs where that input ran: the execute tasks build a command out
            # of the manifest, so there is nothing to require an image for, and
            # the environment that produced the inputs is the one most likely
            # to be able to run it.
            #
            # ⚠️ In flowgraph order, so the node it follows is already placed.
            # An input that is not (a node outside this run) falls back to the
            # job's image, which is what a node needing nothing gets anyway.
            after = inherits.get(node)
            nodes[node] = (nodes.get(after) if node in inherits else None) \
                or job_image["id"]
            continue

        if tool not in held:
            # 🔴 **A requirement no live image holds is fatal.** Where every
            # node runs in a container the registry IS the world: there is
            # nowhere for it to run, and placing it anywhere means dispatching
            # a node that cannot work.
            #
            # Observed: a Bluespec design submitted to a deployment that had
            # never heard of `bsc` was accepted, its `convert` node placed in
            # the PYTHON-ONLY image because nothing raised a requirement,
            # dispatched, and died on the first node with every other node
            # cancelled behind it. The cluster was paid for to learn something
            # submit already knew.
            #
            # ⚠️ What a node needs is DECLARED by its task, so nothing here
            # infers it: `Task.image_requirement` says `openroad` for an
            # OpenROAD task, `slang` for one that has no executable at all, and
            # nothing for a builtin. See `runspec.node_tools`.
            raise _unregistered(tool, node, images)

        # 🔴 The python set PLUS this node's tool, which is exactly what
        # `job_nodes.image_id` has always meant. Resolved per node, because two
        # tools need not be in one image and requiring that would mean one
        # image holding everything -- and because two NODES may want different
        # versions of the same tool.
        #
        # ⚠️ Pinning narrows the candidates BEFORE any tie is broken: with
        # `siliconcompiler==0.38.9` in the python set, `built_at` chooses the
        # newest OpenROAD *among images holding that SC*, not the newest image.
        asked = ((requires or {}).get("tools") or {}).get(tool)
        wants = list(pinned) + [Requirement(tool, specifiers(asked), "tool")]
        found = resolve(images, wants)
        if found is None:
            raise _unsatisfiable(wants, images, blame=tool)
        nodes[node] = found["id"]

    return Plan(job_image["id"], nodes, refs)


def declared_requirements(software, requires: Dict[str, Any]) -> List[Requirement]:
    '''What the run's own Python process needs: the `python` bucket.

    The framework, plus any library the client asked for. A name this
    deployment does not track is not a requirement -- it is a version of
    something nobody here curates, and `version-skew` is where that is answered
    if it is answered at all.

    🔴 **One image has to satisfy all of it**, because these names share a
    process: `siliconcompiler` and a site library run in the same interpreter,
    so spreading them over two containers is not a deployment, it is a broken
    one. The `tools` bucket is the opposite and is resolved per node.

    🔴 **Computable without the upload**, which is what lets create resolve
    images as well as submit: it needs the declared versions and the registry
    and nothing else. That is what keeps the create-time reuse check able to
    skip the upload entirely.
    '''
    tracked = software["python"]
    asked = (requires or {}).get("python") or {}

    pinned = [Requirement(name, specifiers(wanted), "library")
              for name, wanted in sorted(asked.items())
              if name in tracked and isinstance(wanted, (str, int, float, list))]

    if PRIMARY in tracked and not any(want.name == PRIMARY for want in pinned):
        # The client named no framework version. The deployment's own
        # preference order picks, which is what `preference` is for -- and
        # deliberately NOT the newest, because a rebuilt image is newer and is
        # not necessarily preferred.
        pinned.append(Requirement(PRIMARY, None, "library"))

    return pinned


def resolve_declared(images, requirements: Sequence[Requirement]):
    '''The one image the declared versions resolve to. Raises if none fits.'''
    if not images:
        raise ProblemError(
            "unsatisfiable-request", resource_kind="library", resource=PRIMARY,
            detail="this server runs jobs in containers and has no image "
                   "registered")

    found = resolve(images, requirements)
    if found is None:
        raise _unsatisfiable(requirements, images)
    return found


def digests_for(store, requires: Dict[str, Any]) -> List[str]:
    '''What this descriptor's declared versions resolve to, as digests.

    🔴 **The server's half of the job identity.** The client keeps computing
    its own hash over the work and tracks nothing extra; this is folded in, so
    two runs asking for the same thing and resolved to different images are
    correctly different jobs -- and re-registering an image invalidates reuse
    exactly when it should, because a new digest is precisely *the code
    changed*.

    Raises the same refusal submit would, which is the point of doing it at
    create: a descriptor nothing can run is refused before the upload rather
    than after it.
    '''
    images = live_images(store)
    requirements = declared_requirements(live_software(store), requires)
    return [resolve_declared(images, requirements)["digest"]]


def contents_of(store, image_ids: Sequence[Optional[str]]) -> Dict[str, List[str]]:
    '''Every version the given images declare, keyed by distribution.

    🔴 **What a job ran, once a request can carry a range.** Nothing else can
    answer it: the descriptor says what was asked for and the answer is
    whatever this server chose.

    ⚠️ A list per name and not one string, for the same reason `GET /v1`'s
    `software` is a list. A wide flow resolves several images, and where the
    client pinned nothing they can legitimately hold different versions of the
    same distribution -- so a single value would have to pick one and be wrong.
    '''
    wanted = {image_id for image_id in image_ids if image_id}
    if not wanted:
        return {}

    found: Dict[str, List[str]] = {}
    for image in live_images(store):
        if image["id"] not in wanted:
            continue
        for entry in image["contents"]:
            versions = found.setdefault(entry.name, [])
            if entry.version not in versions:
                versions.append(entry.version)

    return {name: sorted(versions) for name, versions in sorted(found.items())}


def _unsatisfiable(requirements: Sequence[Requirement], images,
                   blame: Optional[str] = None) -> ProblemError:
    '''No live image holds all of this.

    🔴 `unsatisfiable-request` rather than `entitlement-denied`: the same
    catalogue and a different question. *This deployment does not have it*, not
    *you may not use it* -- and waiting will not change it.

    🔴 **And it has to say WHICH of those two it is when a name is here but
    unversioned.** A tool recorded from its publish date is in the catalogue,
    appears in `GET /v1`'s `software` -- which has nowhere to carry the mark --
    and can never satisfy a range. So a client's own preflight says yes and
    this says no, which is accepted because the preflight is advisory and this
    is binding. What is NOT acceptable is answering *no image matches* for it:
    the honest answer is that the thing is present and reports no version, and
    the two send somebody to completely different places.
    '''
    culprit = next((want for want in requirements if want.name == blame),
                   requirements[-1] if requirements else None)

    unversioned = _present_but_unversioned(requirements, images)
    if unversioned:
        return ProblemError(
            "unsatisfiable-request",
            resource_kind=unversioned.kind, resource=str(unversioned),
            detail=f"this server has {unversioned.name}, and every image "
                   "holding it reports no version for it -- so nothing here "
                   "can be matched against a version requirement. Ask for it "
                   "without a version, or ask the operator to register the "
                   "version its images actually hold")

    return ProblemError(
        "unsatisfiable-request",
        resource_kind=culprit.kind if culprit else "tool",
        resource=str(culprit) if culprit else "unknown",
        detail=f"no image on this server holds "
               f"{', '.join(str(want) for want in requirements)}; "
               f"{len(images)} image(s) are registered")


def _unregistered(tool: str, node: Tuple[str, str], images) -> ProblemError:
    '''A node needs a program this deployment has never heard of.

    🔴 Distinct from *registered and in no image*, and the detail says which:
    one is an operator who curated a tool and has not built an image holding
    it, the other is a flow reaching for something nobody here offers at all.
    They are fixed in different places by different people.
    '''
    step, index = node
    return ProblemError(
        "unsatisfiable-request", resource_kind="tool", resource=tool,
        detail=f"{step}/{index} runs {tool}, and no image on this server holds "
               f"it -- this deployment runs every node in a container, so there "
               f"is nowhere for it to run. {len(images)} image(s) are "
               "registered, and an operator adds one with "
               "'registry add-software' and 'registry add-image'")


def _present_but_unversioned(requirements: Sequence[Requirement], images):
    '''The first requirement whose name is held, but never with a version.

    Distinguishes *this server does not have it* from *this server has it and
    cannot tell you which one*. Only a requirement that NAMES a version can hit
    this: one that does not is satisfied by any live version, mark or no mark.
    '''
    for want in requirements:
        if not want.wanted:
            continue
        sources = {entry.source for image in images
                   for entry in image["contents"] if entry.name == want.name}
        if sources and "reported" not in sources:
            return want
    return None


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


def stage_bundle(root, ref: str, digest: str, mounts=()):
    '''Unpack one image into a bundle Slurm can run, if it is not there.

    🔴 ``srun --container`` takes a bundle on disk and not a registry
    reference, so somebody has to do this. Shared by the three callers that
    need it at three different moments -- an operator staging ahead of time,
    submit making sure the FRAMEWORK bundle exists before ``sbatch`` names it,
    and the run fetching a node's image while that node reports ``preparing``
    -- because three implementations of an unpack is three ways for a bundle to
    be subtly different.

    Built through a ``.part`` directory and renamed, so a bundle either exists
    complete or does not exist at all. Two callers wanting the same digest race
    and one loses the rename; losing is fine, because the content is addressed
    by that digest and both copies are the same bytes.

    ``mounts`` are the host directories a job needs to see from inside -- the
    build tree it writes to and the cache it reads. They go into the bundle's
    own ``config.json`` rather than into ``oci.conf``, because the shared tree
    is this server's business and a mount configured on the cluster would apply
    to every container Slurm ever ran, including ones it knows nothing about.

    Returns the bundle path. Already staged is a no-op, which is what makes it
    safe to call on every submit.
    '''
    import os
    import shutil
    import subprocess

    target = bundle_path(root, digest)
    if is_staged(target):
        return target

    for tool in ("skopeo", "umoci"):
        if shutil.which(tool) is None:
            raise RuntimeError(
                f"{tool} is not installed here, and unpacking an OCI bundle "
                "needs it")

    target.parent.mkdir(parents=True, exist_ok=True)

    staging = target.with_name(target.name + ".part")
    layout = target.with_name(target.name + ".oci")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(layout, ignore_errors=True)

    try:
        subprocess.run(["skopeo", "copy", f"docker://{ref}", f"oci:{layout}:sc"],
                       check=True)
        # 🔴 `--rootless` only when this really is unprivileged, and it is not
        # a safety flag: it makes umoci write a spec with a USER namespace and
        # no uid mapping, and a container in one cannot mount its own /proc.
        # The failure is "mount `proc` to `proc`: Operation not permitted",
        # which reads like a missing capability rather than like a spec that
        # asked for an unprivileged container nobody wanted.
        unpack = ["umoci", "unpack", "--image", f"{layout}:sc", str(staging)]
        if os.geteuid() != 0:
            unpack.insert(2, "--rootless")

        subprocess.run(unpack, check=True)
        _prepare_spec(staging / "config.json", mounts)
        try:
            staging.rename(target)
        except OSError:
            # Somebody else finished first. Their bundle is this bundle.
            if not is_staged(target):
                raise
    finally:
        shutil.rmtree(layout, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)

    return target


def sweep_bundles(root, store) -> int:
    '''Reclaim the unpacked bundles nothing can run any more. Returns bytes.

    🔴 **Without this a rig fills its disk, quietly and fast.** A bundle is an
    image unpacked onto the filesystem, so the tools one is six and a half
    gigabytes -- and a rebuild produces a new digest, which supersedes the old
    row and leaves the old bundle exactly where it was. Twelve of them, 28 GB,
    is what one afternoon of rebuilds measured.

    ⚠️ **Superseded is not the same as unused, and that is what the query is
    for.** An image row is never deleted, because *what did this run in* has to
    stay answerable -- but the BYTES are only needed while something might
    start in them. A retired image that no unfinished job names can go; one
    that a running job names cannot, because `--container` points straight at
    this path and pulling it out from under a job is a failure with no sensible
    message.

    Also takes the `.part` and `.oci` directories a crashed unpack leaves.
    Those are intermediate by construction -- the real bundle is renamed into
    place last -- so one being present means nothing is using it.
    '''
    import shutil

    from pathlib import Path

    root = Path(root)
    if not root.is_dir():
        return 0

    keep = {row["digest"].replace("sha256:", "")
            for row in store.all("SELECT digest FROM images WHERE retired_at IS NULL")}

    # A retired image whose bytes something might still start in. Both columns,
    # because a job records the framework image and each node records its own.
    busy = {row["digest"].replace("sha256:", "") for row in store.all(
        "SELECT i.digest FROM images i WHERE i.retired_at IS NOT NULL AND ("
        "  EXISTS (SELECT 1 FROM jobs j WHERE j.image_id = i.id"
        "          AND j.state NOT IN ('completed', 'failed', 'cancelled',"
        "                              'rejected', 'abandoned'))"
        "  OR EXISTS (SELECT 1 FROM job_nodes n JOIN jobs j ON j.id = n.job_id"
        "             WHERE n.image_id = i.id"
        "             AND j.state NOT IN ('completed', 'failed', 'cancelled',"
        "                                 'rejected', 'abandoned')))")}

    freed = 0
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.endswith((".part", ".oci")):
            freed += _weigh(entry)
            shutil.rmtree(entry, ignore_errors=True)
            continue
        if entry.name in keep or entry.name in busy:
            continue

        logger.info(f"reclaiming the bundle for {entry.name[:12]}")
        freed += _weigh(entry)
        shutil.rmtree(entry, ignore_errors=True)

    return freed


def _weigh(path) -> int:
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _prepare_spec(config, mounts) -> None:
    '''Make the unpacked bundle runnable for a job on this cluster.

    ⚠️ Two edits, and both are about what an image knows nothing about: it
    describes a filesystem, and a job needs a machine.

    **The mounts.** A container's root filesystem is the image's, so without
    them a node starts in a world where its own build directory does not exist.
    Bind mounts at the same path inside as out, because the manifest the run
    loads names absolute paths resolved on the server -- a different path
    inside would need every one of them rewritten.

    🔴 **The network namespace is removed.** A container in its own one cannot
    reach `slurmctld`, which is fatal for the framework image -- it submits
    every node of the flow it is driving -- and wrong for a task that needs a
    licence server. A compute job belongs on the cluster's network.
    '''
    import json

    with open(config) as f:
        spec = json.load(f)

    # ⚠️ An image's config asks for a terminal because a person usually runs
    # it. Slurm does not give one: it captures stdout to a file, and crun then
    # dies with "tcgetattr: Inappropriate ioctl for device" before the task
    # starts -- which says nothing about a terminal to anybody reading it.
    spec.setdefault("process", {})["terminal"] = False

    namespaces = spec.get("linux", {}).get("namespaces")
    if namespaces is not None:
        spec["linux"]["namespaces"] = [
            entry for entry in namespaces if entry.get("type") != "network"]

    existing = {entry.get("destination") for entry in spec.get("mounts", [])}
    for path in mounts:
        path = str(path)
        if path in existing:
            continue
        spec.setdefault("mounts", []).append({
            "destination": path,
            "source": path,
            "type": "none",
            "options": ["rbind", "rw"],
        })

    with open(config, "w") as f:
        json.dump(spec, f)


def is_staged(bundle) -> bool:
    '''Whether a bundle is there and complete.

    An OCI bundle is a directory, so its existence says nothing: the config is
    what a finished one has, and the unpack renames it into place last.
    '''
    from pathlib import Path

    return (Path(bundle) / "config.json").is_file()


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

def register_software(store, name: str, display_name: str, actor: str,
                      kind: str, driver: Optional[str] = None,
                      version_package: Optional[str] = None) -> str:
    '''Declare that this deployment curates images for a distribution.

    ⚠️ It is a claim with teeth: from here on, a job whose flow needs this tool
    and finds no image holding it is refused at submit. That is the point --
    the alternative is a job that dispatches into a container without the tool
    it needs.

    🔴 **`kind` is stated and is deliberately not derived.** Deriving it means
    asking THIS process whether it can import the name or drive it, and this
    process is not the image: it works for SiliconCompiler's own in-tree
    drivers and quietly gives the wrong answer for everything else, which is
    the worst shape a derivation can have. It decides which bucket the name is
    published in and therefore whether one image has to hold it or each node's
    does, so it is an operator's statement.

    🔴 **`driver` is the module carrying a tool's Task driver**, and it is what
    a probe running inside an image is handed. It cannot be worked out there
    either: a driver can live in any package -- a site library ships its own
    and a proprietary tool's never will be in this tree -- and the in-tree path
    is not reliable in-tree, where `kepler-formal` is driven from
    `...tools.keplerformal`.

    🔴 **`version_package` is the same class of fact: how do I get this name's
    version.** A tool can have no executable at all -- slang's driver runs
    pyslang in the framework's own process -- and still has to be placed in an
    image holding it. The distribution is not called what the tool is called,
    so the mapping is recorded rather than guessed.

    ⚠️ A tool with no driver is legitimate: it is in the image, this deployment
    lists it, and nothing here can ask its version. That is what
    `published_date` records.

    Returns the kind that was recorded.
    '''
    from siliconcompiler.remote.server import probe

    if kind not in probe.KINDS:
        raise ValueError(
            f"{kind!r} is not a software kind; try "
            f"{' or '.join(probe.KINDS)}")
    if driver and kind != "tool":
        raise ValueError(
            f"{name} is {kind} and names a task driver; a driver is what makes "
            "something a tool")
    if version_package and kind != "tool":
        raise ValueError(
            f"{name} is {kind}, so its own name is where its version comes "
            "from; naming a package would be a second source for it")

    with store.transaction():
        store.execute(
            "INSERT INTO software (name, display_name, kind, driver, "
            "                      version_package, added_by) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (name) DO UPDATE SET display_name = excluded.display_name, "
            "  kind = excluded.kind, driver = excluded.driver, "
            "  version_package = excluded.version_package, "
            "  retired_at = NULL, retired_by = NULL",
            (name, display_name or name, kind, driver, version_package, actor))
    return kind


def register_version(store, name: str, version: str, actor: str,
                     preference: int = 0, source: str = "reported") -> str:
    '''One exact version. Returns the spelling that was stored.

    🔴 **Exact in STORAGE, and that rule is scoped to storage.** A stored range
    is a promise nobody can check against anything; the wire carries specifiers
    and they are matched against these rows. An exact version is a row somebody
    added on purpose.

    🔴 **Normalised here, at registration, and not at request time.** It keeps
    per-tool version handling off the request path, and it removes a skew that
    would otherwise be silent: a client and a server on different SC releases
    normalising the same string differently would disagree about whether an
    image matched, and neither would say so.

    ⚠️ ``source="published_date"`` is how a tool that reports no version gets
    into the catalogue at all -- a complete tool list beats a partial one. What
    it costs is that such a row can never satisfy a version requirement and
    always sorts below a reported one, whatever the numbers say.
    '''
    if store.one("SELECT name FROM software WHERE name = ?", (name,)) is None:
        raise ValueError(f"{name} is not registered software; add it first")
    if source not in ("reported", "published_date"):
        raise ValueError(f"{source} is not a version source")

    # 🔴 A `reported` version that has no PEP 440 form is refused, not stored.
    # It is the contract's `version_norm NOT NULL` said in code: the row has
    # nothing to put there, so it cannot be written. Never coerce, pad or
    # substitute to get one in -- a parser handed output it did not expect can
    # return anything (`initialize`, out of gtkwave's `Could not initialize
    # GTK!`), and a rewritten value hides that from the operator who needs to
    # see it. The row is `published_date`, which is the fallback that works.
    if source == "reported" and not _is_pep440(version):
        raise ValueError(
            f"{name} {version!r} is not a PEP 440 version, so it cannot be "
            "recorded as reported; check what the tool printed, and register "
            "it as published_date (-unversioned) if it reports none")

    stored = normalize(version) if source == "reported" else version

    with store.transaction():
        store.execute(
            "INSERT INTO software_versions "
            "  (software_name, version, version_source, preference, added_by) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (software_name, version) DO UPDATE SET "
            "  version_source = excluded.version_source, "
            "  preference = excluded.preference, retired_at = NULL, retired_by = NULL",
            (name, stored, source, preference, actor))
    return stored


def register_image(store, registry_ref: str, digest: str,
                   contents: Sequence[Tuple[str, str]], actor: str,
                   note: Optional[str] = None,
                   built_at: Optional[str] = None) -> str:
    '''Register a container this deployment may run.

    🔴 **The most dangerous write in this schema: it chooses what code executes
    on the cluster.** Higher stakes than any read permission -- a grant decides
    who may see something, this decides what runs as the account the job maps
    to. So it takes a person, every time: ``registered_via`` is the CI path and
    it does not exist here.

    ⚠️ ``built_at`` comes off the image's own manifest and is the only thing
    that separates two images carrying identical versions. It is optional
    because a manifest may not carry one, and NULL means exactly that rather
    than *old*.
    '''
    if not _DIGEST.match(digest or ""):
        raise ValueError(f"{digest!r} is not a sha256 digest")
    if not contents:
        raise ValueError("an image with no declared contents can satisfy nothing")

    # 🔴 Normalised before it is looked up, with the SAME rule that stored it.
    # `verilator 5.052` is stored as `5.52` -- PEP 440 strips the leading zero
    # -- so a caller naming the version the tool actually printed would be told
    # it is not registered, by the registry that just registered it. The
    # normalisation has to happen wherever a version is named, not only where
    # one is written.
    contents = [(name, normalize(version)) for name, version in contents]

    for name, version in contents:
        if store.one("SELECT version FROM software_versions "
                     "WHERE software_name = ? AND version = ?",
                     (name, version)) is None:
            raise ValueError(f"{name}=={version} is not a registered version")

    existing = store.one("SELECT id FROM images WHERE digest = ?", (digest,))
    image_id = existing["id"] if existing else str(uuid7())

    # 🔴 One live image per reference. The digest identifies the BYTES and the
    # reference identifies the thing an operator curates, so re-registering a
    # rebuilt tag supersedes the build before it rather than standing beside
    # it. Two live rows for one reference are indistinguishable to the
    # resolution -- same declared contents, same name -- so it would pick
    # between them arbitrarily, and a rebuild would appear to have no effect
    # while the old bytes went on running.
    #
    # ⚠️ Superseded and not deleted. A job from last year names that row, and
    # *what did this run in* has to stay answerable.
    superseded = [row["id"] for row in store.all(
        "SELECT id FROM images WHERE registry_ref = ? AND digest <> ? "
        "  AND retired_at IS NULL", (registry_ref, digest))]

    with store.transaction():
        for old_id in superseded:
            store.execute(
                "UPDATE images SET retired_at = ?, retired_by = ? WHERE id = ?",
                (now(), actor, old_id))

        if existing:
            # Re-registering the same bytes under a new tag or a new content
            # list. The digest is the identity, so this is an update rather than
            # a second row claiming to be the same image.
            store.execute(
                "UPDATE images SET registry_ref = ?, resolved_at = ?, note = ?, "
                "  built_at = ?, registered_by = ?, retired_at = NULL, "
                "  retired_by = NULL WHERE id = ?",
                (registry_ref, now(), note, built_at, actor, image_id))
            store.execute("DELETE FROM image_contents WHERE image_id = ?", (image_id,))
        else:
            store.execute(
                "INSERT INTO images (id, registry_ref, digest, resolved_at, "
                "                    built_at, registered_by, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (image_id, registry_ref, digest, now(), built_at, actor, note))

        for name, version in contents:
            store.execute(
                "INSERT INTO image_contents (image_id, software_name, version) "
                "VALUES (?, ?, ?)", (image_id, name, version))

    if superseded:
        logger.info(f"{registry_ref} supersedes {len(superseded)} earlier "
                    "image(s) at that reference")

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
