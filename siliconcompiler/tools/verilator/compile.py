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

    # var defaults
    chip.set('tool', tool, 'task', task, 'var', 'mode', 'cc', clobber=False, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'trace_type', 'vcd', clobber=False,
             step=step, index=index)

    mode = chip.get('tool', tool, 'task', task, 'var', 'mode', step=step, index=index)
    if mode not in (['cc'], ['systemc']):
        chip.error(f"Invalid mode {mode} provided to verilator/compile. Expected one of 'cc' or "
                   "'systemc'")

    trace_type = chip.get('tool', tool, 'task', task, 'var', 'trace_type', step=step, index=index)
    if trace_type not in (['vcd'], ['fst']):
        chip.error(f"Invalid trace type {trace_type} provided to verilator/compile. Expected "
                   "one of 'vcd' or 'fst'.")

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

    chip.set('tool', tool, 'task', task, 'var', 'pins_bv',
             'controls datatypes used to represent SystemC inputs/outputs. See --pins-bv in '
             'Verilator docs for more info.',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'mode',
             "defines compilation mode for Verilator. Valid options are 'cc' for C++, or 'systemc' "
             "for SystemC.",
             field='help')

    chip.set('tool', tool, 'task', task, 'dir', 'cincludes',
             'include directories to provide to the C++ compiler invoked by Verilator',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'trace_type',
             "specifies type of wave file to create when [option, trace] is set. Valid options are "
             "'vcd' or 'fst'. Defaults to 'vcd'.",
             field='help')


def runtime_options(chip):
    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    cmdlist = runtime_options_tool(chip)

    cmdlist.extend(['--exe', '--build'])

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    cmdlist.extend(['-j', str(threads)])

    mode = chip.get('tool', tool, 'task', task, 'var', 'mode', step=step, index=index)
    if mode == ['cc']:
        cmdlist.append('--cc')
    elif mode == ['systemc']:
        cmdlist.append('--sc')

    pins_bv = chip.get('tool', tool, 'task', task, 'var', 'pins_bv', step=step, index=index)
    if pins_bv:
        cmdlist.extend(['--pins-bv', pins_bv[0]])

    cmdlist.extend(['-o', f'../outputs/{design}.vexe'])

    if chip.get('option', 'trace', step=step, index=index):
        trace_type = chip.get('tool', tool, 'task', task, 'var', 'trace_type',
                              step=step, index=index)

        if trace_type == ['vcd']:
            trace_opt = '--trace'
        elif trace_type == ['fst']:
            trace_opt = '--trace-fst'

        cmdlist.append(trace_opt)

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
