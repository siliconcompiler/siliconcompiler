'''
What a submitted run executes, read the same way at both ends.

The client decides from it what to upload, what to name in `continues_from`
and what tools to ask for; the server, which rows to write, what an upload must
hold and where each node runs. Two copies would be two answers to which nodes a
run covers, so both ends call these.

🔴 **Outside `server/` on purpose, and it imports no Flask**: the client runs
without the server extra, and importing anything under
`siliconcompiler.remote.server` loads the server package.
'''

from typing import Dict, List, Optional, Set, Tuple

__all__ = ["runtime_flow", "runtime_nodes", "upstream_nodes", "outputs_present",
           "node_tools", "inheriting_nodes", "python_nodes"]


def runtime_flow(project):
    '''The flow this run will actually execute.

    Not ``project.get_flow()``: ``from``, ``to`` and ``prune`` narrow a
    flowgraph to the part a particular run covers, and a server that wrote a
    row per node of the whole graph would report nodes that were never going to
    run as pending for ever.
    '''
    from siliconcompiler.flowgraph import RuntimeFlowgraph

    return RuntimeFlowgraph(
        project.get_flow(),
        from_steps=project.option.get_from(),
        to_steps=project.option.get_to(),
        prune_nodes=project.option.get_prune())


def runtime_nodes(project) -> List[Tuple[str, str]]:
    '''The nodes this run will execute, in flowgraph order.

    The same derivation on both ends: the server writes a row per node at
    submit, and the run reports against the same list. Deriving it twice from
    the same manifest is what keeps the job object's ``progress`` counts
    matching what actually ran.
    '''
    return list(runtime_flow(project).get_nodes())


def upstream_nodes(project, skipped=()) -> List[Tuple[str, str]]:
    '''The nodes a run reads and does not run: every node outside the run
    that a node in it takes inputs from (surface D175). A node in ``skipped``
    -- skipped in the job that ran it -- is looked through to its own inputs,
    since it has no results to read.

    🔴 **One derivation for both ends.** The client decides from it what to
    upload or name in `continues_from`, and the server what must be in the
    upload or copied in; two copies of it would be two answers to which
    results a `-from` run needs.
    '''
    runtime = runtime_flow(project)
    flow = project.get_flow()
    pruned = set(project.option.get_prune() or [])
    running = set(runtime.get_nodes())
    skipped = set(skipped)

    found = set()
    seen = set()
    pending = [source for node in running for source in runtime.get_node_inputs(*node)]
    while pending:
        node = tuple(pending.pop())
        if node in running or node in seen or node in pruned:
            continue
        seen.add(node)
        if node in skipped:
            pending.extend(flow.get(*node, "input"))
        else:
            found.add(node)
    return sorted(found)


def outputs_present(node_dir, design: str) -> bool:
    '''Whether a node's results are there: a file under its ``outputs/`` other
    than its own manifest. The same test on both ends.'''
    import os

    outputs = os.path.join(str(node_dir), "outputs")
    manifest = f"{design}.pkg.json"
    for root, _, files in os.walk(outputs):
        for name in files:
            if root == outputs and name == manifest:
                continue
            return True
    return False


def node_tools(flow, nodes) -> Dict[Tuple[str, str], Optional[str]]:
    '''What each node's image must hold, which is what the resolution needs.

    🔴 **Asked of the task and never inferred.** `Task._remote_toolname`
    declares it; every rule that guesses gets a real task wrong. Inferring
    from `exe` says *nothing* for the slang tasks, which have no executable
    and drive `pyslang` in this process -- and an image without pyslang cannot
    run them. Inferring from the tool NAME says *builtin*, which is not a
    thing anybody installs.

    🔴 Per node rather than a set for the whole flow, because submit resolves N
    images and not one: an `import` node needing nothing but Python has no
    business pulling a twelve-gigabyte OpenROAD image, and the only thing that
    can tell them apart is what each node declares.

    ⚠️ **Here rather than in the server, because both ends derive it.** The
    server needs it to place nodes; the client needs it to say what its flow
    will reach for, which is what lets the server refuse before the archive
    moves. Two copies of this would be two answers to *which image does this
    node need*.

    ⚠️ Read off a BARE task -- no setup, no project -- so a forty-node flow
    costs forty attribute reads and nothing else.
    '''
    wanted: Dict[Tuple[str, str], Optional[str]] = {}
    for step, index in nodes:
        try:
            wanted[(step, index)] = flow.get_task_module(step, index)() \
                ._remote_toolname
        except Exception:                                       # noqa: BLE001
            # A task that will not load declares nothing, which places the
            # node in the job's own image -- the safe direction, since that is
            # what a node needing nothing gets.
            wanted[(step, index)] = None
    return wanted


def inheriting_nodes(flow, nodes, edges) -> Dict[Tuple[str, str],
                                                 Optional[Tuple[str, str]]]:
    '''Nodes that run wherever their input node ran, and where that is.

    🆕 The execute tasks assemble a command out of the manifest, so there is
    nothing to require an image for -- and the environment that produced the
    inputs is the one most likely to be able to run it. Following the previous
    node costs nothing when it does not.

    ⚠️ The FIRST input, where there is more than one. A task computing a
    command over several inputs has no better claim on one of them, and
    picking deterministically beats picking arbitrarily.
    '''
    before: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for from_step, from_index, to_step, to_index in edges:
        before.setdefault((to_step, to_index), (from_step, from_index))

    found: Dict[Tuple[str, str], Optional[Tuple[str, str]]] = {}
    for step, index in nodes:
        try:
            if flow.get_task_module(step, index)()._remote_inherits_env:
                found[(step, index)] = before.get((step, index))
        except Exception:                                       # noqa: BLE001
            continue
    return found


def python_nodes(flow, nodes) -> Set[Tuple[str, str]]:
    '''The nodes whose task runs the user's Python: its class reports what
    that Python needs (`Task.get_python_environment`). Where the job's Python
    packages are installed, and whose tool finds them on its `PYTHONPATH`.

    Read off the class, never a setup: the read runs none.
    '''
    from siliconcompiler.tool import Task

    found = set()
    for step, index in nodes:
        try:
            task = flow.get_task_module(step, index)
        except Exception:                                       # noqa: BLE001
            continue
        if getattr(task, "get_python_environment", None) is not Task.get_python_environment:
            found.add((step, index))
    return found
