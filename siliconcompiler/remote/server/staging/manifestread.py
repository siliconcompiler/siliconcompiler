'''
The one place a job's manifest is read: a process of its own, while the job
stages, whose only output is a data summary.

``python3 -m siliconcompiler.remote.server.staging.manifestread <request>``

Contract §1: no server process holding credentials parses a manifest, since
reading one resolves whatever classes the uploader named. So the read runs
here, from ``sc-server``'s own SiliconCompiler (profile §5), given only
:func:`request`'s data and no path to the data directory, key, store or
private roots. Its summary is untrusted input, held to :func:`validate`.

It contains itself as far as the host allows (:func:`contain`; profile §5,
implementation-notes §E); in the job's container, the container is the
boundary. Where nodes run on the host there is no filesystem boundary: this
profile makes no security claim (§0).
'''

import json
import os
import sys
import time

from typing import Any, Dict, List

__all__ = ["SUMMARY_VERSION", "Invalid", "request", "validate", "read", "contain", "main"]


# A shape change is a new number; an unknown one is a malformed summary.
SUMMARY_VERSION = 4

# The manifest controls what this process writes, so the summary is capped
# whole and per field as it is read back.
MAX_SUMMARY_BYTES = 16 * 1024 * 1024
MAX_STRING = 4096
# `manifest_flow` and `manifest_pdk` are columns (database D145).
MAX_NAME = 200
MAX_NODES = 100_000
MAX_VALUES = 500_000
MAX_KEY_PARTS = 32

# What a read may refuse a job for, and the reasons each may carry.
OUTCOMES = {
    "archive-rejected": ("invalid_manifest", "breakpoint", "interactive_task"),
    "declared-mismatch": (None,),
    "software-unavailable": ("unknown_class",),
    "resource-unresolved": (None,),
}

_ORIGINS = ("local", "editable", "installed", "remote", "private")


class Invalid(ValueError):
    '''A summary that does not hold to its shape: the manifest was not read.'''


def _outputs_manifests(tree) -> List[str]:
    '''Each manifest under `<step>/<index>/outputs/` in ``tree``, relative, never through a link.'''
    found = []
    for step in sorted(set(_dirs(tree)) - {"sc_collected_files"}):
        for index in sorted(_dirs(os.path.join(tree, step))):
            outputs = os.path.join(tree, step, index, "outputs")
            if os.path.islink(outputs) or not os.path.isdir(outputs):
                continue
            for name in sorted(os.listdir(outputs)):
                path = os.path.join(outputs, name)
                if name.endswith(".pkg.json") and not os.path.islink(path) \
                        and os.path.isfile(path):
                    found.append(os.path.join(step, index, "outputs", name))
    return found


def _dirs(where) -> List[str]:
    '''The directories directly in ``where``, never a link to one.'''
    try:
        return [entry.name for entry in os.scandir(where)
                if entry.is_dir(follow_symlinks=False)]
    except OSError:
        return []


def request(tree, design: str, jobname: str, requires_siliconcompiler=None,
            skipped=()) -> Dict[str, Any]:
    '''What the server hands the read, as data.'''
    return {"tree": str(tree), "design": design, "jobname": jobname,
            "requires_siliconcompiler": list(requires_siliconcompiler or []),
            "skipped": sorted([list(node) for node in skipped])}


def validate(summary: Any) -> Dict[str, Any]:
    '''``summary`` held to its shape and bounds, or :class:`Invalid`.

    Every node name goes through the one node-name check before it reaches
    a column, a path or a URL (implementation-notes §E).
    '''
    from siliconcompiler.flowgraph import Flowgraph
    from siliconcompiler.remote import owners

    def fail(why):
        raise Invalid(why)

    def text(value, what, limit=MAX_STRING, optional=False):
        if value is None and optional:
            return None
        if not isinstance(value, str) or len(value) > limit:
            fail(f"{what} is not a string of at most {limit} characters")
        return value

    def node(value, what):
        if not isinstance(value, list) or len(value) != 2:
            fail(f"{what} is not a [step, index] pair")
        step, index = text(value[0], what, MAX_NAME), text(value[1], what, MAX_NAME)
        try:
            Flowgraph.check_node_name(step, index)
        except ValueError as e:
            fail(f"{what} names a node that is not one: {e}")
        return (step, index)

    def listed(value, what, limit):
        if not isinstance(value, list) or len(value) > limit:
            fail(f"{what} is not a list of at most {limit} entries")
        return value

    if not isinstance(summary, dict) or summary.get("summary") != SUMMARY_VERSION:
        fail("the read returned no summary this server understands")

    outcome = summary.get("outcome")
    if outcome is not None:
        if not isinstance(outcome, dict) or outcome.get("type") not in OUTCOMES:
            fail("the read's outcome is not one this server knows")
        if outcome.get("reason") not in OUTCOMES[outcome["type"]]:
            fail("the read's outcome carries a reason its type does not have")
        text(outcome.get("detail"), "the outcome's detail", optional=True)
        members = outcome.get("members") or {}
        if not isinstance(members, dict) or len(json.dumps(members)) > MAX_STRING:
            fail("the outcome's members are not a small object")

    text(summary.get("design"), "design", MAX_NAME, optional=True)
    text(summary.get("jobname"), "jobname", MAX_NAME, optional=True)
    text(summary.get("flow"), "flow", MAX_NAME, optional=True)
    text(summary.get("pdk"), "pdk", MAX_NAME, optional=True)
    text(summary.get("fpga"), "fpga", MAX_NAME, optional=True)

    nodes = summary.get("nodes")
    if nodes is not None:
        for entry in listed(nodes, "nodes", MAX_NODES):
            if not isinstance(entry, dict):
                fail("a node is not an object")
            node([entry.get("step"), entry.get("index")], "a node")
            text(entry.get("task"), "a node's task class", optional=True)
            text(entry.get("tool"), "a node's tool", MAX_NAME, optional=True)
            if not all(isinstance(entry.get(flag), bool) for flag in ("inherits", "python")):
                fail("a node's inherits and python are not booleans")

    for edge in listed(summary.get("edges") or [], "edges", MAX_NODES * 4):
        if not isinstance(edge, list) or len(edge) != 4:
            fail("an edge is not [from_step, from_index, to_step, to_index]")
        node(edge[:2], "an edge"), node(edge[2:], "an edge")
    for entry in listed(summary.get("upstream") or [], "upstream", MAX_NODES):
        node(entry, "an upstream node")

    for name in listed(summary.get("libraries") or [], "libraries", 1000):
        text(name, "a library", MAX_NAME)
    for name in listed(summary.get("tools") or [], "tools", 1000):
        text(name, "a tool", MAX_NAME)

    required = summary.get("required")
    if required is not None:
        for key in listed(required, "required", MAX_VALUES):
            _key(key, fail, text)

    # Keypaths only: the read never reports the value (surface D302).
    for key in listed(summary.get("credentials") or [], "credentials", MAX_VALUES):
        _key(key, fail, text)

    for record in listed(summary.get("values") or [], "values", MAX_VALUES):
        if not isinstance(record, dict):
            fail("a value is not an object")
        _key(record.get("key"), fail, text)
        for field in ("step", "index", "name", "dataroot", "path", "collected_path",
                      "collected", "source", "ref", "package"):
            text(record.get(field), f"a value's {field}", optional=True)
        # A library's or a task's dataroot keypath, or none.
        if record.get("keypath") is not None:
            _key(record["keypath"], fail, text)
            if not owners.is_dataroot_keypath(record["keypath"]):
                fail("a value's dataroot keypath is neither a library's nor a task's")
        if record.get("kind") not in ("design", "pdk", "library", "fpga", "tool", "project") \
                or record.get("origin") not in _ORIGINS:
            fail("a value's kind or origin is not one this server knows")
    return summary


def _key(key, fail, text) -> None:
    if not isinstance(key, list) or not key or len(key) > MAX_KEY_PARTS:
        fail("a keypath is not a short list")
    for part in key:
        text(part, "a keypath's part", MAX_NAME)


def read(asked: Dict[str, Any]) -> Dict[str, Any]:
    '''Read the job's manifest, make every check that reads it, and return the summary.

    Named classes are looked up among what this installation provides, never
    imported from the tree (`schemaclasses.load`, `remote.manifests`).
    '''
    import warnings

    from siliconcompiler.schema.baseschema import SchemaVersionWarning

    from siliconcompiler.remote import manifests
    from siliconcompiler.remote import owners
    from siliconcompiler.remote import runflow
    from siliconcompiler.remote.server.staging import schemaclasses

    tree = asked["tree"]
    design, jobname = asked["design"], asked["jobname"]
    summary: Dict[str, Any] = {
        "summary": SUMMARY_VERSION, "outcome": None, "design": None, "jobname": None,
        "flow": None, "nodes": None, "edges": [], "upstream": [], "pdk": None,
        "libraries": [], "fpga": None, "tools": [], "required": None, "values": [],
        "credentials": []}

    def refuse(slug, detail, reason=None, **members):
        summary["outcome"] = {"type": slug, "reason": reason, "detail": detail,
                              "members": members}
        return summary

    manifest = os.path.join(tree, f"{design}.pkg.json")
    schemaclasses.load()
    # Reading a newer manifest silently drops or replaces keys, so
    # SiliconCompiler's warning is the refusal.
    with warnings.catch_warnings(record=True) as raised:
        warnings.simplefilter("always", SchemaVersionWarning)
        try:
            # Whole, not lazily: every class it names is resolved here.
            project = manifests.read(manifest, lazyload=False)
        except Exception as e:                               # noqa: BLE001
            return refuse("archive-rejected",
                          f"the uploaded manifest could not be read: {e}",
                          reason="invalid_manifest")

    newer = [str(warning.message) for warning in raised
             if issubclass(warning.category, SchemaVersionWarning)]
    if newer:
        wanted = ", ".join(asked.get("requires_siliconcompiler") or []) or "any"
        return refuse("declared-mismatch",
                      f"this server cannot read that manifest: {newer[0]}. It was "
                      "written by a newer SiliconCompiler than the one the job "
                      f"resolved to ({wanted}), and reading one is only backwards "
                      "compatible")

    summary["design"], summary["jobname"] = project.name, project.option.get_jobname()
    if project.name != design or project.option.get_jobname() != jobname:
        return refuse("declared-mismatch",
                      f"the manifest is {project.name}/{project.option.get_jobname()} "
                      f"and the job is {design}/{jobname}")

    # Each dataroot path carrying userinfo, by keypath, never value (surface D302).
    summary["credentials"] = [list(keypath)
                              for keypath, path in owners.dataroot_paths(project)
                              if owners.has_userinfo(path)]
    # And in every upstream node's manifest (surface D307).
    for member in _outputs_manifests(tree):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                upstream = manifests.read(os.path.join(tree, member), lazyload=False)
        except Exception as e:                               # noqa: BLE001
            return refuse("archive-rejected",
                          f"the uploaded manifest {member} could not be read: {e}",
                          reason="invalid_manifest")
        for keypath, path in owners.dataroot_paths(upstream):
            if owners.has_userinfo(path) and list(keypath) not in summary["credentials"]:
                summary["credentials"].append(list(keypath))

    try:
        runtime = runflow.runtime_flow(project)
        nodes = list(runtime.get_nodes())
    except Exception as e:                                   # noqa: BLE001
        return refuse("archive-rejected", f"the manifest names no runnable flow: {e}",
                      reason="invalid_manifest")
    if not nodes:
        return refuse("archive-rejected", "the manifest's flow has no nodes to run",
                      reason="invalid_manifest")

    flow = project.get_flow()
    summary["flow"] = flow.name
    tasks = {node: flow.get_graph_node(*node).get_taskmodule() for node in nodes}

    # An unprovided task class is refused (surface D163), by name, before
    # anything below asks for a task, which imports it.
    known = manifests.known_classes()
    unknown: Dict[str, List[str]] = {}
    for (step, index), name in tasks.items():
        if name not in known:
            unknown.setdefault(name, []).append(f"{step}/{index}")
    if unknown:
        named = "; ".join(f"{', '.join(where)} runs {name}"
                          for name, where in sorted(unknown.items()))
        return refuse(
            "software-unavailable",
            f"this server does not have the task class each of these nodes runs: "
            f"{named}. A task's own setup runs on the node, so it is not run as its "
            "base class instead",
            reason="unknown_class",
            unresolved=[{"kind": "class", "name": name, "requirement": [],
                         "available": []}
                        for name in sorted(unknown)])

    tools = runflow.node_tools(flow, nodes)
    edges = [[in_step, in_index, step, index]
             for step, index in nodes
             for in_step, in_index in runtime.get_node_inputs(step, index)
             if (in_step, in_index) in nodes]
    inherits = runflow.inheriting_nodes(flow, nodes,
                                        [tuple(edge) for edge in edges])
    python = runflow.python_nodes(flow, nodes)
    summary["nodes"] = [{
        "step": step, "index": index,
        "task": tasks[(step, index)],
        "tool": tools.get((step, index)),
        "inherits": (step, index) in inherits,
        "python": (step, index) in python} for step, index in nodes]
    summary["edges"] = edges
    summary["tools"] = sorted({tool for tool in tools.values() if tool})

    refused = _unattended(project, nodes)
    if refused:
        return refuse("archive-rejected", refused[1], reason=refused[0])

    try:
        from siliconcompiler.flowgraph import Flowgraph
        for step, index in nodes:
            Flowgraph.check_node_name(step, index)
    except ValueError as e:
        return refuse("archive-rejected",
                      f"the manifest's flow names a node that is not one: {e}",
                      reason="invalid_manifest")

    summary["upstream"] = [list(node) for node in runflow.upstream_nodes(
        project, {tuple(node) for node in asked.get("skipped") or []})]
    # 'none' where the class has no PDK setting, None where it is unset: the
    # column's CHECK on admitted jobs must tell resolved-to-none from unresolved.
    summary["pdk"] = (project.get("asic", "pdk") or None) \
        if project.valid("asic", "pdk") else "none"
    summary["libraries"] = _libraries(project)
    try:
        summary["fpga"] = project.get("fpga", "device") or None
    except Exception:                                       # noqa: BLE001
        pass

    required = owners.required(project)
    summary["required"] = sorted([list(key) for key in required]) \
        if required is not None else None
    summary["values"] = owners.value_records(
        project, os.path.join(tree, "sc_collected_files"), required)

    # Fails closed where the class has a PDK setting left unset.
    if summary["pdk"] is None:
        return refuse("resource-unresolved",
                      f"this {type(project).__name__} project sets no PDK: set one "
                      "with set_pdk() before it is submitted",
                      resource_kind="pdk")
    return summary


def _unattended(project, nodes):
    '''``(reason, detail)`` for a node that would wait for a person, or None (surface D165).

    A breakpoint, or a task that opens a window; a `ScreenshotTask` is headless.'''
    from siliconcompiler import OpenTask, ScreenshotTask

    flow = project.get_flow()
    for step, index in nodes:
        if project.option.get_breakpoint(step=step, index=index):
            return ("breakpoint",
                    f"{step}/{index} has a breakpoint set, which stops the run for a "
                    "person to look -- and nobody is at a remote run. Clear "
                    "option,breakpoint for it")
        try:
            task = flow.get_task_module(step, index)
        except ImportError:
            continue
        if issubclass(task, OpenTask) and not issubclass(task, ScreenshotTask):
            return ("interactive_task",
                    f"{step}/{index} runs {task.__module__}/{task.__name__}, which opens a "
                    "window for a person -- and nobody is at a remote run. A screenshot "
                    "task renders the same view without one")
    return None


def _libraries(project) -> List[str]:
    '''The standard-cell libraries this run uses, main library first.

    Both keys: `asic,asiclib` is only filled from `asic,mainlib` when a run starts.
    '''
    found: List[str] = []
    for key in ("mainlib", "asiclib"):
        try:
            value = project.get("asic", key)
        except Exception:                                       # noqa: BLE001
            continue
        for name in (value if isinstance(value, list) else [value]):
            if name and name not in found:
                found.append(name)
    return found


# Defaults; the server passes its own through the environment.
CPU_SECONDS = 300
MEMORY_BYTES = 4 * 1024 ** 3
FILE_BYTES = 16 * 1024 * 1024


def contain(cpu_seconds: int = CPU_SECONDS, memory_bytes: int = MEMORY_BYTES) -> Dict[str, Any]:
    '''Contain this process before it opens anything; returns what it achieved.

    In this process after ``exec``, never a ``preexec_fn``, unsafe in a threaded server.
    '''
    achieved = {"network": False, "limits": False}

    unshare = getattr(os, "unshare", None)
    if unshare is not None and sys.platform.startswith("linux"):
        try:
            # The network namespace holds only a loopback that is down.
            unshare(os.CLONE_NEWUSER | os.CLONE_NEWNET)
            achieved["network"] = True
        except OSError:
            pass

    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_BYTES, FILE_BYTES))
        achieved["limits"] = True
    except (ImportError, OSError, ValueError):
        pass
    return achieved


def main(argv=None) -> int:
    '''Contain, read, print the summary; the request is JSON or ``@<path>``.'''
    argv = sys.argv[1:] if argv is None else argv
    started = time.monotonic()

    achieved = contain(int(os.environ.get("SC_READ_CPU_SECONDS") or CPU_SECONDS),
                       int(os.environ.get("SC_READ_MEMORY_BYTES") or MEMORY_BYTES))

    if len(argv) != 1:
        print("usage: python3 -m siliconcompiler.remote.server.staging.manifestread <request>",
              file=sys.stderr)
        return 2
    text = argv[0]
    if text.startswith("@"):
        with open(text[1:]) as f:
            text = f.read()
    asked = json.loads(text)

    summary = read(asked)
    summary["contained"] = achieved
    summary["seconds"] = round(time.monotonic() - started, 3)
    sys.stdout.write(json.dumps(summary))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
