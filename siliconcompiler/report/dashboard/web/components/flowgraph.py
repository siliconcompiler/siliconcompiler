"""
Utility functions for generating and configuring the interactive flowgraph
display for the web dashboard using the `streamlit-agraph` library.
"""
from siliconcompiler.report import report
from siliconcompiler import NodeStatus

from streamlit_agraph import Node, Edge, Config


# --- Constants ---
# Defines the color scheme for nodes based on their execution status.
NODE_COLORS = {
    NodeStatus.SUCCESS: '#70db70',  # green
    NodeStatus.SKIPPED: '#ffc299',  # orange
    NodeStatus.PENDING: '#6699ff',  # blue
    NodeStatus.QUEUED: '#6699ff',   # blue
    NodeStatus.RUNNING: '#ffff4d',  # yellow
    NodeStatus.ERROR: '#ff1a1a',    # red
    NodeStatus.TIMEOUT: '#ff1a1a',  # red
    "Unknown": '#6699ff',           # blue
}


def get_nodes_and_edges(project):
    """
    Constructs the nodes and edges for the flowgraph from a project object.

    This function traverses the project's flowgraph, creating styled `Node` and
    `Edge` objects for `streamlit-agraph`. Node colors are based on status,
    and edge styles (width, color, dashes) indicate the execution path and
    dependencies.

    Args:
        project (Project): The project object containing the flowgraph data.

    Returns:
        tuple: A tuple containing two lists:
            - list[Node]: A list of `streamlit_agraph.Node` objects.
            - list[Edge]: A list of `streamlit_agraph.Edge` objects.
    """
    nodes = []
    edges = []

    if not project.get('option', 'flow'):
        return nodes, edges

    # --- Style Configuration ---
    default_node_border_width = 1
    successful_path_node_width = 3
    default_edge_width = 3
    successful_path_edge_width = 5

    # --- Data Extraction ---
    node_dependencies = report.get_flowgraph_edges(project)
    successful_path = report.get_flowgraph_path(project)
    flow = project.get('option', 'flow')
    flowgraph_schema = project.get("flowgraph", flow, field="schema")
    entry_exit_nodes = flowgraph_schema.get_entry_nodes() + flowgraph_schema.get_exit_nodes()

    # --- Node and Edge Creation ---
    for step, index in node_dependencies:
        # 1. Build the Node
        node_border_width = default_node_border_width
        if (step, index) in entry_exit_nodes:
            node_border_width = successful_path_node_width

        node_status = project.get('record', 'status', step=step, index=index)
        node_color = NODE_COLORS.get(node_status, NODE_COLORS["Unknown"])

        tool = flowgraph_schema.get(step, index, "tool")
        task = flowgraph_schema.get(step, index, "task")
        node_name = f'{step}/{index}'
        label = f"{node_name}\n{tool}/{task}"
        if tool == 'builtin':
            label = f"{node_name}\n{tool}"

        nodes.append(Node(
            id=node_name,
            label=label,
            color=node_color,
            borderWidth=node_border_width,
            shape='oval',
            fixed=True))

        # 2. Build Edges to this Node
        path_taken = set(project.get('record', 'inputnode', step=step, index=index) or [])
        all_possible_inputs = set(node_dependencies.get((step, index), []))
        all_edges = all_possible_inputs.union(path_taken)

        for source_step, source_index in all_edges:
            # Determine edge style based on whether it was part of the
            # actual execution path and the critical path.
            edge_width = default_edge_width
            if (step, index) in successful_path and (source_step, source_index) in successful_path:
                edge_width = successful_path_edge_width

            dashes = False
            color = 'black'
            if (source_step, source_index) not in path_taken:
                # Potential but unused dependency
                color = 'gray'
                dashes = True
            elif node_status != NodeStatus.SUCCESS:
                # Executed path, but not part of a successful flow
                color = 'gray'
            elif NodeStatus.is_waiting(node_status) or NodeStatus.is_running(node_status):
                # Path leading to a currently active node
                color = 'blue'
                dashes = True

            edges.append(Edge(
                source=f'{source_step}/{source_index}',
                target=node_name,
                dir='up',
                width=edge_width,
                color=color,
                dashes=dashes))

    return nodes, edges


def get_graph_config():
    """
    Returns a `streamlit_agraph.Config` object with predefined settings
    for a hierarchical, top-down flowgraph layout.

    Returns:
        Config: The configuration object for the agraph component.
    """
    return Config(
        width='100%',
        height=1000,
        directed=True,
        physics=False,
        hierarchical=True,
        # Hierarchical layout settings
        nodeSpacing=150,
        levelSeparation=100,
        sortMethod='directed')
