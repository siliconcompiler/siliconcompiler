'''
What a version means in containers: the registry of software, versions and
images, and resolving a job's requirements to them.

🔴 The submitter names a version and the operator names the image: a client that
could name an image would choose what executes on the cluster. The registry is
also the switch: one that registers nothing runs jobs on the host, which is
conforming; ``containers`` in the config turns images on.
⚠️ ``image_contents`` is declared and unverified here: a wrong row fails a job at
run time, not at submit.
'''

import json
import logging
import re
import uuid

from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from siliconcompiler.remote.environment import IMAGE_SITE, canonical
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.running.runspec import write_json
from siliconcompiler.remote.server.software.probe import INTERPRETER, KINDS
from siliconcompiler.remote.server.state.store import now

__all__ = ["BUCKETS", "PRIMARY", "Held", "Requirement", "Plan", "bundle_path",
           "catalogue", "contents_of", "declared_requirements",
           "sweep_bundles", "matches", "normalize", "specifiers",
           "derivation", "derived_image", "register_derived", "stage_derived_bundle",
           "job_bundle", "is_staged", "live_images", "live_software", "pinned_ref",
           "plan_for_job", "register_image", "register_software", "register_version",
           "resolve", "resolve_declared", "retire_image", "retire_software",
           "retire_version", "stage_bundle"]


logger = logging.getLogger("sc-server")


# What every node needs; the key `GET /v1`'s `software` must carry, and whose
# `preference` breaks a tie between images.
PRIMARY = "siliconcompiler"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

# 🔴 Kind -> bucket, a closed set with all three keys always on the wire, a
# bucket possibly `{}`. ⚠️ Written out, not derived by adding an "s".
BUCKETS = {"python": "python", "tool": "tools", "interpreter": "interpreter"}

# A requirement's `kind` on a `software-unavailable` `unresolved` entry
# (surface D311): the `requested_versions` key it is under, as spelled.
UNRESOLVED_KIND = {"library": "python", "tool": "tools", "interpreter": "interpreter"}


class Requirement(NamedTuple):
    '''One thing an image has to hold.

    ``wanted`` is PEP 440 specifier sets, any one of which will do, as in
    `Task.get('version')`; empty is any live version. ⚠️ Alternatives are OR,
    a set's commas AND. 🔴 A range on the wire, never in storage: only the
    server can answer *which image holds all of these*, so only it resolves.
    '''
    name: str
    wanted: Tuple[str, ...]
    kind: str               # 'library', 'tool' or 'interpreter' -- what a refusal calls it

    def __str__(self) -> str:
        if not self.wanted:
            return self.name
        return f"{self.name}{' or '.join(self.wanted)}"


_HAS_OPERATOR = re.compile(r"^\s*(===|==|!=|~=|<=|>=|<|>)")


def specifiers(declared) -> Tuple[str, ...]:
    '''What the client asked for, as PEP 440 specifier sets; empty is *any*.

    ⚠️ A bare ``0.38.9`` means ``==0.38.9``, as in `Task.check_exe_version`.
    '''
    if declared is None:
        return ()

    given = declared if isinstance(declared, (list, tuple)) else [declared]

    wanted = []
    for one in given:
        text = str(one).strip()
        if not text:
            continue
        wanted.append(text if _HAS_OPERATOR.match(text) else f"=={text}")
    return tuple(wanted)


def normalize(version: str) -> str:
    '''One version in PEP 440's own spelling, or unchanged if it is not PEP 440.'''
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
    '''Whether one registered version answers one requirement: any alternative will do.

    🔴 A `published_date` version never answers a specifier: `20260924` beats
    `2.0.1` under every comparison, so an old unversioned build would win forever.
    '''
    if not wanted:
        return True
    if source != "reported":
        return False

    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version

    for one in wanted:
        try:
            # A registered prerelease was registered on purpose.
            if Version(version) in SpecifierSet(one, prereleases=True):
                return True
        except (InvalidSpecifier, InvalidVersion):
            # Unparsable: the exact registered string.
            if one.lstrip("=") == version:
                return True
    return False


class Held(NamedTuple):
    '''One distribution an image declares, as the resolution reads it.'''
    name: str
    version: str
    preference: int
    source: str             # 'reported' or 'published_date'
    kind: str               # 'python', 'tool' or 'interpreter'


class Plan(NamedTuple):
    '''Which image each part of one job runs in.

    ``refs`` pins every id, so the runner needs no database to know what to pull.
    '''
    job: Optional[str]                              # images.id, or None
    nodes: Dict[Tuple[str, str], Optional[str]]     # (step, index) -> images.id
    refs: Dict[str, str]                            # images.id -> repository@digest

    def ref(self, image_id: Optional[str]) -> Optional[str]:
        return self.refs.get(image_id) if image_id else None

    def placements(self) -> Dict[Tuple[str, str], str]:
        '''Every node that has an image, as the reference to pull.'''
        return {node: self.refs[image]
                for node, image in self.nodes.items()
                if image and image in self.refs}


######################################################################
# Reading the registry
######################################################################

def own_version() -> str:
    '''The SiliconCompiler this server runs: the one version every job resolves to (profile §5).

    🔴 One, because the manifest's read is this server's own SiliconCompiler.
    '''
    from siliconcompiler import __version__

    return __version__


def holds_own_version(image) -> bool:
    '''Whether ``image`` holds this server's own SiliconCompiler.'''
    mine = normalize(own_version())
    return any(held.name == PRIMARY and normalize(held.version) == mine
               for held in image["contents"])


def live_images(store) -> List[Dict[str, Any]]:
    '''Every image this deployment may run, with what it declares it holds.

    The match is in Python, not a dynamic SQL ``HAVING``: being able to read
    the rule over the most dangerous data matters more than the query plan.
    '''
    # 🔴 Never a derived image, or one user's packages would place another's node.
    rows = store.all(
        "SELECT id, registry_ref, digest, note, built_at, resolved_at FROM images "
        "WHERE retired_at IS NULL AND derived_from IS NULL ORDER BY registry_ref")

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
             "built_at": row["built_at"], "resolved_at": row["resolved_at"],
             "contents": contents.get(row["id"], [])}
            for row in rows]


def catalogue(store, include_retired: bool = False) -> Dict[str, Any]:
    '''The whole registry, for the ``registry`` command and the portal's images screen.'''
    where = "" if include_retired else " WHERE retired_at IS NULL"

    software = [dict(row) for row in store.all(
        f"SELECT * FROM software{where} ORDER BY name")]
    versions = [dict(row) for row in store.all(
        f"SELECT * FROM software_versions{where} "
        "ORDER BY software_name, "
        "         CASE version_source WHEN 'reported' THEN 0 ELSE 1 END, "
        "         preference DESC, version")]
    rows = [dict(row) for row in store.all(
        f"SELECT * FROM images{where} ORDER BY registry_ref")]

    holds: Dict[str, List[str]] = {}
    for row in store.all("SELECT * FROM image_contents "
                         "ORDER BY software_name, version"):
        holds.setdefault(row["image_id"], []).append(
            f"{row['software_name']}=={row['version']}")
    for image in rows:
        image["contents"] = holds.get(image["id"], [])

    images = [row for row in rows if not row.get("derived_from")]
    derived = [row for row in rows if row.get("derived_from")]
    bases = {row["id"]: row["registry_ref"] for row in store.all(
        "SELECT id, registry_ref FROM images WHERE id IN (SELECT derived_from FROM images)")}
    for image in derived:
        image["installed"] = [f"{name}=={version}"
                              for name, version in json.loads(image["installed"] or "[]")]
        image["base"] = bases.get(image["derived_from"])

    return {"software": software, "versions": versions, "images": images,
            "derived": derived}


def live_software(store) -> Dict[str, Dict[str, List[str]]]:
    '''Which distributions this deployment tracks, at which versions, in the three buckets.

    🔴 The split is structural: the python set is satisfied by one image per job,
    a tool per node (surface D293 for `interpreter`). Only a registered name
    raises a requirement at all. ⚠️ Keyed on the software, so a name whose
    every version is retired is still tracked, with none: retiring the last
    version must not hand jobs back to the host. 🔴 `reported` versions sort first.
    '''
    tracked: Dict[str, Dict[str, List[str]]] = {bucket: {} for bucket in BUCKETS.values()}

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


######################################################################
# The resolution
######################################################################

def resolve(images, requirements: Sequence[Requirement]):
    '''The one image that fits, or None, ranked by :func:`_rank`.'''
    fits = [image for image in images if _satisfies(image, requirements)]
    if not fits:
        return None

    return min(fits, key=lambda image: _rank(image, requirements))


def _satisfies(image, requirements: Sequence[Requirement]) -> bool:
    held = image["contents"]
    for want in requirements:
        if not any(entry.name == want.name
                   and matches(entry.version, entry.source, want.wanted)
                   for entry in held):
            return False
    return True


def _rank(image, requirements: Sequence[Requirement] = ()):
    '''Lower sorts first: preference, specificity, build time, pin time, then the name.

    🔴 The operator's `preference`, never newest-wins: a rebuilt image is newer,
    not preferred. 🔴 Then the fewest declared contents (bar the interpreter),
    so a framework node lands in the python-only image rather than the huge
    tool image holding the same SC. 🆕 Then `built_at`, ⚠️ before
    `resolved_at`, which is when the tag was pinned; `resolved_at` still
    breaks ties between reproducible builds stamped 1970.
    '''
    preference = max((entry.preference for entry in image["contents"]
                      if entry.name == PRIMARY), default=None)
    # 🔴 Every other name asked for by preference too, never build time (surface D177).
    chosen = []
    for want in requirements:
        if want.name == PRIMARY:
            continue
        held = [entry for entry in image["contents"] if entry.name == want.name
                and matches(entry.version, entry.source, want.wanted)]
        chosen.append(min(((entry.source != "reported", -entry.preference)
                           for entry in held), default=(True, 0)))
    # No framework ranks last, not excluded: it may be the only fit.
    return (-preference if preference is not None else 1,
            tuple(chosen),
            sum(1 for entry in image["contents"] if entry.kind != "interpreter"),
            _newest_first(image["built_at"]),
            _newest_first(image["resolved_at"]),
            image["registry_ref"])


def _newest_first(built_at: Optional[str]) -> str:
    '''A sort key putting the newest RFC 3339 time first and an unknown one last.'''
    if not built_at:
        return "~"                      # after every digit, dash and colon
    return "".join(chr(0x7e - (ord(c) - 0x20)) if 0x20 <= ord(c) < 0x7f else c
                   for c in built_at)


def plan_for_job(store, requires: Dict[str, Any],
                 node_tools: Dict[Tuple[str, str], Optional[str]],
                 inherits=None, job_image_id: Optional[str] = None,
                 python_nodes=()) -> Plan:
    '''Which image every node of this job runs in.

    🔴 A node no image can place fails the whole submit, before anything runs.
    ⚠️ Only called where containers run, so an empty registry refuses rather
    than falling back to the host. 🔴 ``python_nodes`` are also matched on
    `requested_versions.interpreter` (surface D293).
    '''
    images = live_images(store)
    software = live_software(store)
    python_nodes = set(python_nodes)
    interpreter = interpreter_requirement(requires)

    # 🔴 The python set alone decides the job image, picked at create and kept while live.
    pinned = declared_requirements(software, requires)
    job_image = next((image for image in images if image["id"] == job_image_id), None) \
        or resolve_declared(images, pinned)

    refs = {image["id"]: pinned_ref(image["registry_ref"], image["digest"])
            for image in images}

    inherits = inherits or {}
    held = software["tools"]
    failed: Dict[Requirement, List[Requirement]] = {}

    nodes: Dict[Tuple[str, str], Optional[str]] = {}
    for node, tool in node_tools.items():
        if not tool:
            # 🆕 A node declaring nothing that follows its input runs where that
            # input ran. ⚠️ Flowgraph order places the input first; one outside
            # this run falls back to the job's image.
            after = inherits.get(node)
            nodes[node] = (nodes.get(after) if node in inherits else None) \
                or job_image["id"]
            if interpreter and node in python_nodes:
                here = next(image for image in images if image["id"] == nodes[node])
                if not _satisfies(here, [interpreter]):
                    found = resolve(images, list(pinned) + [interpreter])
                    if found is None:
                        failed.setdefault(interpreter, list(pinned) + [interpreter])
                        continue
                    nodes[node] = found["id"]
            continue

        if tool not in held:
            # 🔴 Fatal: with containers the registry is the world, and placed
            # anywhere the node would die in the python-only image. ⚠️ The task
            # declares its tool (`runflow.node_tools`). Distinct from a tool
            # registered but in no image: different people fix the two.
            step, index = node
            raise ProblemError(
                "resource-unavailable", resource_kind="tool", resource=tool,
                detail=f"{step}/{index} runs {tool}, and no image on this server holds "
                       f"it -- this deployment runs every node in a container, so there "
                       f"is nowhere for it to run. {len(images)} image(s) are "
                       "registered, and an operator adds one with "
                       "'registry add-software' and 'registry add-image'")

        # 🔴 The python set plus this node's tool, `job_nodes.image_id`, per
        # node: tools need not share an image. ⚠️ Pinning narrows candidates
        # before any tie is broken.
        asked = ((requires or {}).get("tools") or {}).get(tool)
        wants = list(pinned) + ([interpreter] if interpreter and node in python_nodes
                                else []) + [Requirement(tool, specifiers(asked), "tool")]
        found = resolve(images, wants)
        if found is None:
            # 🔴 Kept, not raised: a job missing two tools reports both.
            failed.setdefault(wants[-1], wants)
            continue
        nodes[node] = found["id"]

    if failed:
        raise _unsatisfiable_tools(list(failed.values()), images)

    return Plan(job_image["id"], nodes, refs)


def interpreter_requirement(requires: Dict[str, Any]) -> Optional[Requirement]:
    '''`requested_versions.interpreter` as a Requirement, or None where the job sent none.'''
    asked = ((requires or {}).get(BUCKETS["interpreter"]) or {}).get(INTERPRETER)
    if asked is None:
        return None
    return Requirement(INTERPRETER, specifiers(asked), "interpreter")


def declared_requirements(software, requires: Dict[str, Any]) -> List[Requirement]:
    '''What the run's own Python process needs: the `python` bucket.

    🔴 One image must satisfy all of it, since these names share an interpreter.
    🔴 The framework is always this server's own version (:func:`own_version`).
    🔴 Computable without the upload, so create can resolve the image too.
    '''
    tracked = software["python"]
    asked = (requires or {}).get("python") or {}

    pinned = [Requirement(name, specifiers(wanted), "library")
              for name, wanted in sorted(asked.items())
              if name in tracked and isinstance(wanted, (str, int, float, list))]
    pinned.append(Requirement(PRIMARY, (f"=={own_version()}",), "library"))
    return pinned


def resolve_declared(images, requirements: Sequence[Requirement]):
    '''The one image the declared versions resolve to. Raises if none fits.'''
    if not images:
        raise _software_unavailable("unavailable", list(requirements) or
                                    [Requirement(PRIMARY, (), "library")], images)

    found = resolve(images, requirements)
    if found is None:
        raise _unsatisfiable(requirements, images)
    return found


def job_image_for(store, requires: Dict[str, Any]) -> Dict[str, Any]:
    '''The job's own image from `requested_versions.python` alone, picked at create.

    Surface §13; database D145. Raises the refusal create answers with.'''
    return resolve_declared(live_images(store),
                            declared_requirements(live_software(store), requires))


def contents_of(store, image_ids: Sequence[Optional[str]],
                interpreter_ids: Sequence[Optional[str]] = ()) -> Dict[str, List[str]]:
    '''Every version the given images declare, by distribution: what a job actually ran.

    The `interpreter` bucket holds only ``interpreter_ids``' Python (surface
    D293). ⚠️ A list per name: a wide flow's images may differ.
    '''
    wanted = {image_id for image_id in image_ids if image_id}
    interpreted = {image_id for image_id in interpreter_ids if image_id}
    if not wanted:
        return {}

    found: Dict[str, Dict[str, List[str]]] = {bucket: {} for bucket in BUCKETS.values()}

    def add(bucket, name, version):
        versions = found[bucket].setdefault(name, [])
        if version not in versions:
            versions.append(version)

    # A derived image is its base plus what its layer installed.
    for row in store.all(
            f"SELECT id, derived_from, installed FROM images WHERE derived_from IS NOT NULL "
            f"AND id IN ({', '.join('?' * len(wanted))})", tuple(wanted)):
        wanted.add(row["derived_from"])
        if row["id"] in interpreted:
            interpreted.add(row["derived_from"])
        for name, version in json.loads(row["installed"] or "[]"):
            add("python", canonical(name), version)

    for image in live_images(store):
        if image["id"] not in wanted:
            continue
        for entry in image["contents"]:
            bucket = BUCKETS.get(entry.kind, "tools")
            if bucket == BUCKETS["interpreter"] and image["id"] not in interpreted:
                continue
            add(bucket, canonical(entry.name) if bucket == "python"
                else entry.name.lower(), entry.version)

    if not any(found.values()):
        return {}
    # `python` and `tools` always, as `software` has them; `interpreter` where
    # a node ran the user's Python (surface §17).
    return {bucket: {name: sorted(versions) for name, versions in sorted(held.items())}
            for bucket, held in found.items()
            if bucket != BUCKETS["interpreter"] or held}


def _unsatisfiable(requirements: Sequence[Requirement], images) -> ProblemError:
    '''No live image holds the python set: `software-unavailable` with a `reason` (D110).

    ``unavailable`` lists every requirement no image satisfies alone;
    ``combination`` lists all of them when each exists but never together.
    ⚠️ Not `entitlement-denied`, nor `resource-unavailable` (never heard of).
    '''
    alone = [want for want in requirements if resolve(images, [want]) is None]
    if alone:
        return _software_unavailable("unavailable", alone, images)
    return _software_unavailable("combination", list(requirements), images)


def _unsatisfiable_tools(failures: Sequence[Sequence[Requirement]],
                         images) -> ProblemError:
    '''Every node tool no image could place, as one refusal, as :func:`_unsatisfiable`.'''
    unavailable = []
    for wants in failures:
        # The node's tool and interpreter: whichever no image holds is missing.
        for want in [want for want in wants if want.kind == "interpreter"] + [wants[-1]]:
            if resolve(images, [want]) is None and want not in unavailable:
                unavailable.append(want)
    if unavailable:
        return _software_unavailable("unavailable", unavailable, images)

    together: List[Requirement] = []
    for wants in failures:
        for want in wants:
            if want not in together:
                together.append(want)
    return _software_unavailable("combination", together, images)


def _software_unavailable(reason: str, unresolved: Sequence[Requirement],
                          images) -> ProblemError:
    entries = [{"kind": UNRESOLVED_KIND[want.kind], "name": want.name,
                "requirement": list(want.wanted or ()),
                "available": sorted({entry.version for image in images
                                     for entry in image["contents"]
                                     if entry.name == want.name})}
               for want in unresolved]

    unversioned = _present_but_unversioned(unresolved, images)
    if reason == "unavailable" and unversioned:
        # 🔴 Otherwise a mystery: `GET /v1` lists the name, so a preflight passed.
        detail = (f"this server has {unversioned.name}, and every image holding "
                  "it reports no version for it -- so nothing here can be matched "
                  "against a version requirement. Ask for it without a version, "
                  "or ask the operator to register the version its images hold")
    elif reason == "combination":
        detail = ("each of these is available on its own, and no single image "
                  "holds them together; choose versions that exist side by side")
    else:
        detail = (f"no image on this server holds "
                  f"{', '.join(str(want) for want in unresolved)}; "
                  f"{len(images)} image(s) are registered")

    return ProblemError("software-unavailable", reason=reason,
                        unresolved=entries, detail=detail)


def _present_but_unversioned(requirements: Sequence[Requirement], images):
    '''The first version-naming requirement whose name is held, but never with a version.'''
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

    🔴 Rebuilding a tag must not change what runs; only a re-registration may.
    '''
    from docker.utils import parse_repository_tag

    # Twice, since `repo:tag@digest` keeps its tag; a registry's port is kept.
    repository = parse_repository_tag(parse_repository_tag(registry_ref)[0])[0]
    return f"{repository}@{digest}"


def bundle_path(root, digest: str):
    '''Where the OCI bundle for one image lives: by digest, unpacked once for everybody.'''
    return Path(root) / digest.replace("sha256:", "")


def stage_bundle(root, ref: str, digest: str, mounts=()):
    '''Unpack one image into a bundle ``srun --container`` can run; returns its path.

    One implementation for all three callers, so bundles never differ. Built
    through ``.part`` and renamed: a lost race is the same bytes. ``mounts``
    go into the bundle's ``config.json``, not ``oci.conf``, which would apply
    to every container Slurm runs. Already staged is a no-op.
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
        # 🔴 `--rootless` only when unprivileged, not as a safety flag: its user
        # namespace without a uid map cannot mount /proc.
        unpack = ["umoci", "unpack", "--image", f"{layout}:sc", str(staging)]
        if os.geteuid() != 0:
            unpack.insert(2, "--rootless")

        subprocess.run(unpack, check=True)
        _prepare_spec(staging / "config.json", mounts)
        try:
            staging.rename(target)
        except OSError:
            if not is_staged(target):
                raise
    finally:
        shutil.rmtree(layout, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)

    return target


def sweep_bundles(root, store) -> int:
    '''Reclaim the unpacked bundles nothing can run any more; returns bytes.

    ⚠️ Superseded is not unused: a retired image an unfinished job names is
    kept, since `--container` points straight at it. A crashed unpack's
    `.part` and `.oci` directories go too.
    '''
    import shutil

    from siliconcompiler.remote.server.state.store import TERMINAL_STATES

    root = Path(root)
    if not root.is_dir():
        return 0

    # A derived bundle runs its base's root filesystem: live only with its base.
    keep = {row["digest"].replace("sha256:", "") for row in store.all(
        "SELECT i.digest FROM images i LEFT JOIN images b ON b.id = i.derived_from "
        "WHERE i.retired_at IS NULL AND (i.derived_from IS NULL OR b.retired_at IS NULL)")}

    # Anything an unfinished job or node might start in, retired or not, and its base.
    terminal = tuple(sorted(TERMINAL_STATES))
    live = f"j.state NOT IN ({', '.join('?' * len(terminal))})"
    busy = set()
    for row in store.all(
            "SELECT i.digest, b.digest AS base FROM images i "
            "LEFT JOIN images b ON b.id = i.derived_from WHERE ("
            f"  EXISTS (SELECT 1 FROM jobs j WHERE j.image_id = i.id AND {live})"
            "  OR EXISTS (SELECT 1 FROM job_nodes n JOIN jobs j ON j.id = n.job_id"
            f"             WHERE n.image_id = i.id AND {live}))", terminal * 2):
        busy.add(row["digest"].replace("sha256:", ""))
        if row["base"]:
            busy.add(row["base"].replace("sha256:", ""))

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


# Never held by a container's process (profile D39), though a containerised
# compute node needs NET_ADMIN for crun to bring up the build loopback.
WITHHELD_CAPABILITIES = ("CAP_NET_ADMIN",)


def drop_capabilities(spec) -> None:
    '''Take `WITHHELD_CAPABILITIES` out of every set an OCI spec grants.'''
    capabilities = (spec.get("process") or {}).get("capabilities") or {}
    for name, held in list(capabilities.items()):
        if isinstance(held, list):
            capabilities[name] = [cap for cap in held if cap not in WITHHELD_CAPABILITIES]


def _prepare_spec(config, mounts) -> None:
    '''Make the unpacked bundle runnable for a job on this cluster.

    Mounts at the same path inside as out, since the manifest names absolute
    server paths. 🔴 The network namespace is removed: the framework image must
    reach `slurmctld` to submit nodes, and tasks may need a licence server.
    '''
    with open(config) as f:
        spec = json.load(f)

    drop_capabilities(spec)

    # ⚠️ Slurm gives no terminal, and crun dies on "tcgetattr" if one is asked for.
    spec.setdefault("process", {})["terminal"] = False

    namespaces = spec.get("linux", {}).get("namespaces")
    if namespaces is not None:
        spec["linux"]["namespaces"] = [
            entry for entry in namespaces if entry.get("type") != "network"]

    _add_mounts(spec, mounts)

    with open(config, "w") as f:
        json.dump(spec, f)


def _add_mounts(spec, mounts) -> None:
    '''Bind each host path at the same path inside, once.'''
    existing = {entry.get("destination") for entry in spec.get("mounts", [])}
    for mount in mounts:
        # A path, read-write; or `(path, "ro")` for a root the server supplies.
        path, mode = (mount if isinstance(mount, (tuple, list)) else (mount, "rw"))
        path = str(path)
        if path in existing:
            continue
        existing.add(path)
        spec.setdefault("mounts", []).append({
            "destination": path,
            "source": path,
            "type": "none",
            "options": ["rbind", "ro" if mode == "ro" else "rw"],
        })


def _borrowed_root(spec, bundle, readonly: Optional[bool] = None) -> Dict[str, Any]:
    '''``spec``'s root filesystem as an absolute path, so another bundle can run it in place.'''
    root = spec.get("root") or {}
    where = Path(root.get("path") or "rootfs")
    return {"path": str((where if where.is_absolute() else Path(bundle) / where).resolve()),
            "readonly": bool(root.get("readonly", False)) if readonly is None else readonly}


def job_bundle(shared, target, mounts):
    '''One job's bundle: the shared root filesystem with this job's own mounts.

    🔴 What keeps the signing key and the store out of a job's view: a mount in
    a shared bundle would be every job's. ⚠️ ``target`` must be unwritable by
    any job, or a node could rewrite what the next one starts with.
    '''
    target = Path(target)
    with open(Path(shared) / "config.json") as f:
        spec = json.load(f)

    spec["root"] = _borrowed_root(spec, shared)
    _add_mounts(spec, mounts)

    write_json(target / "config.json", spec)
    return target


def read_bundle(shared, target, tree):
    '''A bundle for reading one job's manifest in its own image.

    🔴 The staging sandbox (implementation-notes §E; profile D63): every bind
    mount removed but ``tree``, read-only, and its own network namespace, so no
    credential, munge socket, PDK data, private root or network.
    '''
    target = Path(target)
    with open(Path(shared) / "config.json") as f:
        spec = json.load(f)

    spec["root"] = _borrowed_root(spec, shared, readonly=True)
    spec["mounts"] = [entry for entry in spec.get("mounts", []) if not _is_bind(entry)]
    # /tmp is the read's HOME, and the root filesystem is read-only.
    spec["mounts"].append({"destination": "/tmp", "type": "tmpfs", "source": "tmpfs",
                           "options": ["nosuid", "nodev", "size=256m"]})
    _add_mounts(spec, [(str(tree), "ro")])

    namespaces = spec.setdefault("linux", {}).setdefault("namespaces", [])
    if not any(entry.get("type") == "network" for entry in namespaces):
        namespaces.append({"type": "network"})

    write_json(target / "config.json", spec)
    return target


def _is_bind(entry) -> bool:
    options = entry.get("options") or []
    return entry.get("type") == "bind" or "bind" in options or "rbind" in options


######################################################################
# Derived images: a job's Python packages, layered on a node's image (§L)
######################################################################


def derivation(base_digest: str, requirements: str, constraints: str, wheels=(),
               constrain=(), indexes=(), source_builds: bool = False) -> str:
    '''The cache key of a derived image (implementation-notes §L).

    The index configuration is in it, since a package set means something else
    from another index; the base's Python is a function of its digest.'''
    import hashlib

    return hashlib.sha256(json.dumps(
        {"base": base_digest, "requirements": requirements, "constraints": constraints,
         "wheels": sorted(wheels), "constrain": sorted(set(constrain)),
         "indexes": list(indexes), "source_builds": bool(source_builds)},
        sort_keys=True).encode()).hexdigest()


def drop_built(store, name: str, version: Optional[str], actor: str,
               environments=None) -> List[str]:
    '''Stop reusing every environment built with ``name`` (at ``version``); returns what went.

    For a yanked or broken package: derived images are retired, host
    ``environments`` removed. The rows stay, so what a job ran in stays answerable.'''
    import shutil

    wanted = canonical(name)

    def holds(pairs) -> bool:
        return any(canonical(held) == wanted
                   and (version is None or normalize(found) == normalize(version))
                   for held, found in pairs)

    dropped = []
    for row in store.all("SELECT id, registry_ref, installed FROM images "
                         "WHERE derived_from IS NOT NULL AND retired_at IS NULL"):
        if holds(json.loads(row["installed"] or "[]")):
            retire_image(store, row["id"], actor)
            dropped.append(row["registry_ref"])

    root = Path(environments) if environments else None
    if root is not None and root.is_dir():
        for recorded in sorted(root.glob("*.json")):
            try:
                pairs = json.loads(recorded.read_text()).get("installed") or []
            except (OSError, ValueError):
                continue
            if holds(pairs):
                shutil.rmtree(recorded.with_suffix(""), ignore_errors=True)
                recorded.unlink(missing_ok=True)
                dropped.append(str(recorded.with_suffix("")))
    return dropped


def derived_image(store, base_id: str, key: str) -> Optional[Dict[str, Any]]:
    '''The live derived image for this base and key, or None.'''
    row = store.one("SELECT * FROM images WHERE derived_from = ? AND derivation = ? "
                    "AND retired_at IS NULL", (base_id, key))
    return dict(row) if row else None


def register_derived(store, base_id: str, registry_ref: str, digest: str, key: str,
                     installed: Sequence[Tuple[str, str]], note: str) -> str:
    '''Record an image the server built; returns its id.

    🔴 No `image_contents`, so no requirement resolves to it and `GET /v1` never lists it.
    '''
    if not _DIGEST.match(digest or ""):
        raise ValueError(f"{digest!r} is not a sha256 digest")
    # Two builds of one key: the first registered is the one reused.
    existing = store.one("SELECT id FROM images WHERE digest = ? OR "
                         "(derived_from = ? AND derivation = ? AND retired_at IS NULL)",
                         (digest, base_id, key))
    if existing is not None:
        return existing["id"]

    image_id = str(uuid.uuid4())
    with store.transaction():
        store.execute(
            "INSERT INTO images (id, registry_ref, digest, resolved_at, built_at, "
            "  registered_via, derived_from, derivation, installed, note) "
            "VALUES (?, ?, ?, ?, ?, 'derived', ?, ?, ?, ?)",
            (image_id, registry_ref, digest, now(), now(), base_id, key,
             json.dumps([list(pair) for pair in installed]), note))
    return image_id


def stage_derived_bundle(root, base_digest: str, digest: str, layer):
    '''The bundle a derived image runs as: its staged base's, with the layer at `IMAGE_SITE`.

    🔴 Not a second unpack of the base, so no tool-image copy per environment.
    '''
    import shutil

    base = bundle_path(root, base_digest)
    if not is_staged(base):
        raise RuntimeError(f"the base bundle {base} is not staged")
    target = bundle_path(root, digest)
    if is_staged(target):
        return target

    staging = target.with_name(target.name + ".part")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copytree(layer, staging / "layer", symlinks=True)

    with open(base / "config.json") as f:
        spec = json.load(f)
    spec["root"] = _borrowed_root(spec, base)
    # On the tool's PYTHONPATH only (`Task.get_runtime_environmental_variables`).
    spec.setdefault("mounts", []).append({
        "destination": IMAGE_SITE, "type": "bind", "source": str(target / "layer"),
        "options": ["rbind", "ro", "nosuid", "nodev"]})
    with open(staging / "config.json", "w") as f:
        json.dump(spec, f, indent=1)

    try:
        staging.rename(target)
    except OSError:
        if not is_staged(target):
            raise
        shutil.rmtree(staging, ignore_errors=True)
    return target


def is_staged(bundle) -> bool:
    '''Whether a bundle is there and complete: its ``config.json``, renamed in last.'''
    return (Path(bundle) / "config.json").is_file()


######################################################################
# Writing it
######################################################################

def driver_allowed(driver: str, allowed: Sequence[str] = ()) -> bool:
    '''Whether ``driver`` is a module this server will import (D95).

    🔴 The probe imports it on the server, so it is under ``siliconcompiler.tools``
    or named by configuration, never a free form field anyone could fill.
    '''
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", driver or ""):
        return False
    if driver == "siliconcompiler.tools" or driver.startswith("siliconcompiler.tools."):
        return True
    return driver in set(allowed or ())


def register_software(store, name: str, display_name: str, actor: str,
                      kind: str, driver: Optional[str] = None,
                      version_package: Optional[str] = None,
                      allowed_drivers: Sequence[str] = ()) -> str:
    '''Declare that this deployment curates images for a distribution; returns the kind.

    ⚠️ A claim with teeth: a job needing this tool with no image holding it is
    refused at submit. 🔴 `kind`, `driver` (the tool's Task module, handed to a
    probe) and `version_package` (where a driverless or exe-less tool's version
    comes from) are stated, never derived: this process is not the image.
    '''
    if kind not in KINDS:
        raise ValueError(
            f"{kind!r} is not a software kind; try "
            f"{' or '.join(KINDS)}")
    if kind == "interpreter" and name != INTERPRETER:
        raise ValueError(
            f"the interpreter kind has one name, {INTERPRETER}: the image's own "
            f"Python. {name} is not it")
    if driver and kind != "tool":
        raise ValueError(
            f"{name} is {kind} and names a task driver; a driver is what makes "
            "something a tool")
    if driver and not driver_allowed(driver, allowed_drivers):
        raise ValueError(
            f"{driver} is not a driver this server imports: a driver is a module "
            "under siliconcompiler.tools, or one named in this deployment's "
            "software_drivers")
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
    '''Register one exact version; returns the spelling stored.

    🔴 Exact in storage; the wire's specifiers are matched against these rows.
    🔴 Normalised here, not at request time, so client and server never disagree
    silently. ⚠️ ``published_date`` lets a tool reporting no version in,
    at the cost of never satisfying a version requirement.
    '''
    if store.one("SELECT name FROM software WHERE name = ?", (name,)) is None:
        raise ValueError(f"{name} is not registered software; add it first")
    if source not in ("reported", "published_date"):
        raise ValueError(f"{source} is not a version source")

    # 🔴 Refused, never coerced (`version_norm NOT NULL`): a parser fed odd
    # output returns anything (`initialize` from gtkwave), and a rewrite hides it.
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


def _contains(values: Optional[Sequence[str]]) -> List[Tuple[str, str]]:
    '''Parse ``name==version`` contents, as an operator writes them, for :func:`register_image`.

    ``==`` only: no ranges anywhere in this registry.
    '''
    pairs = []
    for value in values or []:
        name, sep, version = value.partition("==")
        if not sep or not name or not version:
            raise ValueError(f"{value!r} is not name==version")
        pairs.append((name.strip(), version.strip()))
    return pairs


def register_image(store, registry_ref: str, digest: str,
                   contents: Sequence[Tuple[str, str]], actor: str,
                   note: Optional[str] = None,
                   built_at: Optional[str] = None) -> str:
    '''Register a container this deployment may run.

    🔴 The most dangerous write in this schema: it chooses what code executes on
    the cluster, so it takes a person every time. ⚠️ ``built_at`` is from the
    image's manifest; NULL means unknown, not old.
    '''
    if not _DIGEST.match(digest or ""):
        raise ValueError(f"{digest!r} is not a sha256 digest")
    if not contents:
        raise ValueError("an image with no declared contents can satisfy nothing")

    # 🔴 Normalised as stored: `verilator 5.052` is stored as `5.52`.
    contents = [(name, normalize(version)) for name, version in contents]

    for name, version in contents:
        if store.one("SELECT version FROM software_versions "
                     "WHERE software_name = ? AND version = ?",
                     (name, version)) is None:
            raise ValueError(f"{name}=={version} is not a registered version")

    existing = store.one("SELECT id FROM images WHERE digest = ?", (digest,))
    image_id = existing["id"] if existing else str(uuid.uuid4())

    # 🔴 One live image per reference: a rebuilt tag supersedes (⚠️ retires, never
    # deletes) the build before it, or the resolution would pick arbitrarily.
    superseded = [row["id"] for row in store.all(
        "SELECT id FROM images WHERE registry_ref = ? AND digest <> ? "
        "  AND retired_at IS NULL", (registry_ref, digest))]

    with store.transaction():
        for old_id in superseded:
            store.execute(
                "UPDATE images SET retired_at = ?, retired_by = ? WHERE id = ?",
                (now(), actor, old_id))

        if existing:
            # The digest is the identity: same bytes, new tag or contents.
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
    '''Stop dispatching into it; ⚠️ the row stays, so *what did this run in* stays answerable.'''
    _retire(store, "images", "id = ?", (image_id,), actor)


def retire_version(store, name: str, version: str, actor: str) -> None:
    _retire(store, "software_versions",
            "software_name = ? AND version = ?", (name, version), actor)


def retire_software(store, name: str, actor: str) -> None:
    _retire(store, "software", "name = ?", (name,), actor)


def _retire(store, table: str, where: str, params, actor: str) -> None:
    '''Set ``retired_at`` and ``retired_by`` together, as each table's CHECK requires.'''
    with store.transaction():
        store.execute(
            f"UPDATE {table} SET retired_at = ?, retired_by = ? "
            f"WHERE {where} AND retired_at IS NULL",
            (now(), actor, *params))
