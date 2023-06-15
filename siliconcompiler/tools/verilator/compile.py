import subprocess

from siliconcompiler.tools.verilator.verilator import setup as setup_tool
from siliconcompiler.tools.verilator.verilator import runtime_options as runtime_options_tool


def setup(chip):
    '''
    Compiles Verilog and C/C++ sources into an executable. In addition to the
    standard RTL inputs, this task reads C/C++ sources from :keypath:`input,
    hll, c`.  Outputs an executable in ``outputs/<design>.vexe``.

    This task supports using the :keypath:`option, trace` parameter to enable
    Verilator's ``--trace`` flag.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option', ['--cc', '--exe'],
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', f'-o ../outputs/{design}.vexe',
             step=step, index=index)

    if chip.valid('input', 'hll', 'c'):
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['input', 'hll', 'c']),
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'cflags',
             'flags to provide to the C++ compiler invoked by Verilator',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'ldflags',
             'flags to provide to the linker invoked by Verilator',
             field='help')

    chip.set('tool', tool, 'task', task, 'dir', 'cincludes',
             'include directories to provide to the C++ compiler invoked by Verilator',
             field='help')


def runtime_options(chip):
    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    cmdlist = runtime_options_tool(chip)

    c_flags = chip.get('tool', tool, 'task', task, 'var', 'cflags', step=step, index=index)
    c_includes = chip.find_files('tool', tool, 'task', task, 'dir', 'cincludes',
                                 step=step, index=index)

    if c_includes:
        c_flags.extend([f'-I{include}' for include in c_includes])

    if c_flags:
        cflags_str = ' '.join(c_flags)
        cmdlist.extend(['-CFLAGS', f'"{cflags_str}"'])

    ld_flags = chip.get('tool', tool, 'task', task, 'var', 'ldflags', step=step, index=index)
    if ld_flags:
        ldflags_str = ' '.join(ld_flags)
        cmdlist.extend(['-LDFLAGS', f'"{ldflags_str}"'])

    for value in chip.find_files('input', 'hll', 'c', step=step, index=index):
        cmdlist.append(value)

    return cmdlist


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
