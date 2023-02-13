import os
import subprocess

from siliconcompiler.tools.verilator.verilator import setup as setup_tool

def setup(chip):
    ''' Helper method to load configs specific to compile tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'import'
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option',  ['--lint-only', '--debug'], step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', ",".join(['input', 'rtl', 'verilog']), step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.v', step=step, index=index)
    for value in chip.get('option', 'define'):
        chip.add('tool', tool, 'task', task, 'option', '-D' + value, step=step, index=index)

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    design = chip.top()
    step = chip.get('arg','step')

    # Post-process hack to collect vpp files
    # Creating single file "pickle' synthesis handoff
    subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                   shell=True)

    # Moving pickled file to outputs
    os.rename("verilator.v", f"outputs/{design}.v")
