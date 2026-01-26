from typing import TYPE_CHECKING

from siliconcompiler.tools.builtin import BuiltinTask

if TYPE_CHECKING:
    from siliconcompiler import Flowgraph


class Wait(BuiltinTask):
    '''
    A wait task that stalls the flow until all inputs are available.
    '''
    def __init__(self):
        super().__init__()

    def _set_io_files(self):
        # No file IO needed for wait task
        return

    def task(self):
        return "wait"

    @staticmethod
    def __has_path(flowgraph: "Flowgraph", source: tuple, target: tuple) -> bool:
        '''
        Helper method to check if there's any path from source to target node.

        Args:
            flowgraph: The flowgraph to search.
            source: Tuple of (step, index) for the source node.
            target: Tuple of (step, index) for the target node.

        Returns:
            bool: True if there's a path from source to target, False otherwise.
        '''
        if source == target:
            return True

        visited = set()
        to_visit = [source]

        while to_visit:
            current = to_visit.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)

            # Add all output nodes to the queue
            outputs = flowgraph.get_node_outputs(current[0], current[1])
            to_visit.extend(outputs)

        return False

    @staticmethod
    def serialize_tool_tasks(flowgraph: "Flowgraph", tool_name: str) -> None:
        '''
        Adds wait tasks between nodes of the same tool that could execute in parallel.

        This method inserts `Wait` task nodes between nodes that use the same
        tool, but only when those nodes could execute in parallel (i.e., there's
        no dependency path between them). This ensures that tool instances don't
        execute in parallel, while avoiding unnecessary wait tasks for nodes
        that already have a dependency relationship.

        The method modifies the flowgraph in-place by:
        1. Finding all nodes that use the specified tool
        2. For each pair of tool nodes with no dependency path, inserting a wait task
        3. Using naming convention: {target_step}.wait
           (named after the node being delayed)

        Args:
            flowgraph: The flowgraph to modify.
            tool_name (str): The name of the tool (e.g., 'openroad', 'yosys').
                All nodes using this tool will be serialized.

        Raises:
            ValueError: If the flowgraph is invalid or tool_name is empty.

        Example:
            >>> flow = Flowgraph("myflow")
            >>> flow.node("place1", openroad.Place, index=0)
            >>> flow.node("syn", yosys.Syn, index=0)
            >>> flow.node("place2", openroad.Place, index=1)
            >>> flow.edge("place1", "syn")
            >>> flow.edge("syn", "place2")
            >>> Wait.serialize_tool_tasks(flow, "openroad")
            >>> # No wait task added - place1 and place2 already have a dependency path
        '''
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError(f"tool_name must be a non-empty string, not {tool_name}")

        if not flowgraph.validate():
            raise ValueError(f"Flowgraph '{flowgraph.name}' is invalid before serialization")

        # Find all nodes using the specified tool
        tool_nodes = []
        for step, index in flowgraph.get_nodes():
            graph_node = flowgraph.get_graph_node(step, index)
            if graph_node.get_tool() == tool_name:
                tool_nodes.append((step, index))

        if not tool_nodes or len(tool_nodes) < 2:
            # Need at least 2 nodes to create wait tasks
            return

        # Sort nodes by execution order to establish a consistent serialization
        execution_order = flowgraph.get_execution_order()
        node_order_map = {}
        for level_idx, level in enumerate(execution_order):
            for node_idx, node in enumerate(level):
                node_order_map[node] = (level_idx, node_idx)

        sorted_tool_nodes = sorted(
            tool_nodes, key=lambda n: node_order_map.get(n, (float('inf'), 0)))

        # Check if there are pairs without dependency paths that need serialization
        needs_serialization = False
        for i in range(len(sorted_tool_nodes)):
            for j in range(i + 1, len(sorted_tool_nodes)):
                node1 = sorted_tool_nodes[i]
                node2 = sorted_tool_nodes[j]
                if not Wait.__has_path(flowgraph, node1, node2):
                    needs_serialization = True
                    break
            if needs_serialization:
                break

        if not needs_serialization:
            # All tool nodes already have dependency paths, no wait nodes needed
            return

        # Create wait nodes between each pair of consecutive tool nodes
        # Chain: tool[0] -> wait_1 -> tool[1] -> wait_2 -> tool[2] -> ...
        for i in range(len(sorted_tool_nodes) - 1):
            curr_node = sorted_tool_nodes[i]
            next_node = sorted_tool_nodes[i + 1]

            # Check if there's already a dependency path between them
            if Wait.__has_path(flowgraph, curr_node, next_node):
                # Already serialized, skip
                continue

            # Create wait node named after the next node (the one being delayed)
            wait_step = f"{next_node[0]}.wait"
            wait_index = next_node[1]
            flowgraph.node(wait_step, Wait(), index=wait_index)

            # Connect: curr_node -> wait_node -> next_node
            flowgraph.edge(curr_node[0], wait_step, tail_index=curr_node[1], head_index=wait_index)
            flowgraph.edge(wait_step, next_node[0], tail_index=wait_index, head_index=next_node[1])
