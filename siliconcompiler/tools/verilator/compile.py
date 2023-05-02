import subprocess

from siliconcompiler.tools.verilator.verilator import setup as setup_tool


def setup(chip):
    '''
    Compiles Verilog and C/C++ sources into an executable.  Takes in a single
    pickled Verilog file from ``inputs/<design>.v`` and a set of C/C++ sources
    from :keypath:`input, c`. Outputs an executable in
    ``outputs/<design>.vexe``.

    This step supports using the :keypath:`option, trace` parameter to enable
    Verilator's ``--trace`` flag.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option', ['--cc', '--exe'], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'input', f'{design}.v', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', f'-o ../outputs/{design}.vexe', step=step, index=index)


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    design = chip.top()

    # Run make to compile Verilated design into executable.
    # If we upgrade our minimum supported Verilog, we can remove this and
    # use the --build flag instead.
    proc = subprocess.run(['make', '-C', 'obj_dir', '-f', f'V{design}.mk'])
    if proc.returncode > 0:
        chip.error(
            f'Make returned error code {proc.returncode} when compiling '
            'Verilated design', fatal=True
        )
