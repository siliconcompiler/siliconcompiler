import os
import subprocess

from siliconcompiler.tools.verilator.verilator import setup as setup_tool


def setup(chip):
    '''
    Preprocesses and pickles Verilog sources. Takes in a set of Verilog source
    files supplied via :keypath:`input, verilog` and reads the following
    parameters:

    * :keypath:`option, ydir`
    * :keypath:`option, vlib`
    * :keypath:`option, idir`
    * :keypath:`option, cmdfile`

    Outputs a single Verilog file in ``outputs/<design>.v``.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option', ['--lint-only', '--debug'], step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', ",".join(['input', 'rtl', 'verilog']), step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.v', step=step, index=index)
    for value in chip.get('option', 'define'):
        chip.add('tool', tool, 'task', task, 'option', '-D' + value, step=step, index=index)


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    design = chip.top()

    # Post-process hack to collect vpp files
    # Creating single file "pickle' synthesis handoff
    subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                   shell=True)

    # Moving pickled file to outputs
    os.rename("verilator.v", f"outputs/{design}.v")
