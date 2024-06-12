from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.chisel import convert as chisel_convert
from siliconcompiler.tools.bambu import convert as bambu_convert
from siliconcompiler.tools.bluespec import convert as bluespec_convert
from siliconcompiler.tools.ghdl import convert as ghdl_convert
from siliconcompiler.tools.sv2v import convert as sv2v_convert

from siliconcompiler.tools.builtin import concatenate


def _make_docs(chip):
    chip.set('input', 'rtl', 'vhdl', 'test')
    chip.set('input', 'rtl', 'verilog', 'test')
    chip.set('input', 'hll', 'c', 'test')
    chip.set('input', 'hll', 'bsv', 'test')
    chip.set('input', 'hll', 'scala', 'test')


def __get_frontends(allow_system_verilog):
    systemverilog_frontend = [
        ('import', surelog_parse)
    ]
    if not allow_system_verilog:
        systemverilog_frontend.append(('convert', sv2v_convert))

    return {
        "verilog": [('import', surelog_parse)],
        "systemverilog": systemverilog_frontend,
        "chisel": [('import', chisel_convert)],
        "c": [('import', bambu_convert)],
        "bluespec": [('import', bluespec_convert)],
        "vhdl": [('import', ghdl_convert)]
    }


def setup_multiple_frontends(chip, flow, allow_system_verilog=False):
    '''
    Sets of multiple frontends if different frontends are required.

    Returns name of final step from the setup.
    '''

    def check_key(*key):
        if not chip.valid(*key):
            return False

        if any([values for values, _, _ in chip.schema._getvals(*key)]):
            return True

        return False

    selected_frontends = []
    # Select frontend sets
    if check_key('input', 'rtl', 'vhdl'):
        selected_frontends.append("vhdl")

    if check_key('input', 'hll', 'c'):
        selected_frontends.append("c")
    if check_key('input', 'hll', 'bsv'):
        selected_frontends.append("bluespec")
    if check_key('input', 'hll', 'scala'):
        selected_frontends.append("chisel")
    if check_key('input', 'config', 'chisel'):
        selected_frontends.append("chisel")

    if check_key('input', 'rtl', 'verilog'):
        frontend = "verilog"

        if not allow_system_verilog:
            # Search files to check for system verilog
            files = []
            for values, _, _ in chip.schema._getvals('input', 'rtl', 'verilog'):
                files.extend(values)

            for f in files:
                if f.endswith('.sv') or f.endswith('.sv.gz'):
                    frontend = "systemverilog"

        selected_frontends.append(frontend)

    concat_nodes = []
    flowname = flow.design
    for frontend, pipe in __get_frontends(allow_system_verilog).items():
        if frontend not in selected_frontends:
            continue

        prev_step = None
        for step, task in pipe:
            if len(selected_frontends) > 1:
                step_name = f'{step}_{frontend}'
            else:
                step_name = step

            flow.node(flowname, step_name, task)
            if prev_step:
                flow.edge(flowname, prev_step, step_name)

            prev_step = step_name

        if prev_step:
            concat_nodes.append(prev_step)

    if len(concat_nodes) > 1:
        final_node = 'combine'
        flow.node(flowname, final_node, concatenate)
        for node in concat_nodes:
            flow.edge(flowname, node, final_node)
    elif len(concat_nodes) == 1:
        final_node = concat_nodes[0]
    else:
        chip.logger.debug('Unable to determine automatically frontend')
        final_node = None
        for step, task in setup_frontend(chip, allow_system_verilog=allow_system_verilog):
            flow.node(flowname, step, task)
            if final_node:
                flow.edge(flowname, final_node, step)
            final_node = step

    return final_node


def setup_frontend(chip, allow_system_verilog=False):
    '''
    Return list of frontend steps to be prepended to flowgraph as list of
    (step, task) tuples.
    '''

    frontends = __get_frontends(allow_system_verilog)
    frontend = chip.get('option', 'frontend')
    if frontend not in frontends:
        raise ValueError(f'Unsupported frontend: {frontend}')

    return frontends[frontend]
