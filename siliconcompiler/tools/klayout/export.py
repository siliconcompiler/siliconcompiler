
from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.screenshot import setup_gui_screenshot
from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.tools._common.asic import get_libraries


def setup(chip):
    '''
    Generate a GDSII file from an input DEF file
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    clobber = False

    script = 'klayout_export.py'
    option = ['-z', '-nc', '-rx', '-r']
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)

    targetlibs = get_libraries(chip, 'logic')
    stackup = chip.get('option', 'stackup')
    pdk = chip.get('option', 'pdk')

    # Set stream extension
    streams = ('gds', 'oas')
    chip.set('tool', tool, 'task', task, 'var', 'stream', 'gds',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'stream',
             f'Extension to use for stream generation ({streams})',
             field='help')
    default_stream = chip.get('tool', tool, 'task', task, 'var', 'stream',
                              step=step, index=index)[0]
    sc_stream_order = [default_stream, *[s for s in streams if s != default_stream]]

    if stackup and targetlibs:
        macrolibs = get_libraries(chip, 'macro')

        chip.add('tool', tool, 'task', task, 'require', ",".join(['asic', 'logiclib']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require', ",".join(['option', 'stackup']),
                 step=step, index=index)
        req_set = False
        for s in sc_stream_order:
            if chip.valid('pdk', pdk, 'layermap', 'klayout', 'def', s, stackup):
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', s, stackup]),
                         step=step, index=index)
                req_set = True
                break
        if not req_set:
            # add default require
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['pdk', pdk, 'layermap', 'klayout', 'def', 'klayout', stackup]),
                     step=step, index=index)

        for lib in (targetlibs + macrolibs):
            lib_requires_stream = True
            if chip.valid('library', lib, 'option', 'var', 'klayout_allow_missing_cell') and \
               chip.get('library', lib, 'option', 'var', 'klayout_allow_missing_cell'):
                lib_requires_stream = False
            req_set = False
            for s in sc_stream_order:
                if chip.valid('library', lib, 'output', stackup, s):
                    chip.add('tool', tool, 'task', task, 'require',
                             ",".join(['library', lib, 'output', stackup, s]),
                             step=step, index=index)
                    req_set = True
                    break
            if not req_set and lib_requires_stream:
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(['library', lib, 'output', stackup, default_stream]),
                         step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', stackup, 'lef']),
                     step=step, index=index)
    else:
        chip.error('Stackup and targetlib parameters required for Klayout.')

    # Input/Output requirements for default flow
    design = chip.top()
    if design + '.def' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.def',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,layout,def',
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', f'{design}.{default_stream}',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.lyt',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.lyp',
             step=step, index=index)

    # Export GDS with timestamps by default.
    chip.set('tool', tool, 'task', task, 'var', 'timestamps', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'timestamps',
             'Export GDSII with timestamps',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'screenshot', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'screenshot',
             'true/false: true will cause KLayout to generate a screenshot of the layout',
             field='help')

    if chip.get('tool', tool, 'task', task, 'var', 'screenshot',
                step=step, index=index) == ['true']:
        setup_gui_screenshot(chip, require_input=False)
