'''
What a submitted run executes, read the same way at both ends so they agree on
which nodes a run covers.

Outside `server/` on purpose, importing no Flask: the client runs without the
server extra.
'''

from typing import Dict, List, Optional, Set, Tuple

__all__ = ["runtime_flow", "runtime_nodes", "upstream_nodes", "outputs_present",
           "node_tools", "inheriting_nodes", "python_nodes"]


def runtime_flow(project):
    '''The flow this run will actually execute, narrowed by ``from``, ``to`` and ``prune``.'''
    from siliconcompiler.flowgraph import RuntimeFlowgraph

    return RuntimeFlowgraph(
        project.get_flow(),
        from_steps=project.option.get_from(),
        to_steps=project.option.get_to(),
        prune_nodes=project.option.get_prune())


def runtime_nodes(project) -> List[Tuple[str, str]]:
    '''The nodes this run will execute, in flowgraph order.'''
    return list(runtime_flow(project).get_nodes())


def upstream_nodes(project, skipped=()) -> List[Tuple[str, str]]:
    '''The nodes outside the run that it takes inputs from (surface D175).
    A node in ``skipped`` has no results, so it is looked through to its inputs.'''
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
    '''Whether a node's ``outputs/`` holds a file other than its own manifest.'''
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
    '''The tool each node's image must hold, per node: submit resolves an image each.

    Asked of the task (`Task._remote_toolname`), never inferred: `exe` says
    nothing for the pyslang tasks, and the tool name says *builtin*.
    Read off a BARE task, no setup, so it costs an attribute read per node.
    '''
    wanted: Dict[Tuple[str, str], Optional[str]] = {}
    for step, index in nodes:
        try:
            wanted[(step, index)] = flow.get_task_module(step, index)() \
                ._remote_toolname
        except Exception:                                       # noqa: BLE001
            # The job's own image: the safe direction.
            wanted[(step, index)] = None
    return wanted


def inheriting_nodes(flow, nodes, edges) -> Dict[Tuple[str, str],
                                                 Optional[Tuple[str, str]]]:
    '''Nodes that run wherever their input node ran, and where that is.

    An execute task's command comes from the manifest, so the image that made
    its inputs is likeliest to run it. The FIRST input: deterministic.
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
    '''The nodes whose task overrides `Task.get_python_environment`, so runs the
    user's Python and gets the job's packages. Read off the class, running no setup.'''
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
