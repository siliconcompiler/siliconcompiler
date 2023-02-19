import siliconcompiler
import shutil
import os

from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners

def make_docs():
    chip = siliconcompiler.Chip('<design>')
    chip.load_target('freepdk45_demo')
    step = 'show'
    index = '<index>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('flowgraph', chip.get('option', 'flow'), step, index, 'task', 'show')
    chip.set('tool', 'openroad', 'task', 'show', 'var', 'show_filepath', '<path>')
    setup(chip)

    return chip

def setup(chip):
    ''' Helper method for configs specific to show tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'show'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    option = "-no_init -gui"

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', "false", step=step, index=index, clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']), step=step, index=index)
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext, step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{incoming_ext}', step=step, index=index)

    # Add to option string.
    cur_options = ' '.join(chip.get('tool', tool, 'task', task, 'option', step=step, index=index))
    new_options = f'{cur_options} {option}'
    chip.set('tool', tool, 'task', task, 'option', new_options, step=step, index=index, clobber=True)

def pre_process(chip):
    copy_show_files(chip)
    build_pex_corners(chip)

def copy_show_files(chip):

    tool = 'openroad'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        show_file = chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index)[0]
        show_type = chip.get('tool', tool, 'task', task, 'var', 'show_filetype', step=step, index=index)[0]
        show_job = chip.get('tool', tool, 'task', task, 'var', 'show_job', step=step, index=index)[0]
        show_step = chip.get('tool', tool, 'task', task, 'var', 'show_step', step=step, index=index)[0]
        show_index = chip.get('tool', tool, 'task', task, 'var', 'show_index', step=step, index=index)[0]

        # copy source in to keep sc_apr.tcl simple
        dst_file = "inputs/"+chip.top()+"."+show_type
        shutil.copy2(show_file, dst_file)
        sdc_file = chip.find_result('sdc', show_step, jobname=show_job, index=show_index)
        if sdc_file and os.path.exists(sdc_file):
            shutil.copy2(sdc_file, "inputs/"+chip.top()+".sdc")

def find_incoming_ext(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')

    supported_ext = ('odb', 'def')

    for input_step, input_index in chip.get('flowgraph', flow, step, index, 'input'):
        for ext in supported_ext:
            show_file = chip.find_result(ext, step=input_step, index=input_index)
            if show_file:
                return ext

    # Nothing found, just add last one
    return supported_ext[-1]
