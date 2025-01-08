import os
import shutil

from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.klayout import runtime_options as runtime_options_tool
from siliconcompiler.tools._common import find_incoming_ext, get_tool_task


def make_docs(chip):
    from siliconcompiler.tools.klayout import klayout
    klayout.make_docs(chip)
    chip.set('tool', 'klayout', 'task', 'show', 'var', 'show_filepath', '<path>')


def general_gui_setup(chip, task, exit, require_input=True):
    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    clobber = False

    script = 'klayout_show.py'
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=clobber)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    if chip.valid('pdk', pdk, 'var', 'klayout', 'hide_layers', stackup):
        layers_to_hide = chip.get('pdk', pdk, 'var', 'klayout', 'hide_layers', stackup)
        chip.add('tool', tool, 'task', task, 'var', 'hide_layers', layers_to_hide,
                 step=step, index=index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath') and \
       chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']),
                 step=step, index=index)
    elif require_input:
        incoming_ext = find_incoming_ext(chip, ('gds', 'oas', 'def'), 'def')
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'show_filetype']),
                 step=step, index=index)
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext,
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{chip.top()}.{incoming_ext}',
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', "true" if exit else "false",
             step=step, index=index, clobber=False)

    # Help
    chip.set('tool', tool, 'task', task, 'var', 'hide_layers',
             'List of layers to hide',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'show_filepath',
             'File to open',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'show_filetype',
             'File type to look for in the inputs',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'show_exit',
             'true/false: true will cause kLayout to exit when complete',
             field='help')


def setup(chip):
    '''
    Show a layout in kLayout
    '''

    # Generic tool setup.
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    clobber = False

    chip.set('tool', tool, 'task', task, 'threads', 1, step=step, index=index, clobber=clobber)

    general_gui_setup(chip, task, False)

    option = ['-nc', '-rm']
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath') and \
       chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        show_file = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                             step=step, index=index)[0]

        rel_path = os.path.dirname(show_file)
        for ext in ('lyt', 'lyp'):
            ext_file = os.path.join(rel_path, f'{chip.top()}.{ext}')
            if ext_file and os.path.exists(ext_file):
                shutil.copy2(ext_file, f"inputs/{chip.top()}.{ext}")


def runtime_options(chip):
    return runtime_options_tool(chip) + [
        '-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'
    ]
