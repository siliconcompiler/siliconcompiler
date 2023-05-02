from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.chisel import convert as chisel_convert
from siliconcompiler.tools.bambu import convert as bambu_convert
from siliconcompiler.tools.bluespec import convert as bluespec_convert
from siliconcompiler.tools.ghdl import convert as ghdl_convert
from siliconcompiler.tools.sv2v import convert as sv2v_convert


def setup_frontend(chip):
    '''
    Return list of frontend steps to be prepended to flowgraph as list of
    (step, task) tuples.
    '''

    frontend = chip.get('option', 'frontend')
    frontend_flow = []

    if frontend in ('verilog', 'systemverilog'):
        frontend_flow.append(('import', surelog_parse))
    elif frontend == 'chisel':
        frontend_flow.append(('import', chisel_convert))
    elif frontend == 'c':
        frontend_flow.append(('import', bambu_convert))
    elif frontend == 'bluespec':
        frontend_flow.append(('import', bluespec_convert))
    elif frontend == 'vhdl':
        frontend_flow.append(('import', ghdl_convert))
    else:
        raise ValueError(f'Unsupported frontend: {frontend}')

    if frontend == 'systemverilog':
        frontend_flow.append(('convert', sv2v_convert))

    return frontend_flow
