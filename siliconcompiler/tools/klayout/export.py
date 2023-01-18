def setup(chip):
    ''' Helper method for configs specific to export tasks.
    '''

    tool = 'klayout'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'export'
    clobber = False

    script = 'klayout_export.py'
    option = ['-b', '-r']
    chip.set('tool', tool, 'task', task, 'script', step, index, script, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', step, index, option, clobber=clobber)

    targetlibs = chip.get('asic', 'logiclib')
    stackup = chip.get('asic', 'stackup')
    pdk = chip.get('option', 'pdk')
    if bool(stackup) & bool(targetlibs):
        macrolibs = chip.get('asic', 'macrolib')

        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['asic', 'stackup']))
        chip.add('tool', tool, 'task', task, 'require', step, index,  ",".join(['pdk', pdk, 'layermap', 'klayout', 'def','gds', stackup]))

        for lib in (targetlibs + macrolibs):
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'gds']))
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
    else:
        chip.error(f'Stackup and targetlib paremeters required for Klayout.')

    # Input/Output requirements for default flow
    design = chip.top()
    if step in ['export']:
        if (not chip.valid('input', 'layout', 'def') or
            not chip.get('input', 'layout', 'def')):
            chip.add('tool', tool, 'task', task, 'input', step, index, design + '.def')
        chip.add('tool', tool, 'task', task, 'output', step, index, design + '.gds')
