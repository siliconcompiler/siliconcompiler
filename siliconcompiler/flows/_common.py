def setup_frontend(chip):
    ''' Return list of frontend steps to be prepended to flowgraph as list of
    (step, tool) tuples. '''

    frontend = chip.get('option', 'frontend')
    frontend_flow = []

    if frontend in ('verilog', 'systemverilog'):
        frontend_flow.append(('import', 'surelog', 'parse'))
    elif frontend == 'chisel':
        frontend_flow.append(('import', 'chisel', 'convert'))
    elif frontend == 'c':
        frontend_flow.append(('import', 'bambu', 'convert'))
    elif frontend == 'bluespec':
        frontend_flow.append(('import', 'bluespec', 'convert'))
    elif frontend == 'vhdl':
        frontend_flow.append(('import', 'ghdl', 'convert'))
    else:
        raise ValueError(f'Unsupported frontend: {frontend}')

    if frontend == 'systemverilog':
        frontend_flow.append(('convert', 'sv2v', 'convert'))

    return frontend_flow
