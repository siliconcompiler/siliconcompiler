import shutil
import os

from siliconcompiler.tools.openroad import openroad
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process
from siliconcompiler.tools._common import find_incoming_ext, input_provides, get_tool_task


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    openroad.make_docs(chip)
    chip.set('tool', 'openroad', 'task', 'show', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Show a design in openroad
    '''

    # Generic tool setup.
    setup_tool(chip)

    generic_show_setup(chip, 'show', False)


def generic_show_setup(chip, task, exit):
    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    option = "-no_init -gui"

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', "true" if exit else "false",
             step=step, index=index, clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']),
                 step=step, index=index)
    else:
        incoming_ext = find_incoming_ext(chip, ('odb', 'def'), 'def')
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext,
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{incoming_ext}',
                 step=step, index=index)
        if f'{design}.sdc' in input_provides(chip, step, index):
            chip.add('tool', tool, 'task', task, 'input', f'{design}.sdc',
                     step=step, index=index)

    # Add to option string.
    cur_options = ' '.join(chip.get('tool', tool, 'task', task, 'option', step=step, index=index))
    new_options = f'{cur_options} {option}'
    chip.set('tool', tool, 'task', task, 'option', new_options,
             step=step, index=index, clobber=True)


def pre_process(chip):
    or_pre_process(chip)
    copy_show_files(chip)
    build_pex_corners(chip)


def copy_show_files(chip):

    tool = 'openroad'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        show_file = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                             step=step, index=index)[0]
        show_type = chip.get('tool', tool, 'task', task, 'var', 'show_filetype',
                             step=step, index=index)[0]
        show_job = chip.get('tool', tool, 'task', task, 'var', 'show_job',
                            step=step, index=index)
        show_step = chip.get('tool', tool, 'task', task, 'var', 'show_step',
                             step=step, index=index)
        show_index = chip.get('tool', tool, 'task', task, 'var', 'show_index',
                              step=step, index=index)

        # copy source in to keep sc_apr.tcl simple
        dst_file = f"inputs/{chip.top()}.{show_type}"
        shutil.copy2(show_file, dst_file)
        if show_job and show_step and show_index:
            sdc_file = chip.find_result('sdc', show_step[0],
                                        jobname=show_job[0],
                                        index=show_index[0])
            if sdc_file and os.path.exists(sdc_file):
                shutil.copy2(sdc_file, f"inputs/{chip.top()}.sdc")
