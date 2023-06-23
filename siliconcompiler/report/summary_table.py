import pandas

from siliconcompiler.report.utils import _collect_data
from siliconcompiler import TaskStatus


def _show_summary_table(chip, flow, steplist, show_all_indices):
    '''
    Prints the end of run summary table
    '''

    # Display data
    pandas.set_option('display.max_rows', 500)
    pandas.set_option('display.max_columns', 500)
    pandas.set_option('display.width', 100)

    nodes, errors, metrics, metrics_unit, metrics_to_show, reports = \
        _collect_data(chip, flow, steplist)

    # Find all tasks that are part of a "winning" path.
    selected_tasks = set()
    to_search = []

    # Start search with any successful leaf tasks.
    leaf_tasks = chip._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for task in leaf_tasks:
        if chip.get('flowgraph', flow, *task, 'status') == TaskStatus.SUCCESS:
            selected_tasks.add(task)
            to_search.append(task)

    # Search backwards, saving anything that was selected by leaf tasks.
    while len(to_search) > 0:
        task = to_search.pop(-1)
        for selected in chip.get('flowgraph', flow, *task, 'select'):
            if selected not in selected_tasks:
                selected_tasks.add(selected)
                to_search.append(selected)

    # only report tool based steps functions
    for step in steplist.copy():
        tool, task = chip._get_tool_task(step, '0', flow=flow)
        if chip._is_builtin(tool, task):
            index = steplist.index(step)
            del steplist[index]

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

    colwidth = 8  # minimum col width
    row_labels = [' ' + metric for metric in metrics_to_show]
    column_labels = [f'{step}{index}'.center(colwidth) for step, index in nodes_to_show]
    column_labels.insert(0, 'units')

    data = []
    for metric in metrics_to_show:
        row = []
        row.append(metrics_unit[metric])
        for node in nodes_to_show:
            value = metrics[node][metric]
            if value is None:
                value = '---'
            value = ' ' + value.center(colwidth)
            row.append(value)
        data.append(row)

    info_list = ["SUMMARY:\n",
                 "design : " + chip.design,
                 "params : " + paramstr,
                 "jobdir : " + chip._getworkdir()]

    if chip.get('option', 'mode') == 'asic':
        pdk = chip.get('option', 'pdk')

        libraries = set()
        for val, step, _ in chip.schema._getvals('asic', 'logiclib'):
            if not step or step in steplist:
                libraries.update(val)

        info_list.extend([f"foundry : {chip.get('pdk', pdk, 'foundry')}",
                          f"process : {pdk}",
                          f"targetlibs : {' '.join(libraries)}"])
    elif chip.get('option', 'mode') == 'fpga':
        info_list.extend([f"partname : {chip.get('fpga','partname')}"])

    info = '\n'.join(info_list)

    print("-" * 135)
    print(info, "\n")

    df = pandas.DataFrame(data, row_labels, column_labels)
    if not df.empty:
        print(df.to_string())
    else:
        print(' No metrics to display!')
    print("-" * 135)
