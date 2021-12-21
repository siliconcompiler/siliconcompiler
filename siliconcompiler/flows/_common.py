def setup_frontend(chip):
    ''' Return list of frontend steps to be prepended to flowgraph as list of
    (step, tool) tuples. '''

    frontend = chip.get('frontend')
    frontend_flow = []

    if frontend in ('verilog', 'systemverilog'):
        frontend_flow.append(('import', 'surelog'))
    elif frontend == 'chisel':
        frontend_flow.append(('import', 'chisel'))
    elif frontend == 'c':
        frontend_flow.append(('import', 'bambu'))
    elif frontend == 'bluespec':
        frontend_flow.append(('import', 'bluespec'))
    else:
        raise ValueError(f'Unsupported frontend: {frontend}')

    if frontend == 'systemverilog':
        frontend_flow.append(('convert', 'sv2v'))

    return frontend_flow
