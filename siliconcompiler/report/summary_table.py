import shutil

from siliconcompiler.report.utils import _collect_data, _get_flowgraph_path
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.utils import truncate_text


def _show_summary_table(chip, flow, flowgraph_nodes, show_all_indices):
    '''
    Prints the end of run summary table
    '''
    from pandas import DataFrame

    # Display data
    column_width = 15

    max_line_width = max(4 * column_width, int(0.95*shutil.get_terminal_size().columns))

    nodes, _, metrics, metrics_unit, metrics_to_show, _ = \
        _collect_data(chip, flow, flowgraph_nodes)

    selected_tasks = \
        _get_flowgraph_path(chip, flow, flowgraph_nodes, only_include_successful=True)

    # only report tool based steps functions
    for (step, index) in list(flowgraph_nodes):
        if get_tool_task(chip, step, index, flow=flow)[0] == 'builtin':
            del flowgraph_nodes[flowgraph_nodes.index((step, index))]

    if show_all_indices:
        nodes_to_show = nodes
    else:
        nodes_to_show = [n for n in nodes if n in selected_tasks]

    # Custom reporting modes
    paramlist = []
    for item in chip.getkeys('option', 'param'):
        paramlist.append(item + "=" + chip.get('option', 'param', item))

    if paramlist:
        paramstr = ', '.join(paramlist)
    else:
        paramstr = "None"

    # trim labels to column width
    column_labels = []
    labels = [f'{step}{index}' for step, index in nodes_to_show]
    if labels:
        column_width = min([column_width, max([len(label) for label in labels])])

    for label in labels:
        column_labels.append(truncate_text(label, column_width).center(column_width))

    row_labels = []
    if metrics_to_show:
        row_label_len = max([len(metric) for metric in metrics_to_show])
        row_unit_len = max([len(metrics_unit[metric]) for metric in metrics_to_show])
        for metric in metrics_to_show:
            row_labels.append(f'{metric:<{row_label_len}}  {metrics_unit[metric]:>{row_unit_len}}')

    data = []
    for metric in metrics_to_show:
        row = []
        for node in nodes_to_show:
            value = metrics[node][metric]
            if value is None:
                value = '---'
            value = ' ' + value.center(column_width)
            row.append(value)
        data.append(row)

    info_list = ["SUMMARY:\n",
                 "design : " + chip.design,
                 "params : " + paramstr,
                 "jobdir : " + chip.getworkdir()]

    pdk = chip.get('option', 'pdk')
    if pdk:
        info_list.extend([
            f"foundry : {chip.get('pdk', pdk, 'foundry')}",
            f"process : {pdk}"])
    else:
        fpga_partname = chip.get('fpga', 'partname')
        if fpga_partname:
            info_list.append(f"partname : {fpga_partname}")

    libraries = set()
    for val, step, index in chip.schema.get('asic', 'logiclib', field=None).getvalues():
        if not step or (step, index) in flowgraph_nodes:
            libraries.update(val)
    if libraries:
        info_list.append(f"targetlibs : {' '.join(libraries)}")

    info = '\n'.join(info_list)

    print("-" * max_line_width)
    print(info, "\n")

    df = DataFrame(data, row_labels, column_labels)
    if not df.empty:
        print(df.to_string(line_width=max_line_width, col_space=2))
    else:
        print(' No metrics to display!')
    print("-" * max_line_width)
