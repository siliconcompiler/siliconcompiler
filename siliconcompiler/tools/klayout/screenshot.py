
from .klayout import setup as setup_tool

def setup(chip):
    ''' Helper method for configs specific to screenshot tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()
    task = 'screenshot'
    clobber = False

    script = 'klayout_show.py'
    option = ['-nc', '-z', '-rm']
    chip.set('tool', tool, 'task', task, 'script', step, index, script, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', step, index, option, clobber=clobber)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    if chip.valid('pdk', pdk, 'var', 'klayout', 'hide_layers', stackup):
        layers_to_hide = chip.get('pdk', pdk, 'var', 'klayout', 'hide_layers', stackup)
        chip.add('tool', tool, 'task', task, 'var', step, index, 'hide_layers', layers_to_hide)
    if chip.valid('tool', tool, 'task', task, 'var', step, index, 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, 'show_filepath']))
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, 'show_filetype']))
        chip.set('tool', tool, 'task', task, 'var', step, index, 'show_filetype', incoming_ext)
        chip.add('tool', tool, 'task', task, 'input', step, index, f'{design}.{incoming_ext}')
    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_exit', "true", clobber=False)

    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.png')
    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_horizontal_resolution', '1024', clobber=False)
    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_vertical_resolution', '1024', clobber=False)
