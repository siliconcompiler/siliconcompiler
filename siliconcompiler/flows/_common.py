from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.chisel import convert as chisel_convert
from siliconcompiler.tools.bambu import convert as bambu_convert
from siliconcompiler.tools.bluespec import convert as bluespec_convert
from siliconcompiler.tools.ghdl import convert as ghdl_convert
from siliconcompiler.tools.sv2v import convert as sv2v_convert

from siliconcompiler.tools.builtin import concatenate


def _make_docs(chip):
    from siliconcompiler.targets import freepdk45_demo
    chip.set('input', 'rtl', 'vhdl', 'test')
    chip.set('input', 'rtl', 'verilog', 'test')
    chip.set('input', 'rtl', 'systemverilog', 'test')
    chip.set('input', 'hll', 'c', 'test')
    chip.set('input', 'hll', 'bsv', 'test')
    chip.set('input', 'hll', 'scala', 'test')

    chip.load_target(freepdk45_demo)


def __get_frontends(allow_system_verilog):
    systemverilog_frontend = [
        ('import', surelog_parse)
    ]
    if not allow_system_verilog:
        systemverilog_frontend.append(('convert', sv2v_convert))

    return {
        "verilog": systemverilog_frontend,
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

    concat_nodes = []
    flowname = flow.design
    for frontend, pipe in __get_frontends(allow_system_verilog).items():
        prev_step = None
        for step, task in pipe:
            step_name = f'{step}_{frontend}'

            flow.node(flowname, step_name, task)
            if prev_step:
                flow.edge(flowname, prev_step, step_name)

            prev_step = step_name

        if prev_step:
            concat_nodes.append(prev_step)

    final_node = 'combine'
    flow.node(flowname, final_node, concatenate)
    for node in concat_nodes:
        flow.edge(flowname, node, final_node)

    return final_node
