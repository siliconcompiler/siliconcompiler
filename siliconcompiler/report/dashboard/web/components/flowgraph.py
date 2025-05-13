from siliconcompiler.report import report
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler import NodeStatus

from streamlit_agraph import Node, Edge, Config


# for flowgraph
NODE_COLORS = {
    NodeStatus.SUCCESS: '#70db70',  # green

    NodeStatus.SKIPPED: '#ffc299',  # orange

    NodeStatus.PENDING: '#6699ff',  # blue
    NodeStatus.QUEUED: '#6699ff',  # blue

    NodeStatus.RUNNING: '#ffff4d',  # yellow

    NodeStatus.ERROR: '#ff1a1a',  # red
    NodeStatus.TIMEOUT: '#ff1a1a',  # red

    "Unknown": '#6699ff',  # blue
}


def get_nodes_and_edges(chip):
    """
    Returns the nodes and edges required to make a streamlit_agraph.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
    """
    nodes = []
    edges = []

    if not chip.get('option', 'flow'):
        return nodes, edges

    default_node_border_width = 1
    successful_path_node_width = 3
    default_edge_width = 3
    successful_path_edge_width = 5

    node_dependencies = report.get_flowgraph_edges(chip)
    successful_path = report.get_flowgraph_path(chip)

    flow = chip.get('option', 'flow')
    entry_exit_nodes = chip.schema.get("flowgraph", flow, field="schema").get_entry_nodes() + \
        chip.schema.get("flowgraph", flow, field="schema").get_exit_nodes()

    for step, index in node_dependencies:
        # Build node
        node_border_width = default_node_border_width
        if (step, index) in entry_exit_nodes:
            node_border_width = successful_path_node_width

        node_status = chip.get('record', 'status', step=step, index=index)
        if node_status not in NODE_COLORS:
            node_status = "Unknown"
        node_color = NODE_COLORS[node_status]

        tool, task = get_tool_task(chip, step, index)
        node_name = f'{step}{index}'
        label = node_name + "\n" + tool + "/" + task
        if tool == 'builtin':
            label = node_name + "\n" + tool

        nodes.append(Node(
            id=node_name,
            label=label,
            color=node_color,
            opacity=1,
            borderWidth=node_border_width,
            shape='oval',
            fixed=True))

        # Build edges
        path_taken = chip.get('record', 'inputnode', step=step, index=index)
        all_edges = set([*node_dependencies[step, index], *path_taken])
        for source_step, source_index in all_edges:
            edge_width = default_edge_width
            if (step, index) in successful_path and \
               (source_step, source_index) in successful_path:
                edge_width = successful_path_edge_width

            dashes = False
            color = 'black'
            if (source_step, source_index) not in path_taken:
                color = 'gray'
                dashes = True
            elif node_status != NodeStatus.SUCCESS:
                color = 'gray'
            elif NodeStatus.is_waiting(node_status) or NodeStatus.is_running(node_status):
                color = 'blue'
                dashes = True

            edges.append(Edge(
                source=f'{source_step}{source_index}',
                target=node_name,
                dir='up',
                width=edge_width,
                color=color,
                dashes=dashes))

    return nodes, edges


def get_graph_config():
    return Config(
        width='100%',
        height=1000,
        directed=True,
        physics=False,
        hierarchical=True,
        nodeSpacing=150,
        levelSeparation=100,
        sortMethod='directed')
