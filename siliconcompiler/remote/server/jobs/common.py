'''
What the job service's parts share: its constants, the small helpers kept
out of the class, and the exceptions staging raises.
'''

import base64
import json
import logging
import os
import re

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from siliconcompiler.flowgraph import Flowgraph
from siliconcompiler.remote import environment, owners
from siliconcompiler.remote.server.errors import bound, ERRORS, ProblemError, TYPE_BASE
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.staging import archive, manifestread
from siliconcompiler.remote.server.state.store import parse, stamp

logger = logging.getLogger("sc-server")


# `sha256` is the only algorithm v1 accepts, and the prefix is always written.
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

# 🔴 How often ONE process will ask the scheduler about ONE job, at most.
# Deliberately decoupled from `poll_interval_seconds`: reading a job is a local
# SQLite read and a stat, and can be answered as fast as anybody asks, while
# `squeue` is one or more RPCs into slurmctld and is the only part that leaves
# the machine. Without this, shortening the poll interval would multiply the
# load on slurmctld by the same factor.
SCHEDULER_QUERY_FLOOR = 5

# Job reuse returns a result the hash determines and never a refusal it does
# not: `rejected` is an entitlement decision about a person at a moment, and
# `cancelled` and `abandoned` are somebody having stopped.
REUSABLE_STATES = ("completed", "failed")

# What a job-stream request is told for each capability the deployment lacks,
# broadest first.
_WITHOUT = {
    "logs.stream": "this deployment does not serve a live log; each node's "
                   "log is an artifact once it finishes",
    "logs.stream.job": "this deployment does not merge a job's logs into one "
                       "stream; follow each running node instead",
}

# The two surfaces a caller reaches a job through. They disagree about exactly
# two things -- `max_download_bytes` and `api_fetchable_kinds` -- and both are
# decided from this one value.
SURFACES = ("api", "portal")

# Long enough for any real design or job name and short enough that the column,
# the path and the log line all stay sane.
MAX_NAME = 100

# A cancel's `reason`, at most (surface D288): refused above it, never cut, and
# served whole -- what is accepted is what everyone reads.
MAX_REASON = 300

# What a caller's reason may not hold: it is served as it arrived, so a control
# character is refused at the boundary rather than stripped on the way out.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# `design` and `jobname`, which become path segments under the job's own root
# (see `_name`). The manifest's own copies are checked again at submit against
# the same rule -- an upload is the other end of this.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# How long an `Idempotency-Key` is honoured (surface §6).
IDEMPOTENCY_SECONDS = 24 * 3600


# Node archives already reported as sitting over a member deleted on its own,
# so a client polling the listing does not raise the same alert every second.
_ALERTED: Set[str] = set()


class _Supply:
    '''What this server can supply by IDENTITY, never by a path a job names.'''

    def __init__(self, config, sources):
        self._config = config
        self._sources = sources

    def package(self, module: str) -> bool:
        '''Whether this installation has ``module``, asked without importing
        anything a job named (contract §1).

        ⚠️ `find_spec` on a dotted name imports its parent first, so only a
        top-level name is looked up -- which runs nothing -- and a submodule is
        answered only once its parent is already loaded here.
        '''
        import importlib.util
        import sys

        top, _, rest = module.partition(".")
        if not top.isidentifier() or (rest and top not in sys.modules):
            return False
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            return False

    def private_root(self, keypath) -> Optional[str]:
        '''This server's own copy of a private dataroot, by its keypath: a
        library's from `library`, and a task's from `task` for that one task,
        else from `tool` for every task of the tool.'''
        if not owners.is_dataroot_keypath(keypath):
            return None
        mapped = self._config["private_dataroots"] or {}
        if keypath[0] == "library":
            _, name, _, root = keypath
            return ((mapped.get("library") or {}).get(name) or {}).get(root)
        _, tool, _, task, _, root = keypath
        return (((mapped.get("task") or {}).get(tool) or {}).get(task) or {}).get(root) \
            or ((mapped.get("tool") or {}).get(tool) or {}).get(root)

    def held(self, source, ref) -> Optional[str]:
        # Nothing is held on a server that fetches nothing: a copy left from
        # before would supply the job and skip the path it exists to test.
        if self._config["fetch_fails"]:
            return None
        return self._sources.held(source, ref)

    def allowlisted(self, source, ref) -> bool:
        # 🔴 A source whose query values were masked on the way here
        # (`?token=***`) says what it is, not enough to be fetched from: it is
        # never fetched, so the client is asked for it instead.
        if owners.is_masked(source):
            return False
        return self._sources.allowlisted(source, ref)


######################################################################
# Small things, kept out of the class
######################################################################

def requirements(descriptor: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """What a job needs from its image, by bucket:
    `descriptor.requested_versions`.

    🔴 **The one member, and it names every Python distribution the job
    imports**, pinned exactly -- a name not in `requested_versions` is not
    required, and the job may land in an image without it. There is no
    `versions` member and no fallback to one (D126, superseded).

    🔴 **Each value is a LIST of PEP 440 specifier sets, any one of which
    satisfies**, and a bare string is refused: that is what SiliconCompiler
    means by a version requirement -- `Task.get('version')` is a list, and two
    tasks of one tool contribute two entries. `[]` is *any version*, which is
    not the same as leaving the name out.

    🔴 **By bucket, and a flat map is refused.** The whole `python` set
    shares an interpreter and must be held by ONE image, while a tool is
    satisfied per node; accepting a flat map would mean guessing which.
    """
    from siliconcompiler.remote.server.software.images import BUCKETS, INTERPRETER

    buckets = tuple(BUCKETS.values())
    found: Dict[str, Dict[str, Any]] = {bucket: {} for bucket in buckets}

    given = descriptor.get("requested_versions")
    if given is None:
        return found
    if not isinstance(given, dict):
        raise ProblemError("invalid-request", detail="requested_versions must be an object")

    unknown = set(given) - set(buckets)
    if unknown:
        raise ProblemError(
            "invalid-request",
            detail=f"requested_versions is keyed on {', '.join(buckets)}; "
                   f"{', '.join(sorted(unknown))} is none of them")

    for bucket in buckets:
        inner = given.get(bucket)
        if inner is None:
            continue
        if not isinstance(inner, dict):
            raise ProblemError(
                "invalid-request",
                detail=f"requested_versions.{bucket} must be an object of name to "
                       "requirement")
        if bucket == BUCKETS["interpreter"] and set(inner) - {INTERPRETER}:
            raise ProblemError(
                "invalid-request",
                detail=f"requested_versions.interpreter has one name, {INTERPRETER}")
        for name, wanted in inner.items():
            if not isinstance(wanted, list) or not all(isinstance(one, str) for one in wanted):
                raise ProblemError(
                    "invalid-request",
                    detail=f"requested_versions.{bucket}.{name} is a list of specifier "
                           "sets, even with one entry; a bare string is not")
        found[bucket] = dict(inner)

    return found


# 🔴 Strict on requests (contract.md): what each body may carry. `run_hash` is
# job reuse's, and top level: the descriptor is what submit re-derives.
CREATE_MEMBERS = ("design", "jobname", "project", "descriptor", "run_hash", "continues_from",
                  "python_packages")
DESCRIPTOR_MEMBERS = ("flow", "node_count", "needs", "requested_versions", "sources")
SOURCE_MEMBERS = ("keypath", "source", "ref", "private")


def _only(body: Dict[str, Any], allowed, where: str) -> None:
    '''An unknown member is refused, never ignored: a misspelled optional
    member would otherwise be a check the caller believes they asked for.'''
    unknown = sorted(set(body) - set(allowed))
    if unknown:
        raise ProblemError(
            "invalid-request",
            detail=f"{where} has no member {unknown[0]!r}; it takes "
                   f"{', '.join(allowed)}")


def _name(value, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProblemError("invalid-request", detail=f"{field} is required")
    if len(value) > MAX_NAME or not _NAME_RE.match(value):
        # Both of these become a path segment under the job's own root, so the
        # check is not cosmetic: it is the reason a manifest cannot name its way
        # out of the directory the server gave it.
        raise ProblemError(
            "invalid-request",
            detail=f"{field} must be at most {MAX_NAME} characters of "
                   "letters, digits, '.', '_' and '-'")
    return value


_RUN_HASH = re.compile(r"^[\x20-\x7e]{1,128}$")


def _extract_outputs(archive_path: Path, tree: Path, step: str, index: str, limits,
                     only: Optional[str] = None) -> None:
    '''The ``outputs/`` of a node archive -- or the one member ``only``
    names -- into ``tree``, at ``<step>/<index>/``, under an upload's rules:
    its links kept, bounded by the job's tree rather than the node's.'''
    def wanted(name):
        if only is not None:
            return name == only or only.startswith(f"{name}/") or name.startswith(f"{only}/")
        return name == "outputs" or name.startswith("outputs/")

    tree.mkdir(parents=True, exist_ok=True)
    archive.extract(archive_path, tree, limits, prefix=f"{step}/{index}", select=wanted)


def _link_home(tree: Path, link: Path):
    '''Where a link under ``tree`` points, as ``((step, index), member)``
    with ``member`` relative to that node -- or None where it is not a node's
    ``outputs/``.'''
    target = os.readlink(link)
    if os.path.isabs(target):
        return None
    joined = os.path.normpath(os.path.join(os.path.dirname(os.path.relpath(link, tree)),
                                           target))
    parts = joined.replace(os.sep, "/").split("/")
    if len(parts) < 4 or parts[2] != "outputs" or os.pardir in parts:
        return None
    return (parts[0], parts[1]), "/".join(parts[2:])


def _python_packages(member) -> Optional[environment.Packages]:
    '''`python_packages`, held to its grammar and bounds; None where it is
    absent or lists nothing. `400 invalid-request`, naming the entry.'''
    if member is None:
        return None
    try:
        packages = environment.parse(member)
    except environment.PackagesError as e:
        raise ProblemError("invalid-request", detail=f"python_packages: {e}") from None
    return packages if packages.requirements or packages.constraints else None


def _continuations(value) -> List[Tuple[str, str, str]]:
    '''`continues_from`: a list of `{step, index, job_id}`, one per node.'''
    import uuid

    if value is None:
        return []
    if not isinstance(value, list):
        raise ProblemError("invalid-request",
                           detail="continues_from is a list of {step, index, job_id}")
    found, seen = [], set()
    for entry in value:
        if not isinstance(entry, dict):
            raise ProblemError("invalid-request",
                               detail="each continues_from entry is {step, index, job_id}")
        _only(entry, ("step", "index", "job_id"), "a continues_from entry")
        step, index, job = entry.get("step"), entry.get("index"), entry.get("job_id")
        if not all(isinstance(value, str) and value for value in (step, index, job)):
            raise ProblemError("invalid-request",
                               detail="each continues_from entry names a step, an index "
                                      "and a job_id")
        try:
            uuid.UUID(job)
        except ValueError:
            raise ProblemError("invalid-request",
                               detail=f"continues_from names {job!r}, which is not a job "
                                      "id") from None
        try:
            # The same node-name check SiliconCompiler applies to a flow.
            Flowgraph.check_node_name(step, index)
        except ValueError as e:
            raise ProblemError("invalid-request", detail=f"continues_from: {e}") from None
        if (step, index) in seen:
            raise ProblemError("invalid-request",
                               detail=f"two continues_from entries name {step}/{index}")
        seen.add((step, index))
        found.append((step, index, job))
    return found


def _run_hash(value) -> Optional[str]:
    '''An opaque string of 1 to 128 printable ASCII characters, or absent.'''
    if value is None:
        return None
    if not isinstance(value, str) or not _RUN_HASH.match(value):
        raise ProblemError("invalid-request",
                           detail="run_hash is an opaque string of 1 to 128 printable "
                                  "ASCII characters")
    return value


def _resources(summary) -> List[Tuple[str, str]]:
    '''The PDK, libraries and FPGA device a job's flow needs, as
    ``(resource_kind, name)``, in the order a refusal names them.'''
    return (([("pdk", summary["pdk"])] if summary["pdk"] != "none" else []) +
            [("library", name) for name in summary["libraries"]] +
            ([("fpga", summary["fpga"])] if summary.get("fpga") else []))


def _declared_sources(descriptor) -> Optional[List[Dict[str, Any]]]:
    '''The descriptor's `sources`, checked, with every query value masked --
    or None where there are none.

    `private` is OPTIONAL and defaults to false. A private entry carries
    `source` and `ref` where its dataroot has a remote one (surface D308),
    masked here as any other's; a local one has neither.
    '''
    declared = descriptor.get("sources")
    if declared is None:
        return None
    if not isinstance(declared, list):
        raise ProblemError("invalid-request", detail="sources is a list")
    checked, seen = [], set()
    for item in declared:
        if not isinstance(item, dict):
            raise ProblemError("invalid-request",
                               detail="each source is an object: {keypath}, with an "
                                      "optional source, ref and private")
        _only(item, SOURCE_MEMBERS, "a source")
        keypath = item.get("keypath")
        # 🔴 One of the two places SiliconCompiler keeps a dataroot, and
        # nothing else: this server does not guess what owns one (surface
        # D298).
        if not owners.is_dataroot_keypath(keypath) or \
                any(len(part) > MAX_NAME for part in keypath):
            raise ProblemError(
                "invalid-request",
                detail="a source's keypath is a library's dataroot, [\"library\", name, "
                       "\"dataroot\", root], or a task's, [\"tool\", tool, \"task\", task, "
                       "\"dataroot\", root]")
        if not isinstance(item.get("private", False), bool):
            raise ProblemError("invalid-request", detail="a source's private is true or false")
        where = owners.shown(keypath)
        if tuple(keypath) in seen:
            raise ProblemError("invalid-request", detail=f"sources names {where} twice")
        seen.add(tuple(keypath))
        # A private entry may carry its source and ref (surface D299): a copy
        # this server holds, or a fetch, supplies it as well as the operator's
        # copy does. `private` is what says it is never uploaded or asked for.
        private = item.get("private", False)
        entry = {"keypath": list(keypath), "private": private}
        if isinstance(item.get("source"), str):
            # 🔴 Refused, never stripped (surface D310): no client sends
            # userinfo, so one that did is told which entry -- by its keypath in
            # `detail`, never the value, which is neither stored nor logged.
            if owners.has_userinfo(item["source"]):
                raise ProblemError(
                    "invalid-request",
                    detail=f"{where}: a source carries no userinfo -- no user name and "
                           "no secret ahead of its host")
            # Masked again, as the client masks it (`Resolver.safe_source`): a
            # query's token a client sent anyway is neither stored nor logged.
            try:
                entry["source"] = owners.masked(item["source"])
            except ValueError:
                raise ProblemError("invalid-request",
                                   detail=f"{where}: source is not a URL") from None
        if isinstance(item.get("ref"), str):
            entry["ref"] = item["ref"]
        checked.append(entry)
    return checked


def _python_names(job) -> List[str]:
    '''What the job's `requested_versions.python` names: the image holds each, and
    none is ever installed. Part of what a derived image is keyed on.'''
    from siliconcompiler.remote.server.software.images import BUCKETS

    return sorted(requirements(json.loads(job["descriptor"] or "{}") or {})
                  [BUCKETS["python"]])


def _same_version(one: str, other: str) -> bool:
    '''Whether two versions are one, as PEP 440 compares them.'''
    from packaging.version import InvalidVersion, Version

    try:
        return Version(one) == Version(other)
    except InvalidVersion:
        return one == other


# The states a cancel moves a job into, whose reason is the caller's.
_CANCELS = ("cancelling", "cancelled")


class _NoLongerStaging(Exception):
    '''The job left `staging` while it was being prepared.'''


class _Absent(Exception):
    '''Packages the job is sent back for, as ``(name, why)``: a version no
    configured index lists, or one it offers only as a source.'''

    def __init__(self, asked):
        self.asked = list(asked)
        super().__init__(", ".join(name for name, _ in self.asked))


def _install_lines(record, where: str) -> List[str]:
    '''What an install of the job's Python packages did, for the job-level
    log: what it added, what it substituted within a release line, and each
    listed version the target's own copy was kept over.'''
    added = ", ".join(f"{name}=={version}" for name, version in record.get("installed") or [])
    lines = [f"The job's Python packages, on {where}: installed "
             f"{added or f'nothing beyond what {where} holds'}"]
    yanked = set(record.get("yanked") or [])
    lines += [(f"{name}=={asked} is yanked on its index, so {got} from its release line was "
               "installed instead") if name in yanked else
              (f"{name}=={asked} does not install on {where}; {got} from its release line "
               "was installed instead")
              for name, (asked, got) in sorted((record.get("substituted") or {}).items())]
    ignored = record.get("ignored") or {}
    if ignored:
        kept = ", ".join(f"{name} {held} (listed {listed})"
                         for name, (listed, held) in sorted(ignored.items()))
        lines.append(_bounded(f"{where} holds {len(ignored)} listed distribution(s) at "
                              f"another version, which stays: {kept}"))
    return lines


class _ServerFailure(Exception):
    '''This server's own failure while staging: `staging-failed`, its message
    the `detail`.'''


class _StagingTimedOut(Exception):
    '''This pass of staging ran past the caller's `max_staging_seconds`:
    `staging-timed-out`, the job's own limit (surface D294). Its message says
    what staging was doing when the time ran out.'''


# The run's final manifest, read once as plain JSON for its metrics: larger
# than this is left unread, since the panel is not worth parsing gigabytes.
METRICS_MANIFEST_BYTES = 256 * 1024 * 1024
# Each value kept for the panel, bounded as `detail` is.
_METRIC_VALUE_CHARS = 1000


def _node_metrics(manifest: Path) -> Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]]:
    '''``{(step, index): (metrics, records)}`` out of a run's final manifest,
    read as plain JSON. Empty where there is none, or it is too large or not
    JSON.'''
    try:
        if manifest.stat().st_size > METRICS_MANIFEST_BYTES:
            logger.info(f"{manifest} is too large to read its metrics from")
            return {}
        with open(manifest, "rb") as f:
            body = json.loads(f.read(METRICS_MANIFEST_BYTES + 1))
    except (OSError, ValueError):
        return {}
    if not isinstance(body, dict):
        return {}

    def value_of(held):
        value = held.get("value") if isinstance(held, dict) else None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        text = json.dumps(value) if not isinstance(value, str) else value
        return text[:_METRIC_VALUE_CHARS]

    found: Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for section, slot in (("metric", 0), ("record", 1)):
        params = body.get(section)
        if not isinstance(params, dict):
            continue
        for name, param in params.items():
            if name.startswith("__") or not isinstance(param, dict):
                continue
            nodes = param.get("node")
            if not isinstance(nodes, dict):
                continue
            for step, indexes in nodes.items():
                if not isinstance(indexes, dict) or step in ("global", "default"):
                    continue
                for index, held in indexes.items():
                    value = value_of(held)
                    if value is None or index in ("global", "default"):
                        continue
                    found.setdefault((str(step), str(index)), ({}, {}))[slot][name] = value
    return found


def _problem_from(outcome: Dict[str, Any]) -> ProblemError:
    '''The refusal a read reported, with only the members its type carries.

    🔴 **A read's members are written by whatever the manifest made the read
    do**, so each is taken by name and shape, never passed through: a member
    called `status` or `type` would otherwise be a field of the problem body.
    '''
    members: Dict[str, Any] = {}
    given = outcome.get("members") or {}
    if outcome["type"] == "software-unavailable":
        # A read refuses software only as `unknown_class`: a task class.
        members["unresolved"] = [
            {"kind": "class", "name": str(item.get("name"))[:manifestread.MAX_NAME],
             "requirement": [], "available": []}
            for item in (given.get("unresolved") or [])[:100] if isinstance(item, dict)]
    if outcome["type"] == "resource-unresolved":
        kind = given.get("resource_kind")
        members["resource_kind"] = kind if kind in owners.RESOURCE_KINDS else "pdk"
    if outcome.get("reason"):
        members["reason"] = outcome["reason"]
    return ProblemError(outcome["type"], detail=_bounded(outcome.get("detail") or ""),
                        **members)


def _sent_back_for(result: Dict[str, Any], packages=None) -> List[Tuple[str, str]]:
    '''What an install sends the job back for, each with the probe's finding.'''
    listed = {}
    for pin in (packages.requirements + packages.constraints) if packages else ():
        listed[environment.canonical(pin.name)] = pin.version
    asked = [(name, f"no index this server installs from lists {name}"
              + (f" at {listed[name]}" if name in listed else ""))
             for name in result.get("absent") or []]
    asked += [(name, "an index this server installs from offers it only as a source "
                     "distribution, and this deployment builds none")
              for name in result.get("source_only") or []]
    return asked


def _build_refusal(packages, result: Dict[str, Any], where: str = "") -> ProblemError:
    '''What an install that will not resolve tells the job's owner: each
    package, its version, and the target Python and platform.'''
    target = f"{result.get('python') or 'its Python'} ({result.get('version') or '?'}) " \
             f"on {result.get('platform') or 'its platform'}"

    named = list(result.get("unresolved") or []) or \
        [str(pin) for pin in packages.requirements]
    unresolved = []
    for requirement in named:
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?(.*)$", requirement)
        name, spec = (match.group(1), match.group(3).strip()) if match else (requirement, "")
        unresolved.append({"kind": "package", "name": environment.canonical(name),
                           "requirement": [spec] if spec else [], "available": []})

    refused = result.get("refused") or []
    only_source = result.get("only_source") or []
    tail = "\n".join((result.get("tail") or "").splitlines()[-5:])
    return ProblemError(
        "software-unavailable", reason="uninstallable", unresolved=unresolved,
        detail=_bounded(
            f"the job's Python packages will not install{where} for {target}: "
            f"{', '.join(named) or 'the uploaded wheels'}"
            # 🔴 Said, because it is the one the user can act on (surface
            # D291): a compiled package with no wheel for this platform needs
            # one published to the deployment's index.
            + (f"; {', '.join(only_source)} has only a source distribution for it, "
               "and this deployment builds none: publish a wheel for this platform "
               "to its index" if only_source else "")
            + (f"; the build was refused {', '.join(refused)}, which the index "
               "allowlist does not name" if refused else "")
            + (f"\n{tail}" if tail else "")))


def _bounded(text: str, limit: int = 1000) -> str:
    '''A transition reason, no longer than a page shows.'''
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _after(when: str, seconds: int) -> str:
    """`seconds` after a stored timestamp, in the format the store writes.

    🔴 Milliseconds, three digits, exactly as `store.now()` writes them. These
    are compared as STRINGS against stored timestamps, so a fraction of the
    wrong length does not compare wrong by a rounding error -- it compares
    wrong by character: `.12Z` sorts after `.123Z`, because `Z` is above `3`.
    """
    from datetime import timedelta

    try:
        moment = parse(when)
    except ValueError:
        # Unreadable is not a licence to abandon somebody's job.
        return "9999-12-31T23:59:59.999Z"
    return stamp(moment + timedelta(seconds=seconds))


def _ago(seconds: int) -> str:
    """The timestamp `seconds` ago, in the one format this store writes.

    A string comparison, because that is what the column holds and what `now()`
    produces -- RFC 3339 in UTC to milliseconds sorts lexically.
    """
    from datetime import datetime, timedelta, timezone

    return stamp(datetime.now(timezone.utc) - timedelta(seconds=seconds))


def _expired_key(bound_at: Optional[str]) -> bool:
    '''Whether a key bound at ``bound_at`` is past the time it is honoured.'''
    return bool(bound_at) and bound_at < _ago(IDEMPOTENCY_SECONDS)


def _error(error_type: Optional[str],
           detail: Optional[str] = None,
           members: Optional[str] = None) -> Optional[Dict[str, Any]]:
    '''A job's error, as an RFC 9457 object.

    🔴 `detail` is what makes it worth reading. `type` and `title` are frozen
    and identical on every deployment and for every occurrence -- *The run
    failed* is true of every failed run there has ever been -- so without a
    `detail` the object says only that something went wrong, which the `state`
    already said.

    ⚠️ Bounded like every other `detail`, and this is the path that needs it
    most: a run's reason can be a tool's own exception text, which carries
    whatever paths the client's design named. It does not pass through
    `problem()`, so the bound is applied here rather than inherited.

    A node's error has the same shape (surface §17, *A node's `error`*). A
    node has no transitions to carry its `detail`, so it arrives in
    ``members`` beside the type's own, and is bounded the same way.
    '''
    if not error_type:
        return None
    slug = error_type.rsplit("/", 1)[-1]
    registered = ERRORS.get(slug)
    title = registered.title if registered else "The job failed"

    extra = json.loads(members) if members else {}
    detail = detail or extra.pop("detail", None)

    body = {"type": error_type, "title": title}
    # The registry's status, and none for a type that is never a response.
    if registered is not None and registered.status is not None:
        body["status"] = registered.status
    # Prose that only repeats the slug is not prose: the slug is already the
    # `type`, and a client branches on that.
    if detail and detail != slug:
        body["detail"] = bound(detail)
    for name, value in extra.items():
        body.setdefault(name, value)
    return body


def _node_error(state: str, node: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    '''A node's error, as its `type` URI and the members beside it, from what
    the runner reported of it: ``(None, None)`` unless it failed.

    🔴 **`run-interrupted` where the environment ended it** -- an image that
    would not pull, before the flow started -- so resubmitting unchanged may
    work; **`run-failed` otherwise**, a time or memory limit included, with
    `detail` naming the limit (surface §17). A plain failure names its exit
    status and points at the node's log, which is where the tool said why.
    '''
    if state != "failed":
        return None, None
    interrupted = node.get("interrupted")
    if isinstance(interrupted, dict):
        slug = "run-interrupted"
        detail = (f"the node could not start: its image {interrupted.get('image')} "
                  "could not be pulled")
    elif node.get("limit"):
        slug = "run-failed"
        detail = f"the node exceeded its {node['limit']} limit"
    else:
        slug = "run-failed"
        code = runspec.exit_code(node.get("exit_code"))
        detail = (f"the node's task exited with status {code}; its log says why"
                  if code else "the node's task failed; its log says why")
    return f"{TYPE_BASE}/{slug}", _members_json({"detail": detail})


def _members_json(members: Dict[str, Any]) -> Optional[str]:
    '''A refusal's extension members, for the job's `error` to carry.'''
    return json.dumps(members, sort_keys=True) if members else None


def _flag(value, name: str) -> bool:
    '''A boolean query parameter: `true` or `false`, as S §16 defines one,
    and anything else `invalid-request` (S §6) -- never read as false, which
    would answer a filter the caller did not ask for.'''
    if value == "true":
        return True
    if value == "false":
        return False
    raise ProblemError("invalid-request", detail=f"{name} is true or false")


def _limit(value) -> int:
    if value is None:
        return 50
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise ProblemError("invalid-request", detail="limit must be a number") from None
    return max(1, min(limit, 200))


def _encode_cursor(row) -> str:
    raw = f"{row['created_at']}|{row['id']}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> Tuple[str, str]:
    '''Opaque on the wire, and refused rather than guessed at.

    A cursor is only ever taken from a `Link` header, so one that does not
    decode was made up -- and continuing from a made-up position would silently
    skip rows.
    '''
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, _, job_id = base64.urlsafe_b64decode(padded).decode().partition("|")
    except Exception:                                           # noqa: BLE001
        raise ProblemError("invalid-cursor") from None

    if not created_at or not job_id:
        raise ProblemError("invalid-cursor")
    return created_at, job_id


def _from_epoch(value: float) -> str:
    from datetime import datetime, timezone
    return stamp(datetime.fromtimestamp(value, timezone.utc))
