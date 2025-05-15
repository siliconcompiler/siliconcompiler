from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.tools.xdm import setup as tool_setup
import os
import shutil


def setup(chip):
    tool_setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    if f'{design}.cir' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.cir',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,netlist,spice',
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', f'{design}.xyce', step=step, index=index)

    chip.add('tool', tool, 'task', task, 'option', '--auto',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', ['--source_file_format', 'hspice'],
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', ['--dir_out', f'outputs/{design}.xyce'],
             step=step, index=index)

    chip.set('tool', 'xdm', 'task', 'convert', 'var', 'rename', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', 'xdm', 'task', 'convert', 'var', 'rename',
             'true/false: indicate whether to rename the output file to match the '
             'naming scheme for siliconcompiler', field='help')


def runtime_options(chip):
    return __get_input_file(chip)


def __get_input_file(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.top()

    if f'{design}.cir' in input_provides(chip, step, index):
        return [f'inputs/{design}.cir']

    return chip.find_files('input', 'netlist', 'spice',
                           step=step, index=index)


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if chip.get('tool', 'xdm', 'task', 'convert', 'var', 'rename',
                step=step, index=index) == ['false']:
        return

    inputfile = __get_input_file(chip)[0]

    outdir = f'outputs/{chip.top()}.xyce'

    inputfile_base = os.path.basename(inputfile)
    outputfile_base = f'{chip.top()}.cir'

    if inputfile_base != outputfile_base:
        shutil.move(os.path.join(outdir, inputfile_base), os.path.join(outdir, outputfile_base))
