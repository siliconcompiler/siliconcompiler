import inspect
import importlib

from siliconcompiler import Schema
from siliconcompiler.schema import BaseSchema, NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import NodeStatus


class FlowgraphSchema(NamedSchema):
    '''
    Schema for defining and interacting with a flowgraph.

    A flowgraph is a directed acyclic graph (DAG) that represents the
    compilation flow. Each node in the graph is a step/index pair that

    maps to a specific tool task, and edges represent dependencies between
    these tasks.
    '''

    def __init__(self, name=None):
        '''
        Initializes a new FlowgraphSchema object.

        Args:
            name (str, optional): The name of the flowgraph. Defaults to None.
        '''
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert("default", "default", FlowgraphNodeSchema())

        self.__clear_cache()

    def __clear_cache(self):
        '''
        Clears the internal cache for memoized flowgraph properties.

        This should be called any time the graph structure is modified.
        '''

        self.__cache_nodes = None
        self.__cache_nodes_entry = None
        self.__cache_nodes_exit = None
        self.__cache_execution_order_forward = None
        self.__cache_execution_order_reverse = None

        self.__cache_node_outputs = None

        self.__cache_tasks = None

    def node(self, step, task, index=0):
        '''
        Creates a flowgraph node.

        Creates a flowgraph node by binding a step to a tool-specific task.
        A tool can be an external executable or one of the built-in functions
        in the SiliconCompiler framework (e.g., minimum, maximum, join).

        The method modifies the following schema parameters:

        * `['<step>', '<index>', 'tool']`
        * `['<step>', '<index>', 'task']`
        * `['<step>', '<index>', 'taskmodule']`

        Args:
            step (str): Step name for the node.
            task (module or str): The task to associate with this node. Can be
                a module object or a string in the format '<tool>.<task>'.
            index (int or str): Index for the step. Defaults to 0.

        Examples:
            >>> import siliconcompiler.tools.openroad as openroad
            >>> flow.node('place', openroad.place, index=0)
            # Creates a node for the 'place' task in the 'openroad' tool,
            # identified by step='place' and index=0.
        '''

        if step in (Schema.GLOBAL_KEY, 'default', 'sc_collected_files'):
            raise ValueError(f"{step} is a reserved name")

        index = str(index)
        if index in (Schema.GLOBAL_KEY, 'default'):
            raise ValueError(f"{index} is a reserved name")

        if '/' in step:
            raise ValueError(f"{step} is not a valid step, it cannot contain '/'")
        if '/' in index:
            raise ValueError(f"{index} is not a valid index, it cannot contain '/'")

        # Determine task name and module
        task_module = None
        if isinstance(task, str):
            task_module = task
        elif inspect.ismodule(task):
            task_module = task.__name__
        else:
            raise ValueError(f"{task} is not a string or module and cannot be used to "
                             "setup a task.")

        task_parts = task_module.split('.')
        if len(task_parts) < 2:
            raise ValueError(f"{task} is not a valid task, it must be associated with "
                             "a tool '<tool>.<task>'.")

        tool_name, task_name = task_parts[-2:]

        # bind tool to node
        self.set(step, index, 'tool', tool_name)
        self.set(step, index, 'task', task_name)
        self.set(step, index, 'taskmodule', task_module)

        self.__clear_cache()

    def edge(self, tail, head, tail_index=0, head_index=0):
        '''
        Creates a directed edge from a tail node to a head node.

        Connects the output of a tail node with the input of a head node by
        setting the 'input' field of the head node in the schema flowgraph.

        The method modifies the following parameter:

        * `['<head>', '<head_index>', 'input']`

        Args:
            tail (str): Step name of the tail node.
            head (str): Step name of the head node.
            tail_index (int or str): Index of the tail node. Defaults to 0.
            head_index (int or str): Index of the head node. Defaults to 0.

        Examples:
            >>> chip.edge('place', 'cts')
            # Creates a directed edge from ('place', '0') to ('cts', '0').
        '''
        head_index = str(head_index)
        tail_index = str(tail_index)

        for step, index in [(head, head_index), (tail, tail_index)]:
            if not self.valid(step, index):
                raise ValueError(f"{step}/{index} is not a defined node in {self.name}.")

        tail_node = (tail, tail_index)
        if tail_node in self.get(head, head_index, 'input'):
            return

        self.add(head, head_index, 'input', tail_node)

        self.__clear_cache()

    def remove_node(self, step, index=None):
        '''
        Removes a flowgraph node and reconnects its inputs to its outputs.

        Args:
            step (str): Step name of the node to remove.
            index (int or str, optional): Index of the node to remove. If None,
                all nodes for the given step are removed. Defaults to None.
        '''

        if step not in self.getkeys():
            raise ValueError(f'{step} is not a valid step in {self.name}')

        if index is None:
            # Iterate over all indexes
            for index in self.getkeys(step):
                self.remove_node(step, index)
            return

        index = str(index)
        if index not in self.getkeys(step):
            raise ValueError(f'{index} is not a valid index for {step} in {self.name}')

        # Save input edges
        node = (step, index)
        node_inputs = self.get(step, index, 'input')

        # remove node
        self.remove(step, index)

        # remove step if all nodes a gone
        if len(self.getkeys(step)) == 0:
            self.remove(step)

        for flow_step in self.getkeys():
            for flow_index in self.getkeys(flow_step):
                inputs = self.get(flow_step, flow_index, 'input')
                if node in inputs:
                    inputs = [inode for inode in inputs if inode != node]
                    inputs.extend(node_inputs)
                    self.set(flow_step, flow_index, 'input', sorted(set(inputs)))

        self.__clear_cache()

    def insert_node(self, step, task, before_step, index=0, before_index=0):
        '''
        Inserts a new node in the graph before a specified node.

        The new node is placed between the `before` node and all of its
        original inputs.

        Args:
            step (str): Step name for the new node.
            task (module or str): Task to associate with the new node.
            before_step (str): Step name of the existing node to insert before.
            index (int or str): Index for the new node. Defaults to 0.
            before_index (int or str): Index of the existing node. Defaults to 0.
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
    def graph(self, subflow, name=None):
        '''
        Instantiates a sub-flowgraph within the current flowgraph.

        Args:
            subflow (FlowgraphSchema): The flowgraph to instantiate.
            name (str, optional): A prefix to add to the names of the
                instantiated steps to ensure they are unique. Defaults to None.

        Raises:
            ValueError: If `subflow` is not a `FlowgraphSchema` object, or if
                a step from the sub-flowgraph already exists in the current graph.
        '''
        if not isinstance(subflow, FlowgraphSchema):
            raise ValueError(f"subflow must a FlowgraphSchema, not: {type(subflow)}")

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

            if name is None:
                continue

            # rename inputs
            for index in self.getkeys(newstep):
                all_inputs = self.get(newstep, index, 'input')
                self.set(newstep, index, 'input', [])
                for in_step, in_index in all_inputs:
                    newin = name + "." + in_step
                    self.add(newstep, index, 'input', (newin, in_index))

        self.__clear_cache()

    def get_nodes(self):
        '''
        Returns a sorted tuple of all nodes defined in this flowgraph.

        A node is represented as a `(step, index)` tuple.

        Returns:
            tuple[tuple(str,str)]: All nodes in the graph.
        '''
        if self.__cache_nodes is not None:
            return self.__cache_nodes

        nodes = []
        for step in self.getkeys():
            for index in self.getkeys(step):
                nodes.append((step, index))

        self.__cache_nodes = tuple(sorted(set(nodes)))

        return self.__cache_nodes

    def get_entry_nodes(self):
        '''
        Collects all nodes that are entry points to the flowgraph.

        Entry nodes are those with no inputs.

        Returns:
            tuple[tuple(str,str)]: All entry nodes in the graph.
        '''

        if self.__cache_nodes_entry is not None:
            return self.__cache_nodes_entry

        nodes = []
        for step, index in self.get_nodes():
            if not self.get(step, index, 'input'):
                nodes.append((step, index))

        self.__cache_nodes_entry = tuple(sorted(set(nodes)))

        return self.__cache_nodes_entry

    def get_exit_nodes(self):
        '''
        Collects all nodes that are exit points of the flowgraph.

        Exit nodes are those that are not inputs to any other node.

        Returns:
            tuple[tuple(str,str)]: All exit nodes in the graph.
        '''

        if self.__cache_nodes_exit is not None:
            return self.__cache_nodes_exit

        inputnodes = []
        for step, index in self.get_nodes():
            inputnodes.extend(self.get(step, index, 'input'))
        nodes = []
        for step, index in self.get_nodes():
            if (step, index) not in inputnodes:
                nodes.append((step, index))

        self.__cache_nodes_exit = tuple(sorted(set(nodes)))

        return self.__cache_nodes_exit

    def get_execution_order(self, reverse=False):
        '''
        Generates a topologically sorted list of nodes for execution.

        Args:
            reverse (bool): If True, the order is reversed, from exit nodes
                to entry nodes. Defaults to False.

        Returns:
            tuple[tuple[tuple(str,str)]]: A tuple of tuples, where each inner
            tuple represents a level of nodes that can be executed in parallel.
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
            for istep, iindex in self.get(step, index, 'input'):
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

    def get_node_outputs(self, step, index):
        '''
        Returns the nodes that the given node provides input to.

        Args:
            step (str): Step name of the source node.
            index (str or int): Index of the source node.

        Returns:
            tuple[tuple(str,str)]: A tuple of destination nodes.
        '''

        index = str(index)

        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node")

        if self.__cache_node_outputs is not None:
            return self.__cache_node_outputs[(step, index)]

        self.__cache_node_outputs = {}

        input_map = {}
        for istep, iindex in self.get_nodes():
            input_map[(istep, iindex)] = self.get(istep, iindex, 'input')
            self.__cache_node_outputs[(istep, iindex)] = set()

        for src_node, dst_nodes in input_map.items():
            for dst_node in dst_nodes:
                if dst_node not in self.__cache_node_outputs:
                    self.__cache_node_outputs[dst_node] = set()
                self.__cache_node_outputs[dst_node].add(src_node)

        self.__cache_node_outputs = {
            node: tuple(sorted(outputs)) for node, outputs in self.__cache_node_outputs.items()
        }

        return self.__cache_node_outputs[(step, index)]

    def __find_loops(self, step, index, path=None):
        '''
        Internal helper to search for loops in the graph via depth-first search.

        Args:
            step (str): Step name to start from.
            index (str): Index name to start from.
            path (list, optional): The path taken so far. Defaults to None.

        Returns:
            list: A list of nodes forming a loop, or None if no loop is found.
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

    def validate(self, logger=None):
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
            input_nodes = self.get(step, index, 'input')
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

        # detect loops
        for start_step, start_index in self.get_entry_nodes():
            loop_path = self.__find_loops(start_step, start_index)
            if loop_path:
                error = True
                if logger:
                    loop_path = [f"{step}/{index}" for step, index in loop_path]
                    logger.error(f"{' -> '.join(loop_path)} forms a loop in {self.name}")

        return not error

    def __get_task_module(self, name):
        '''
        Internal helper to import and cache a task module by name.
        '''
        # Create cache
        if self.__cache_tasks is None:
            self.__cache_tasks = {}

        if name in self.__cache_tasks:
            return self.__cache_tasks[name]

        self.__cache_tasks[name] = importlib.import_module(name)
        return self.__cache_tasks[name]

    def get_task_module(self, step, index):
        """
        Returns the imported Python module for a given task node.

        Args:
            step (str): Step name of the node.
            index (int or str): Index of the node.

        Returns:
            module: The imported task module.
        """

        index = str(index)

        if (step, index) not in self.get_nodes():
            raise ValueError(f"{step}/{index} is not a valid node in {self.name}.")

        return self.__get_task_module(self.get(step, index, 'taskmodule'))

    def get_all_tasks(self):
        '''
        Returns all unique task modules used in this flowgraph.

        Returns:
            set[module]: A set of all imported task modules.
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

        return FlowgraphSchema.__name__


class RuntimeFlowgraph:
    '''
    A runtime representation of a flowgraph for a specific execution.

    This class creates a "view" of a base flowgraph that considers runtime
    options such as the start step (`-from`), end step (`-to`), and nodes to
    exclude (`-prune`). It computes the precise subgraph of nodes that need
    to be executed for a given run.
    '''

    def __init__(self, base, args=None, from_steps=None, to_steps=None, prune_nodes=None):
        '''
        Initializes a new RuntimeFlowgraph.

        Args:
            base (FlowgraphSchema): The base flowgraph to create a view of.
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
        if not all([hasattr(base, attr) for attr in dir(FlowgraphSchema)]):
            raise ValueError(f"base must a FlowgraphSchema, not: {type(base)}")

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

    def __walk_graph(self, node, path=None, reverse=True):
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

    def __compute_graph(self):
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

    def get_nodes(self):
        '''
        Returns the nodes that are part of this runtime graph.

        Returns:
            tuple[tuple(str,str)]: A tuple of all nodes in the runtime graph.
        '''
        return self.__nodes

    def get_execution_order(self):
        '''
        Returns the execution order of the nodes in this runtime graph.

        Returns:
            tuple[tuple[tuple(str,str)]]: A tuple of tuples representing
            parallel execution levels.
        '''
        return self.__execution_order

    def get_entry_nodes(self):
        '''
        Returns the entry nodes for this runtime graph.

        Returns:
            tuple[tuple(str,str)]: A tuple of all entry nodes.
        '''
        return self.__from

    def get_exit_nodes(self):
        '''
        Returns the exit nodes for this runtime graph.

        Returns:
            tuple[tuple(str,str)]: A tuple of all exit nodes.
        '''
        return self.__to

    def get_nodes_starting_at(self, step, index):
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

    def get_node_inputs(self, step, index, record=None):
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

    def get_completed_nodes(self, record=None):
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
    def validate(flow, from_steps=None, to_steps=None, prune_nodes=None, logger=None):
        '''
        Validates runtime options against a flowgraph.

        Checks for undefined steps and ensures that pruning does not break
        the graph by removing all entry/exit points or creating disjoint paths.

        Args:
            flow (FlowgraphSchema): The flowgraph to validate against.
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


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(schema):
    '''
    Defines the schema parameters for a flowgraph node.

    This function is called to populate a schema with parameters that
    define a node's properties, such as its inputs, weights, goals, and the
    tool/task it executes.

    Args:
        schema (Schema): The schema object to configure.
    '''
    schema = EditableSchema(schema)

    # flowgraph input
    schema.insert(
        'input',
        Parameter(
            '[(str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: step input",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))"],
            help=trim("""A list of inputs for the current step and index, specified as a
            (step, index) tuple.""")))

    # flowgraph metric weights
    metric = 'default'
    schema.insert(
        'weight', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            defvalue=0.0,
            shorthelp="Flowgraph: metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'weight', 'area_cells', 1.0)"],
            help=trim("""Weights specified on a per step and per metric basis used to give
            effective "goodness" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")))

    schema.insert(
        'goal', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'goal', 'errors', 0)"],
            help=trim("""Goals specified on a per step and per metric basis used to
            determine whether a certain task can be considered when merging
            multiple tasks at a minimum or maximum node. A task is considered
            failing if the absolute value of any of its metrics are larger than
            the goal for that metric, if set.""")))

    # flowgraph tool
    schema.insert(
        'tool',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: tool selection",
            switch="-flowgraph_tool 'flow step index <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'tool', 'openroad')"],
            help=trim("""Name of the tool name used for task execution.""")))

    # task (belonging to tool)
    schema.insert(
        'task',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task selection",
            switch="-flowgraph_task 'flow step index <str>'",
            example=[
                "cli: -flowgraph_task 'asicflow myplace 0 place'",
                "api: chip.set('flowgraph', 'asicflow', 'myplace', '0', 'task', 'place')"],
            help=trim("""Name of the tool associated task used for step execution.""")))

    schema.insert(
        'taskmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task module",
            switch="-flowgraph_taskmodule 'flow step index <str>'",
            example=[
                "cli: -flowgraph_taskmodule 'asicflow place 0 "
                "siliconcompiler.tools.openroad.place'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'taskmodule', "
                "'siliconcompiler.tools.openroad.place')"],
            help=trim("""
            Full python module name of the task module used for task setup and execution.
            """)))

    # flowgraph arguments
    schema.insert(
        'args',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api: chip.add('flowgraph', 'asicflow', 'cts', '0', 'args', '0')"],
            help=trim("""User specified flowgraph string arguments specified on a per
            step and per index basis.""")))
