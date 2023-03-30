import importlib
from siliconcompiler.tools.sv2v import convert as sv2v_convert

def setup_frontend(chip):
    '''
    Return list of frontend steps to be prepended to flowgraph as list of
    (step, task) tuples.
    '''

    frontend = chip.get('option', 'frontend')
    frontend_flow = []

    if frontend in ('verilog', 'systemverilog'):
        frontend_flow.append(('import', importlib.import_module('siliconcompiler.tools.surelog.import')))
    elif frontend == 'chisel':
        frontend_flow.append(('import', importlib.import_module('siliconcompiler.tools.chisel.import')))
    elif frontend == 'c':
        frontend_flow.append(('import', importlib.import_module('siliconcompiler.tools.bambu.import')))
    elif frontend == 'bluespec':
        frontend_flow.append(('import', importlib.import_module('siliconcompiler.tools.bluespec.import')))
    elif frontend == 'vhdl':
        frontend_flow.append(('import', importlib.import_module('siliconcompiler.tools.ghdl.import')))
    else:
        raise ValueError(f'Unsupported frontend: {frontend}')

    if frontend == 'systemverilog':
        frontend_flow.append(('convert', sv2v_convert))

    return frontend_flow
