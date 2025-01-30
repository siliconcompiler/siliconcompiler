from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.slang import elaborate as slang_preprocess
from siliconcompiler.tools.chisel import convert as chisel_convert
from siliconcompiler.tools.bambu import convert as bambu_convert
from siliconcompiler.tools.bluespec import convert as bluespec_convert
from siliconcompiler.tools.ghdl import convert as ghdl_convert
from siliconcompiler.tools.sv2v import convert as sv2v_convert

from siliconcompiler.tools.builtin import concatenate

from siliconcompiler.tools.slang import has_pyslang


def _make_docs(chip):
    from siliconcompiler.targets import freepdk45_demo
    chip.set('input', 'rtl', 'vhdl', 'test')
    chip.set('input', 'rtl', 'verilog', 'test')
    chip.set('input', 'rtl', 'systemverilog', 'test')
    chip.set('input', 'hll', 'c', 'test')
    chip.set('input', 'hll', 'bsv', 'test')
    chip.set('input', 'hll', 'scala', 'test')

    chip.use(freepdk45_demo)


def __get_frontends(allow_system_verilog, use_surelog=False):
    parser = surelog_parse
    if not use_surelog and has_pyslang():
        parser = slang_preprocess
    systemverilog_frontend = [
        ('import.verilog', parser)
    ]
    if not allow_system_verilog:
        systemverilog_frontend.append(('import.convert', sv2v_convert))

    return {
        "verilog": systemverilog_frontend,
        "chisel": [('import.chisel', chisel_convert)],
        "c": [('import.c', bambu_convert)],
        "bluespec": [('import.bluespec', bluespec_convert)],
        "vhdl": [('import.vhdl', ghdl_convert)]
    }


def setup_multiple_frontends(flow, allow_system_verilog=False, use_surelog=False):
    '''
    Sets of multiple frontends if different frontends are required.

    Returns name of final step from the setup.
    '''

    concat_nodes = []
    flowname = flow.design
    for _, pipe in __get_frontends(allow_system_verilog, use_surelog=use_surelog).items():
        prev_step = None
        for step, task in pipe:
            flow.node(flowname, step, task)
            if prev_step:
                flow.edge(flowname, prev_step, step)

            prev_step = step

        if prev_step:
            concat_nodes.append(prev_step)

    final_node = 'import.combine'
    flow.node(flowname, final_node, concatenate)
    for node in concat_nodes:
        flow.edge(flowname, node, final_node)

    return final_node
