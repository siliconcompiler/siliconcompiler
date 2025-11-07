import graphviz
import importlib
import inspect
import logging

import os.path

from typing import Tuple, Union, Optional, List, Type, Set, TYPE_CHECKING

from siliconcompiler.schema import BaseSchema, NamedSchema, DocsSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import NodeStatus

if TYPE_CHECKING:
    from siliconcompiler import Task
    from siliconcompiler.schema_support.record import RecordSchema


class Flowgraph(NamedSchema, DocsSchema):
    '''
    Schema for defining and interacting with a flowgraph.

    A flowgraph is a directed acyclic graph (DAG) that represents the
    compilation flow. Each node in the graph is a step/index pair that
    maps to a specific tool task, and edges represent dependencies between
    these tasks.
    '''

    def __init__(self, name: Optional[str] = None):
        '''
        Initializes a new Flowgraph object.

        Args:
            name (str, optional): The name of the flowgraph. Defaults to None.
        '''
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert("default", "default", FlowgraphNodeSchema())

        self.__clear_cache()

    def __clear_cache(self) -> None:
        '''
        Clears the internal cache for memoized flowgraph properties.

        This should be called any time the graph structure (nodes or edges)
        is modified to ensure subsequent calls to graph traversal methods
        (like get_nodes, get_execution_order, etc.) compute fresh results.
        '''

        self.__cache_nodes = None
        self.__cache_nodes_entry = None
        self.__cache_nodes_exit = None
        self.__cache_execution_order_forward = None
        self.__cache_execution_order_reverse = None

        self.__cache_node_outputs = None

        self.__cache_tasks = None

    def node(self, step: str, task: "Task", index: Optional[Union[str, int]] = 0) -> None:
        '''
        Creates or updates a flowgraph node.

        Creates a flowgraph node by binding a step/index pair to a specific
        tool task. A tool can be an external executable or one of the built-in
        functions in the SiliconCompiler framework (e.g., minimum, maximum, join).

        If the node (step, index) already exists, its task and tool information
        will be updated.

        The method modifies the following schema parameters for the given
        step and index:

        * `['<step>', '<index>', 'tool']`
        * `['<step>', '<index>', 'task']`
        * `['<step>', '<index>', 'taskmodule']`

        Args:
            step (str): Step name for the node. Must not contain '/'.
            task (Task or str or Type[Task]): The task to associate with this
                node. Can be a task instance, a string in the format
                '<module_path>/<ClassName>', or a Task class type.
            index (int or str, optional): Index for the step. Defaults to 0.
                Must not contain '/'.

        Raises:
            ValueError: If 'step' or 'index' are reserved names (like
                'default' or 'global') or contain invalid characters ('/').
            ValueError: If 'task' is not a valid Task object, string, or class.

        Examples:
            >>> import siliconcompiler.tools.openroad as openroad
            >>> # Using a Task class
            >>> flow.node('place', openroad.Place, index=0)
            >>>
            >>> # Using a string identifier
            >>> flow.node('cts', 'siliconcompiler.tools.openroad/Cts', index=0)
            >>>
            >>> # Using a Task instance
            >>> from siliconcompiler.tools.builtin import Join
            >>> flow.node('join', Join(), index=0)
        '''
        from siliconcompiler import Task

        if step in (Parameter.GLOBAL_KEY, 'default') or step.startswith("sc_"):
            raise ValueError(f"{step} is a reserved name")

        index = str(index)
        if index in (Parameter.GLOBAL_KEY, 'default'):
            raise ValueError(f"{index} is a reserved name")

        if '/' in step:
            raise ValueError(f"{step} is not a valid step, it cannot contain '/'")
        if '/' in index:
            raise ValueError(f"{index} is not a valid index, it cannot contain '/'")

        # Determine task name and module
        task_module = None
        if inspect.isclass(task) and issubclass(task, Task):
            # Instantiate the task class
            task = task()

        if isinstance(task, str):
            task_module = task
            task_cls = self.__get_task_module(task_module)
            task = task_cls()
        elif isinstance(task, Task):
            task_module = task.__class__.__module__ + "/" + task.__class__.__name__
        else:
            raise ValueError(f"{task} is not a string, Task class, or Task instance and "
                             "cannot be used to setup a task.")

        # bind tool to node
        graph_node: "FlowgraphNodeSchema" = self.get(step, index, field="schema")
        graph_node.set('tool', task.tool())
        graph_node.set('task', task.task())
        graph_node.set('taskmodule', task_module)

        self.__clear_cache()

    def edge(self, tail: str, head: str,
             tail_index: Optional[Union[str, int]] = 0,
             head_index: Optional[Union[str, int]] = 0) -> None:
        '''
        Creates a directed edge from a tail node to a head node.

        Connects the output of a tail node (tail, tail_index) with the
        input of a head node (head, head_index) by adding the tail node
        to the 'input' list of the head node in the schema.

        If the edge already exists, this method does nothing.

        The method modifies the following parameter:

        * `['<head>', '<head_index>', 'input']`

        Args:
            tail (str): Step name of the tail node (source).
            head (str): Step name of the head node (destination).
            tail_index (int or str, optional): Index of the tail node.
                Defaults to 0.
            head_index (int or str, optional): Index of the head node.
                Defaults to 0.

        Raises:
            ValueError: If either the head or tail node is not defined in
                the flowgraph before calling this method.

        Examples:
            >>> flow.node('place', 'openroad/Place')
            >>> flow.node('cts', 'openroad/Cts')
            >>> flow.edge('place', 'cts')
            # Creates a directed edge from ('place', '0') to ('cts', '0').
        '''
        head_index = str(head_index)
        tail_index = str(tail_index)

        for step, index in [(head, head_index), (tail, tail_index)]:
            if not self.valid(step, index):
                raise ValueError(f"{step}/{index} is not a defined node in {self.name}.")

        head_node = self.get_graph_node(head, head_index)

        tail_node = (tail, tail_index)
        if tail_node in head_node.get_input():
            # Edge already exists
            return

        head_node.add('input', tail_node)

        self.__clear_cache()

    def remove_node(self, step: str, index: Optional[Union[str, int]] = None) -> None:
        '''
        Removes a flowgraph node and reconnects its inputs to its outputs.

        This operation effectively "stitches" the graph back together by
        creating new edges from all inputs of the removed node to all
        outputs of the removed node.

        If `index` is None, all nodes for the given `step` are removed.

        Args:
            step (str): Step name of the node to remove.
            index (int or str, optional): Index of the node to remove. If None,
                all nodes for the given step are removed. Defaults to None.

        Raises:
            ValueError: If the specified `step` or `(step, index)` is not
                a valid node in the flowgraph.
        '''

        if step not in self.getkeys():
            raise ValueError(f'{step} is not a valid step in {self.name}')

        if index is None:
            # Iterate over all indexes for the step
            for index_key in self.getkeys(step):
                self.remove_node(step, index_key)
            return

        index = str(index)
        if index not in self.getkeys(step):
            raise ValueError(f'{index} is not a valid index for {step} in {self.name}')

        # Save input edges of the node being removed
        node_to_remove = (step, index)
        node_inputs = self.get_graph_node(step, index).get_input()

        # Remove the node from the schema
        self.remove(step, index)

        # Remove the step if all its nodes are gone
        if len(self.getkeys(step)) == 0:
            self.remove(step)

        # Re-wire: Find all nodes that had the removed node as an input
        for flow_step in self.getkeys():
            for flow_index in self.getkeys(flow_step):
                current_node = self.get_graph_node(flow_step, flow_index)
                inputs = current_node.get_input()

                if node_to_remove in inputs:
                    # Remove the old edge
                    inputs = [inode for inode in inputs if inode != node_to_remove]
                    # Add new edges from the removed node's inputs
                    inputs.extend(node_inputs)
                    # Set the new list of inputs, removing duplicates
                    self.set(flow_step, flow_index, 'input', sorted(set(inputs)))

        self.__clear_cache()

    def insert_node(self, step: str, task: "Task", before_step: str,
                    index: Optional[Union[str, int]] = 0,
                    before_index: Optional[Union[str, int]] = 0) -> None:
        '''
        Inserts a new node in the graph immediately before a specified node.

        The new node (`step`, `index`) is placed between the `before` node
        (`before_step`, `before_index`) and all of the `before` node's
        original inputs. The `before` node's inputs are cleared, and it
        is given a single input: the new node. The new node inherits all
        the original inputs of the `before` node.

        Args:
            step (str): Step name for the new node.
            task (Task or str or Type[Task]): Task to associate with the new node.
            before_step (str): Step name of the existing node to insert before.
            index (int or str, optional): Index for the new node. Defaults to 0.
            before_index (int or str, optional): Index of the existing node.
                Defaults to 0.

        Raises:
            ValueError: If the `before` node (`before_step`, `before_index`)
                is not a valid node in the flowgraph.
        '''

        index = str(index)
        before_index = str(before_index)

        if (before_step, before_index) not in self.get_nodes():
            raise ValueError(f'{before_step}/{before_index} is not a valid node in {self.name}')

        # add the node
        self.node(step, task, index=index)

        # rewire
        for istep, iindex in self.get_node_outputs(before_step, before_index):
            inputs = self.get(istep, iindex, "input")
            inputs.remove((before_step, before_index))
            self.set(istep, iindex, "input", inputs)
            self.add(istep, iindex, "input", (step, index))
        self.set(step, index, "input", [(before_step, before_index)])

        self.__clear_cache()

    ###########################################################################
    def graph(self, subflow: "Flowgraph", name: Optional[str] = None) -> None:
        '''
        Instantiates a sub-flowgraph within the current flowgraph.

        This method copies all nodes and their internal connections from
        `subflow` into the current flowgraph.

        If `name` is provided, it is used as a prefix (e.g., "core.")
        for all step names from the `subflow` to ensure they are unique
        within the current flowgraph. This prefix is also applied to the
        internal edges to maintain the sub-flowgraph's structure.

        Args:
            subflow (Flowgraph): The flowgraph to instantiate.
            name (str, optional): A prefix to add to the names of the
                instantiated steps to ensure they are unique. Defaults to None.

        Raises:
            ValueError: If `subflow` is not a `Flowgraph` object, or if
                a step from the sub-flowgraph already exists in the current graph.
        '''
        if not isinstance(subflow, Flowgraph):
            raise ValueError(f"subflow must a Flowgraph, not: {type(subflow)}")

        for step in subflow.getkeys():
            # uniquify each step
            if name is None:
                newstep = step
            else:
                newstep = name + "." + step

            if newstep in self.getkeys():
                raise ValueError(f"{newstep} is already defined")

            # forward information
            for keys in subflow.allkeys(step):
                self.set(newstep, *keys, subflow.get(step, *keys))
            self.__clear_cache()

            if name is None:
                continue

            # rename inputs
            for index in self.getkeys(newstep):
                all_inputs = self.get_graph_node(newstep, index).get_input()
                self.set(newstep, index, 'input', [])
                for in_step, in_index in all_inputs:
                    newin = name + "." + in_step
                    self.add(newstep, index, 'input', (newin, in_index))

        self.__clear_cache()

    def get_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Returns a sorted tuple of all nodes defined in this flowgraph.

        A node is represented as a `(step, index)` tuple. The result is
        memoized for efficiency.

        Returns:
            tuple[tuple(str,str)]: A sorted tuple of all (step, index)
            nodes in the graph.
        '''
        if self.__cache_nodes is not None:
            return self.__cache_nodes

        nodes = []
        for step in self.getkeys():
            for index in self.getkeys(step):
                nodes.append((step, index))

        self.__cache_nodes = tuple(sorted(set(nodes)))

        return self.__cache_nodes

    def get_entry_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Collects all nodes that are entry points to the flowgraph.

        Entry nodes are those with no inputs defined. The result is
        memoized.

        Returns:
            tuple[tuple(str,str)]: A sorted tuple of all entry nodes
            in the graph.
        '''

        if self.__cache_nodes_entry is not None:
            return self.__cache_nodes_entry

        nodes = []
        for step, index in self.get_nodes():
            if not self.get_graph_node(step, index).has_input():
                nodes.append((step, index))

        self.__cache_nodes_entry = tuple(sorted(set(nodes)))

        return self.__cache_nodes_entry

    def get_exit_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Collects all nodes that are exit points of the flowgraph.

        Exit nodes are those that are not inputs to any other node in
        the graph. The result is memoized.

        Returns:
            tuple[tuple(str,str)]: A sorted tuple of all exit nodes
            in the graph.
        '''

        if self.__cache_nodes_exit is not None:
            return self.__cache_nodes_exit

        inputnodes = []
        for step, index in self.get_nodes():
            inputnodes.extend(self.get_graph_node(step, index).get_input())
        nodes = []
        for step, index in self.get_nodes():
            if (step, index) not in inputnodes:
                nodes.append((step, index))

        self.__cache_nodes_exit = tuple(sorted(set(nodes)))

        return self.__cache_nodes_exit

    def get_execution_order(self, reverse: Optional[bool] = False) \
            -> Tuple[Tuple[Tuple[str, str], ...], ...]:
        '''
        Generates a topologically sorted list of nodes for execution.

        This method performs a topological sort of the graph. The result is
        a tuple of tuples, where each inner tuple represents a "level" of
        nodes that can be executed in parallel (as their dependencies are
        met).

        The result is memoized for both forward and reverse orders.

        Args:
            reverse (bool, optional): If True, the order is reversed,
                starting from the exit nodes and working backwards to the
                entry nodes. Defaults to False.

        Returns:
            tuple[tuple[tuple(str,str)]]: A tuple of tuples, where each inner
            tuple represents a level of nodes.
        '''

        if reverse:
            if self.__cache_execution_order_reverse is not None:
                return self.__cache_execution_order_reverse
        else:
            if self.__cache_execution_order_forward is not None:
                return self.__cache_execution_order_forward

        # Generate execution edges lookup map
        ex_map = {}
        for step, index in self.get_nodes():
            for istep, iindex in self.get_graph_node(step, index).get_input():
                if reverse:
                    ex_map.setdefault((step, index), set()).add((istep, iindex))
                else:
                    ex_map.setdefault((istep, iindex), set()).add((step, index))

        rev_ex_map = {}
        for node, edges in ex_map.items():
            for step, index in edges:
                rev_ex_map.setdefault((step, index), set()).add(node)

        # Collect execution order of nodes
        if reverse:
            order = [set(self.get_exit_nodes())]
        else:
            order = [set(self.get_entry_nodes())]

        visited = set()
        while True:
            next_level = set()
            next_visited = set()
            for step, index in sorted(order[-1]):
                if (step, index) not in rev_ex_map:
                    # No edges so assume inputs are okay
                    inputs_valid = True
                else:
                    inputs_valid = all([node in visited for node in rev_ex_map[(step, index)]])

                if inputs_valid:
                    next_visited.add((step, index))
                    if (step, index) in ex_map:
                        next_level.update(ex_map.pop((step, index)))
                else:
                    next_level.add((step, index))

            visited.update(next_visited)

            if not next_level:
                break

            order.append(next_level)

        # Filter duplicates from flow
        used_nodes = set()
        exec_order = []
        order.reverse()
        for n, level_nodes in enumerate(order):
            exec_order.append(list(level_nodes.difference(used_nodes)))
            used_nodes.update(level_nodes)

        exec_order.reverse()

        ordering = tuple([tuple(sorted(level)) for level in exec_order])

        if reverse:
            self.__cache_execution_order_reverse = ordering
            return self.__cache_execution_order_reverse
        else:
            self.__cache_execution_order_forward = ordering
            return self.__cache_execution_order_forward

    def get_node_outputs(self, step: str, index: Union[str, int]) -> Tuple[Tuple[str, str], ...]:
        '''
        Returns the nodes that the given node provides input to (its children).

        This is the reverse of `get_graph_node(step, index).get_input()`.
        The results are computed for all nodes and memoized on the first call.

        Args:
            step (str): Step name of the source node.
            index (str or int): Index of the source node.

        Returns:
            tuple[tuple(str,str)]: A sorted tuple of destination nodes
            (step, index) that take the given node as an input.

        Raises:
            ValueError: If the specified `(step, index)` is not a valid node.
        '''

        index = str(index)

        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node")

        if self.__cache_node_outputs is not None:
            return self.__cache_node_outputs[(step, index)]

        self.__cache_node_outputs = {}

        input_map = {}
        for istep, iindex in self.get_nodes():
            input_map[(istep, iindex)] = self.get_graph_node(istep, iindex).get_input()
            self.__cache_node_outputs[(istep, iindex)] = set()

        for src_node, dst_nodes in input_map.items():
            for dst_node in dst_nodes:
                if dst_node not in self.__cache_node_outputs:
                    self.__cache_node_outputs[dst_node] = set()
                self.__cache_node_outputs[dst_node].add(src_node)

        # Convert sets to sorted tuples for consistent output
        self.__cache_node_outputs = {
            node: tuple(sorted(outputs)) for node, outputs in self.__cache_node_outputs.items()
        }

        return self.__cache_node_outputs[(step, index)]

    def __find_loops(self, step: str, index: str, path: Optional[List[Tuple[str, str]]] = None) \
            -> Union[List[Tuple[str, str]], None]:
        '''
        Internal helper to search for loops in the graph via depth-first search.

        This method is used by `validate()`.

        Args:
            step (str): Step name to start/continue from.
            index (str): Index name to start/continue from.
            path (list, optional): The current path (nodes in recursion stack).
                Defaults to None.
            visited (set, optional): All nodes visited so far (to avoid
                re-checking branches). Defaults to None.

        Returns:
            list[tuple(str,str)]: A list of nodes forming a loop, or
            None if no loop is found from this path.
        '''
        if path is None:
            path = []

        if (step, index) in path:
            path.append((step, index))
            return path

        path.append((step, index))

        for ostep, oindex in self.get_node_outputs(step, index):
            loop_path = self.__find_loops(ostep, oindex, path=path.copy())
            if loop_path:
                return loop_path

        return None

    def validate(self, logger: Optional[logging.Logger] = None) -> bool:
        '''
        Checks if the flowgraph is valid.

        This method performs several checks:
        * All edges must point to and from valid nodes.
        * There should be no duplicate edges.
        * All nodes must have their tool, task, and taskmodule defined.
        * The graph must not contain any loops (it must be a DAG).

        Args:
            logger (logging.Logger, optional): A logger to use for reporting
                errors. Defaults to None.

        Returns:
            bool: True if the graph is valid, False otherwise.
        '''

        error = False

        check_nodes = set()
        for step, index in self.get_nodes():
            check_nodes.add((step, index))
            input_nodes = self.get_graph_node(step, index).get_input()
            check_nodes.update(input_nodes)

            for node in set(input_nodes):
                if input_nodes.count(node) > 1:
                    in_step, in_index = node
                    if logger:
                        logger.error(f'Duplicate edge from {in_step}/{in_index} to '
                                     f'{step}/{index} in the {self.name} flowgraph')
                    error = True

        diff_nodes = check_nodes.difference(self.get_nodes())
        if diff_nodes:
            if logger:
                for step, index in diff_nodes:
                    logger.error(f'{step}/{index} is missing in the {self.name} flowgraph')
            error = True

        # Detect missing definitions
        for step, index in self.get_nodes():
            for item in ('tool', 'task', 'taskmodule'):
                if not self.get(step, index, item):
                    if logger:
                        logger.error(f'{step}/{index} is missing a {item} definition in the '
                                     f'{self.name} flowgraph')
                    error = True

        # Detect loops
        for start_step, start_index in self.get_entry_nodes():
            loop_path = self.__find_loops(start_step, start_index)
            if loop_path:
                error = True
                if logger:
                    loop_path_str = [f"{step}/{index}" for step, index in loop_path]
                    logger.error(f"Loop detected in {self.name}: {' -> '.join(loop_path_str)}")

        return not error

    def __get_task_module(self, name: str) -> Type["Task"]:
        '''
        Internal helper to import and cache a task module by name.

        The name is expected in the format '<full.module.path>/<ClassName>'.

        Args:
            name (str): The fully qualified task module name.

        Returns:
            Type[Task]: The imported Task class.

        Raises:
            ValueError: If the name is not in the expected format.
            ImportError: If the module cannot be imported.
            AttributeError: If the class is not found in the module.
        '''
        # Create cache
        if self.__cache_tasks is None:
            self.__cache_tasks = {}

        if name in self.__cache_tasks:
            return self.__cache_tasks[name]

        try:
            module_name, cls = name.split("/")
        except (ValueError, AttributeError):
            raise ValueError("Task module name is not correctly formatted as "
                             f"<full.module.path>/<ClassName>: {name}")
        module = importlib.import_module(module_name)

        self.__cache_tasks[name] = getattr(module, cls)
        return self.__cache_tasks[name]

    def get_task_module(self, step: str, index: Union[str, int]) -> Type["Task"]:
        """
        Returns the imported Python Task class for a given task node.

        Args:
            step (str): Step name of the node.
            index (int or str): Index of the node.

        Returns:
            Type[Task]: The imported Task class associated with the node.

        Raises:
            ValueError: If the node is not valid.
        """
        index = str(index)
        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node in {self.name}.")
        return self.__get_task_module(self.get_graph_node(step, index).get_taskmodule())

    def get_all_tasks(self) -> Set[Type["Task"]]:
        '''
        Returns all unique task classes used in this flowgraph.

        Returns:
            set[Type[Task]]: A set of all imported task classes.
        '''
        tasks = set()
        for step, index in self.get_nodes():
            tasks.add(self.get_task_module(step, index))
        return tasks

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the metadata type for `getdict` serialization.
        """
        return Flowgraph.__name__

    def __get_graph_information(self):
        '''
        Internal helper to gather all node and edge info for graphviz.

        Returns:
            Tuple containing:
                - set: All graph-level inputs (currently empty).
                - dict: Information about each node.
                - list: Information about each edge.
        '''
        # Setup nodes
        node_exec_order = self.get_execution_order()

        node_rank = {}
        for rank, rank_nodes in enumerate(node_exec_order):
            for step, index in rank_nodes:
                node_rank[f'{step}/{index}'] = rank

        # TODO: This appears to be unused, legacy from when files were nodes
        all_graph_inputs = set()

        exit_nodes = [f'{step}/{index}' for step, index in self.get_exit_nodes()]

        nodes = {}
        edges = []

        def clean_label(label):
            return label.replace("<", "").replace(">", "")

        def clean_text(label):
            return label.replace("<", r"\<").replace(">", r"\>")

        all_nodes = [(step, index) for step, index in sorted(self.get_nodes())]

        runtime_flow = RuntimeFlowgraph(self)

        for step, index in all_nodes:
            graph_node = self.get_graph_node(step, index)
            tool = graph_node.get("tool")
            task = graph_node.get("task")

            inputs = []
            outputs = []

            node = f'{step}/{index}'

            nodes[node] = {
                "node": (step, index),
                "file_inputs": inputs,
                "inputs": {clean_text(f): f'input-{clean_label(f)}' for f in sorted(inputs)},
                "outputs": {clean_text(f): f'output-{clean_label(f)}' for f in sorted(outputs)},
                "task": f'{tool}/{task}' if tool != 'builtin' else task,
                "is_input": node_rank[node] == 0,
                "rank": node_rank[node]
            }
            nodes[node]["width"] = max(len(nodes[node]["inputs"]), len(nodes[node]["outputs"]))

            if tool is None or task is None:
                nodes[node]["task"] = None

            rank_diff = {}
            for in_step, in_index in runtime_flow.get_node_inputs(step, index):
                in_node_name = f'{in_step}/{in_index}'
                rank_diff[in_node_name] = node_rank[node] - node_rank[in_node_name]
            nodes[node]["rank_diff"] = rank_diff

        for step, index in all_nodes:
            node = f'{step}/{index}'
            all_inputs = []
            for in_step, in_index in self.get_graph_node(step, index).get_input():
                all_inputs.append(f'{in_step}/{in_index}')
            for item in all_inputs:
                edges.append((item, node, 1 if node in exit_nodes else 2))

        return all_graph_inputs, nodes, edges

    def write_flowgraph(self, filename: str,
                        fillcolor: Optional[str] = '#ffffff',
                        fontcolor: Optional[str] = '#000000',
                        background: Optional[str] = 'transparent',
                        fontsize: Optional[Union[int, str]] = 14,
                        border: Optional[bool] = True,
                        landscape: Optional[bool] = False) -> None:
        r'''
        Renders and saves the compilation flowgraph to a file.

        The flow object flowgraph is traversed to create a graphviz (\*.dot)
        file comprised of node, edges, and labels. The dot file is a
        graphical representation of the flowgraph useful for validating the
        correctness of the execution flow graph. The dot file is then
        converted to the appropriate picture or drawing format based on the
        filename suffix provided. Supported output render formats include
        png, svg, gif, pdf and a few others. For more information about the
        graphviz project, see see https://graphviz.org/

        Args:
            filename (filepath): Output filepath
            fillcolor(str): Node fill RGB color hex value
            fontcolor (str): Node font RGB color hex value
            background (str): Background color
            fontsize (str): Node text font size
            border (bool): Enables node border if True
            landscape (bool): Renders graph in landscape layout if True

        Examples:
            >>> flow.write_flowgraph('mydump.png')
            Renders the object flowgraph and writes the result to a png file.
        '''

        filepath = os.path.abspath(filename)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")

        fontsize = str(fontsize)

        # controlling border width
        if border:
            penwidth = '1'
        else:
            penwidth = '0'

        # controlling graph direction
        if landscape:
            rankdir = 'LR'
            out_label_suffix = ':e'
            in_label_suffix = ':w'
        else:
            rankdir = 'TB'
            out_label_suffix = ':s'
            in_label_suffix = ':n'

        all_graph_inputs, nodes, edges = self.__get_graph_information()

        out_label_suffix = ''
        in_label_suffix = ''

        dot = graphviz.Digraph(format=fileformat)
        dot.graph_attr['rankdir'] = rankdir
        dot.attr(bgcolor=background)

        subgraphs = {
            "graphs": {},
            "nodes": []
        }
        for node, info in nodes.items():
            subgraph_temp = subgraphs

            # Create nested cluster subgraphs for steps like "a.b.c"
            for key in node.split(".")[0:-1]:
                if key not in subgraph_temp["graphs"]:
                    subgraph_temp["graphs"][key] = {
                        "graphs": {},
                        "nodes": []
                    }
                subgraph_temp = subgraph_temp["graphs"][key]

            # Special cluster for input nodes
            if info['is_input']:
                if "sc-inputs" not in subgraph_temp["graphs"]:
                    subgraph_temp["graphs"]["sc-inputs"] = {
                        "graphs": {},
                        "nodes": []
                    }
                subgraph_temp = subgraph_temp["graphs"]["sc-inputs"]

            subgraph_temp["nodes"].append(node)

        with dot.subgraph(name='inputs') as input_graph:
            input_graph.graph_attr['cluster'] = 'true'
            input_graph.graph_attr['color'] = background

            # add inputs
            for graph_input in sorted(all_graph_inputs):
                input_graph.node(
                    graph_input, label=graph_input, bordercolor=fontcolor, style='filled',
                    fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                    penwidth=penwidth, fillcolor=fillcolor, shape="box")

        def make_node(graph, node, prefix):
            '''Helper function to create a node in the graphviz object.'''
            info = nodes[node]

            shape = "oval"
            task_label = f"\\n ({info['task']})" if info['task'] is not None else ""
            labelname = f"{node.replace(prefix, '')}{task_label}"

            graph.node(node, label=labelname, bordercolor=fontcolor, style='filled',
                       fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                       penwidth=penwidth, fillcolor=fillcolor, shape=shape)

        graph_idx = 0

        def get_node_count(graph_info):
            nodes = len(graph_info["nodes"])

            for subgraph in graph_info["graphs"]:
                nodes += get_node_count(graph_info["graphs"][subgraph])

            return nodes

        def build_graph(graph_info, parent, prefix):
            nonlocal graph_idx

            for subgraph in graph_info["graphs"]:
                child_prefix = prefix
                if get_node_count(graph_info["graphs"][subgraph]) > 1:
                    if subgraph != "sc-inputs":
                        child_prefix = f"{child_prefix}{subgraph}."
                    graph = graphviz.Digraph(name=f"cluster_{graph_idx}")
                    graph_idx += 1

                    graph.graph_attr['rankdir'] = rankdir
                    graph.attr(bgcolor=background)

                    if subgraph == "sc-inputs":
                        graph.attr(style='invis')
                    else:
                        # Style the cluster box
                        graph.attr(color=fontcolor)
                        graph.attr(style='rounded')
                        graph.attr(shape='oval')
                        graph.attr(label=subgraph)
                        graph.attr(labeljust='l')
                        graph.attr(fontcolor=fontcolor)
                        graph.attr(fontsize=str(int(fontsize) + 2))
                else:
                    graph = parent

                build_graph(graph_info["graphs"][subgraph], graph, child_prefix)

                if graph is not parent:
                    parent.subgraph(graph)

            # Add all nodes at this level to the parent graph
            for subnode in graph_info["nodes"]:
                make_node(parent, subnode, prefix)

        # Start building the graph from the root
        build_graph(subgraphs, dot, "")

        # Add all the edges
        for edge0, edge1, weight in edges:
            dot.edge(f'{edge0}{out_label_suffix}', f'{edge1}{in_label_suffix}', weight=str(weight))

        dot.render(filename=fileroot, cleanup=True)

    def get_graph_node(self, step: str, index: Optional[Union[int, str]] = None) \
            -> "FlowgraphNodeSchema":
        """
        Get the flowgraph node for this step and index
        """
        if index is None:
            index = "0"
        index = str(index)

        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node in {self.name}.")

        return self.get(step, index, field="schema")

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import image, build_section

        if not key_offset:
            key_offset = tuple()

        docs = []
        image_sec = build_section("Graph", f"{ref_root}-flow-{self.name}-graph")
        image_path_root = os.path.join(doc.env.app.outdir, f"_images/gen/flows/{self.name}.svg")
        image_path = image_path_root
        idx = 0
        while os.path.exists(image_path):
            base, ext = os.path.splitext(image_path_root)
            image_path = f"{base}-{idx}{ext}"
            idx += 1
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        self.write_flowgraph(image_path)
        image_sec += image(image_path, center=True)
        docs.append(image_sec)

        config = build_section("Nodes", f"{ref_root}-flow-{self.name}-nodes")
        for nodes in self.get_execution_order():
            for step, index in nodes:
                sec = build_section(f"{step}/{index}",
                                    f"{ref_root}-flow-{self.name}-nodes-{step}-{index}")
                sec += BaseSchema._generate_doc(
                    self.get_graph_node(step, index),
                    doc,
                    ref_root=f"{ref_root}-flow-{self.name}-nodes-{step}-{index}",
                    key_offset=(*key_offset, "flowgraph", self.name),
                    detailed=False)
                config += sec
        docs.append(config)

        return docs


class RuntimeFlowgraph:
    '''
    A runtime representation of a flowgraph for a specific execution.

    This class creates a "view" of a base `Flowgraph` that considers
    runtime options such as the start step (`-from`), end step (`-to`),
    and nodes to exclude (`-prune`). It computes the precise subgraph of
    nodes that need to be executed for a given run.
    '''

    def __init__(self, base: Flowgraph,
                 args: Optional[Tuple[str, str]] = None,
                 from_steps: Optional[Union[Set[str], List[str]]] = None,
                 to_steps: Optional[Union[Set[str], List[str]]] = None,
                 prune_nodes: Optional[Union[Set[Tuple[str, str]], List[Tuple[str, str]]]] = None):
        '''
        Initializes a new RuntimeFlowgraph.

        Args:
            base (Flowgraph): The base flowgraph to create a view of.
            args (tuple[str, str], optional): A specific `(step, index)` to run.
                If provided, this overrides `from_steps` and `to_steps`.
                Defaults to None.
            from_steps (list[str], optional): List of step names to start execution
                from. Defaults to the base graph's entry nodes.
            to_steps (list[str], optional): List of step names to end execution at.
                Defaults to the base graph's exit nodes.
            prune_nodes (list[tuple(str,str)], optional): A list of `(step, index)`
                nodes to exclude from the graph. Defaults to None.
        '''
        if not all([hasattr(base, attr) for attr in dir(Flowgraph)]):
            raise ValueError(f"base must a Flowgraph, not: {type(base)}")

        self.__base = base

        if args and args[0] is not None:
            from_steps = None
            to_steps = None
            prune_nodes = None

            step, index = args
            if index is None:
                self.__from = [(step, index) for index in self.__base.getkeys(step)]
            else:
                self.__from = [(step, index)]
            self.__to = self.__from
        else:
            if from_steps:
                self.__from = []
                for step in from_steps:
                    try:
                        self.__from.extend([(step, index) for index in self.__base.getkeys(step)])
                    except KeyError:
                        pass
            else:
                self.__from = self.__base.get_entry_nodes()

            if to_steps:
                self.__to = []
                for step in to_steps:
                    try:
                        self.__to.extend([(step, index) for index in self.__base.getkeys(step)])
                    except KeyError:
                        pass
            else:
                self.__to = self.__base.get_exit_nodes()

        self.__from = sorted(set(self.__from))
        self.__to = sorted(set(self.__to))

        if not prune_nodes:
            prune_nodes = set()
        self.__prune = sorted(set(prune_nodes))

        # remove pruned from and tos
        self.__from = [node for node in self.__from if node not in self.__prune]
        self.__to = [node for node in self.__to if node not in self.__prune]

        self.__compute_graph()

    def __walk_graph(self, node: Tuple[str, str],
                     path: Optional[List[Tuple[str, str]]] = None,
                     reverse: Optional[bool] = True) -> Set[Tuple[Tuple[str, str], ...]]:
        '''
        Internal helper to recursively walk the graph to find all connected nodes.

        This walk respects the runtime boundaries (`-from`, `-to`, `-prune`).

        Args:
            node (tuple(str,str)): The node to start the walk from.
            path (list, optional): The path taken so far, used for cycle
                detection. Defaults to None.
            reverse (bool, optional): If True, walks backwards along inputs.
                If False, walks forwards along outputs. Defaults to True.

        Returns:
            set[tuple(str,str)]: The set of nodes visited during the walk.
        '''
        if node in self.__prune:
            return set()

        if path is None:
            path = []

        if node in path:
            return set(path)

        path.append(node)
        if reverse:
            if node in self.__from:
                return set(path)
        else:
            if node in self.__to:
                return set(path)

        nodes = set()
        if reverse:
            for input_node in self.__base.get(*node, "input"):
                nodes.update(self.__walk_graph(input_node, path=path, reverse=reverse))
        else:
            for output_node in self.__base.get_node_outputs(*node):
                nodes.update(self.__walk_graph(output_node, path=path, reverse=reverse))
        return nodes

    def __compute_graph(self) -> None:
        '''
        Internal helper to precompute the runtime graph information.

        This method determines the final set of nodes, entry/exit points, and
        the execution order based on the runtime constraints.
        '''

        self.__nodes = set()
        for entry in self.__to:
            self.__nodes.update(self.__walk_graph(entry))
        self.__nodes = tuple(sorted(self.__nodes))

        # Update to and from
        self.__from = tuple([
            node for node in self.__from
            if not self.__base.get(*node, "input") or
            all([in_node not in self.__nodes for in_node in self.__base.get(*node, "input")])
        ])
        self.__to = tuple([
            node for node in self.__to
            if not self.__base.get_node_outputs(*node) or
            all([out_node not in self.__nodes for out_node in self.__base.get_node_outputs(*node)])
        ])

        ordering = []
        for level_nodes in self.__base.get_execution_order():
            level_exec = [node for node in level_nodes if node in self.__nodes]
            if level_exec:
                ordering.append(tuple(level_exec))
        self.__execution_order = tuple(ordering)

    def get_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Returns the nodes that are part of this runtime graph.

        Returns:
            tuple[tuple(str,str)]: A tuple of all nodes in the runtime graph.
        '''
        return self.__nodes

    def get_execution_order(self) -> Tuple[Tuple[Tuple[str, str], ...], ...]:
        '''
        Returns the execution order of the nodes in this runtime graph.

        Returns:
            tuple[tuple[tuple(str,str)]]: A tuple of tuples representing
            parallel execution levels.
        '''
        return self.__execution_order

    def get_entry_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Returns the entry nodes for this runtime graph.

        This includes user-defined `-from` nodes (if they are part of
        the graph) and any nodes whose inputs are pruned or outside the
        computed graph.

        Returns:
            tuple[tuple(str,str)]: A sorted tuple of all entry nodes.
        '''
        return self.__from

    def get_exit_nodes(self) -> Tuple[Tuple[str, str], ...]:
        '''
        Returns the exit nodes for this runtime graph.

        Returns:
            tuple[tuple(str,str)]: A tuple of all exit nodes.
        '''
        return self.__to

    def get_nodes_starting_at(self, step: str, index: Union[str, int]) \
            -> Tuple[Tuple[str, str], ...]:
        '''
        Returns all nodes reachable from a given starting node in this runtime graph.

        Args:
            step (str): The step name of the starting node.
            index (str or int): The index of the starting node.

        Returns:
            tuple[tuple(str,str)]: A tuple of all reachable nodes.
        '''
        index = str(index)

        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node")

        return tuple(sorted(self.__walk_graph((step, str(index)), reverse=False)))

    def get_node_inputs(self, step: str, index: str, record: Optional["RecordSchema"] = None) \
            -> List[Tuple[str, str]]:
        '''
        Gets the inputs for a specific node in the runtime graph.

        If a `record` object is provided, this method will traverse through
        any input nodes that were SKIPPED to find the true, non-skipped inputs.

        Args:
            step (str): Step name of the node.
            index (str): Index of the node.
            record (Schema, optional): A schema object containing run records.
                Used to check the status of input nodes. Defaults to None.

        Returns:
            list[tuple(str,str)]: A list of input nodes.
        '''
        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node")

        if record is None:
            inputs = set()
            for in_step, in_index in self.__base.get(step, index, "input"):
                if (in_step, in_index) not in self.get_nodes():
                    continue
                inputs.add((in_step, in_index))
            return sorted(inputs)

        inputs = set()
        for in_step, in_index in self.__base.get(step, index, "input"):
            if (in_step, in_index) not in self.get_nodes():
                continue

            if record.get("status", step=in_step, index=in_index) == NodeStatus.SKIPPED:
                inputs.update(self.get_node_inputs(in_step, in_index, record=record))
            else:
                inputs.add((in_step, in_index))
        return sorted(inputs)

    def get_completed_nodes(self, record: Optional["RecordSchema"] = None) -> List[Tuple[str, str]]:
        '''
        Finds all nodes in this runtime graph that have successfully completed.

        Args:
            record (Schema, optional): A schema object containing run records
                to check for node status. Defaults to None.

        Returns:
            list[tuple(str,str)]: A sorted list of successfully completed nodes.
        '''
        if not record:
            return []

        nodes = set()
        for step, index in self.get_nodes():
            if NodeStatus.is_success(record.get("status", step=step, index=index)):
                nodes.add((step, index))

        return sorted(nodes)

    @staticmethod
    def validate(flow: Flowgraph,
                 from_steps: Optional[Union[List[str], Set[str]]] = None,
                 to_steps: Optional[Union[List[str], Set[str]]] = None,
                 prune_nodes: Optional[Union[List[Tuple[str, str]], Set[Tuple[str, str]]]] = None,
                 logger: Optional[logging.Logger] = None) -> bool:
        '''
        Validates runtime options against a flowgraph.

        Checks for undefined steps and ensures that pruning does not break
        the graph by removing all entry/exit points or creating disjoint paths.

        Args:
            flow (Flowgraph): The flowgraph to validate against.
            from_steps (list[str], optional): List of start steps. Defaults to None.
            to_steps (list[str], optional): List of end steps. Defaults to None.
            prune_nodes (list[tuple(str,str)], optional): List of nodes to prune.
                Defaults to None.
            logger (logging.Logger, optional): Logger for error reporting.
                Defaults to None.

        Returns:
            bool: True if the runtime configuration is valid, False otherwise.
        '''
        all_steps = set([step for step, _ in flow.get_nodes()])

        if from_steps:
            from_steps = set(from_steps)
        else:
            from_steps = set()

        if to_steps:
            to_steps = set(to_steps)
        else:
            to_steps = set()

        if prune_nodes:
            prune_nodes = set(prune_nodes)
        else:
            prune_nodes = set()

        error = False

        # Check for undefined steps
        for step in sorted(from_steps.difference(all_steps)):
            if logger:
                logger.error(f'From {step} is not defined in the {flow.name} flowgraph')
            error = True

        for step in sorted(to_steps.difference(all_steps)):
            if logger:
                logger.error(f'To {step} is not defined in the {flow.name} flowgraph')
            error = True

        # Check for undefined prunes
        for step, index in sorted(prune_nodes.difference(flow.get_nodes())):
            if logger:
                logger.error(f'{step}/{index} is not defined in the {flow.name} flowgraph')
            error = True

        if not error:
            runtime = RuntimeFlowgraph(
                flow,
                from_steps=from_steps,
                to_steps=to_steps,
                prune_nodes=prune_nodes)
            unpruned = RuntimeFlowgraph(
                flow,
                from_steps=from_steps,
                to_steps=to_steps)

            # Check for missing entry or exit steps
            unpruned_exits = set([step for step, _ in unpruned.get_exit_nodes()])
            runtime_exits = set([step for step, _ in runtime.get_exit_nodes()])
            for step in unpruned_exits.difference(runtime_exits):
                if logger:
                    logger.error(f'pruning removed all exit nodes for {step} in the {flow.name} '
                                 'flowgraph')
                error = True

            unpruned_entry = set([step for step, _ in unpruned.get_entry_nodes()])
            runtime_entry = set([step for step, _ in runtime.get_entry_nodes()])
            for step in unpruned_entry.difference(runtime_entry):
                if logger:
                    logger.error(f'pruning removed all entry nodes for {step} in the {flow.name} '
                                 'flowgraph')
                error = True

            if not error:
                # Check for missing paths
                missing = []
                found_any = False
                for entrynode in runtime.get_entry_nodes():
                    found = False
                    for exitnode in runtime.get_exit_nodes():
                        if entrynode in runtime.__walk_graph(exitnode):
                            found = True
                    if not found:
                        exits = ",".join([f"{step}/{index}"
                                          for step, index in runtime.get_exit_nodes()])
                        missing.append(f'no path from {entrynode[0]}/{entrynode[1]} to {exits} '
                                       f'in the {flow.name} flowgraph')
                    if found:
                        found_any = True
                if not found_any:
                    error = True
                    if logger:
                        for msg in missing:
                            logger.error(msg)

        return not error


class FlowgraphNodeSchema(BaseSchema):
    '''
    Schema definition for a single node within a flowgraph.

    This class defines the parameters that can be set on a per-node
    basis, such as inputs, weights, goals, and the task to execute.
    '''

    def __init__(self):
        '''
        Initializes a new FlowgraphNodeSchema.
        '''
        super().__init__()
        schema_flowgraph(self)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the metadata type for `getdict` serialization.
        """
        return FlowgraphNodeSchema.__name__

    def add_args(self, arg: Union[List[str], str], clobber: bool = False):
        '''
        Adds command-line arguments specific to this node.

        Args:
            arg (list[str] or str): The argument or list of arguments to add.
            clobber (bool, optional): If True, replaces all existing args
                with the new ones. If False, appends. Defaults to False.
        '''
        if clobber:
            self.set("args", arg)
        else:
            self.add("args", arg)

    def get_args(self) -> List[str]:
        '''
        Gets the list of command-line arguments for this node.

        Returns:
            list[str]: The list of arguments.
        '''
        return self.get("args")

    def add_weight(self, metric: str, weight: float):
        '''
        Sets a weight for a specific metric for this node.

        Weights are used in optimization tasks to define the "cost" of a
        particular metric.

        Args:
            metric (str): The name of the metric (e.g., 'errors', 'area').
            weight (float): The weight value.
        '''
        self.set("weight", metric, weight)

    def get_weight(self, metric: str) -> Optional[float]:
        '''
        Gets the weight for a specific metric for this node.

        Args:
            metric (str): The name of the metric.

        Returns:
            float or None: The weight value, or None if not set.
        '''
        if metric not in self.getkeys("weight"):
            return None
        return self.get("weight", metric)

    def add_goal(self, metric: str, weight: float):
        '''
        Sets a goal for a specific metric for this node.

        Goals are used to determine if a task run is acceptable.

        Args:
            metric (str): The name of the metric (e.g., 'errors', 'setupwns').
            weight (float): The goal value (e.g., 0 for 'errors').
        '''
        self.set("goal", metric, weight)

    def get_goal(self, metric: str) -> Optional[float]:
        '''
        Gets the goal for a specific metric for this node.

        Args:
            metric (str): The name of the metric.

        Returns:
            float or None: The goal value, or None if not set.
        '''
        if metric not in self.getkeys("goal"):
            return None
        return self.get("goal", metric)

    def get_tool(self) -> str:
        '''
        Gets the tool associated with this node.

        Returns:
            str: The name of the tool (e.g., 'openroad').
        '''
        return self.get("tool")

    def get_task(self) -> str:
        '''
        Gets the task associated with this node.

        Returns:
            str: The name of the task (e.g., 'place').
        '''
        return self.get("task")

    def get_taskmodule(self) -> str:
        '''
        Gets the fully qualified Python module/class for this node's task.

        Returns:
            str: The task module string (e.g.,
            'siliconcompiler.tools.openroad/Place').
        '''
        return self.get("taskmodule")

    def get_input(self) -> List[Tuple[str, str]]:
        '''
        Gets the list of input nodes (dependencies) for this node.

        Returns:
            list[tuple(str,str)]: A list of (step, index) tuples.
        '''
        return self.get("input")

    def has_input(self) -> bool:
        '''
        Checks if this node has any inputs.

        Returns:
            bool: True if the node has one or more inputs, False otherwise.
        '''
        return bool(self.get_input())


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(schema: FlowgraphNodeSchema):
    '''
    Defines the schema parameters for a flowgraph node.

    This function is called to populate a `FlowgraphNodeSchema` with
    parameters that define a node's properties, such as its inputs,
    weights, goals, and the tool/task it executes.

    Args:
        schema (FlowgraphNodeSchema): The schema object to configure.
    '''
    edit = EditableSchema(schema)

    # flowgraph input
    edit.insert(
        'input',
        Parameter(
            '[(str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Node inputs",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api: flow.add('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))"],
            help=trim("""
            A list of inputs for this flowgraph node, where each input is
            specified as a (step, index) tuple. This defines the dependencies
            of this node.
            """)))

    # flowgraph metric weights
    metric = 'default'
    edit.insert(
        'weight', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            defvalue=0.0,
            shorthelp="Flowgraph: Metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api: flow.set('flowgraph', 'asicflow', 'cts', '0', 'weight', 'area_cells', 1.0)"],
            help=trim("""
            Weights specified on a per-node and per-metric basis, used by
            optimization tasks (like 'minimum') to calculate a "goodness"
            score for a run. The score is typically a weighted sum of
            metric results.
            """)))

    # flowgraph metric goals
    edit.insert(
        'goal', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 errors 0'",
                "api: flow.set('flowgraph', 'asicflow', 'cts', '0', 'goal', 'errors', 0)"],
            help=trim("""
            Goals specified on a per-node and per-metric basis used to
            determine whether a task run is considered successful. A task run
            may be considered failing if the absolute value of any of its
            reported metrics is larger than the goal for that metric (if set).
            This is often used for metrics like 'errors' or 'setupwns'
            where the goal is 0.
            """)))

    # flowgraph tool
    edit.insert(
        'tool',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Tool selection",
            switch="-flowgraph_tool 'flow step index <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: flow.set('flowgraph', 'asicflow', 'place', '0', 'tool', 'openroad')"],
            help=trim("""
            Name of the tool (e.g., 'openroad', 'yosys', 'builtin') that
            this node will execute.
            """)))

    # task (belonging to tool)
    edit.insert(
        'task',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Task selection",
            switch="-flowgraph_task 'flow step index <str>'",
            example=[
                "cli: -flowgraph_task 'asicflow myplace 0 place'",
                "api: flow.set('flowgraph', 'asicflow', 'myplace', '0', 'task', 'place')"],
            help=trim("""
            Name of the task (e.g., 'place', 'syn', 'join') associated
            with the node's tool.
            """)))

    # task module
    edit.insert(
        'taskmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Task module",
            switch="-flowgraph_taskmodule 'flow step index <str>'",
            example=[
                "cli: -flowgraph_taskmodule 'asicflow place 0 "
                "siliconcompiler.tools.openroad/Place'",
                "api: flow.set('flowgraph', 'asicflow', 'place', '0', 'taskmodule', "
                "'siliconcompiler.tools.openroad/Place')"],
            help=trim("""
            Full Python module path and class name of the task, formatted as
            '<full.module.path>/<ClassName>'. This is used to import and
            instantiate the correct Task class for setup and execution.
            """)))

    # flowgraph arguments
    edit.insert(
        'args',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: Node-specific arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 buffer_cells'",
                "api: flow.add('flowgraph', 'asicflow', 'cts', '0', 'args', 'buffer_cells')"],
            help=trim("""
            User-specified arguments passed to the task's `setup()` method.
            This allows for customizing a specific node's behavior without
            affecting other nodes running the same task.
            """)))
