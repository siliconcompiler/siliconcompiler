'''
GTKWave is a fully featured GTK+ based wave viewer for Unix, Win32, and
Mac OSX which reads LXT, LXT2, VZT, FST, and GHW files as well as standard
Verilog VCD/EVCD files and allows their viewing.

Documentation: https://gtkwave.github.io/gtkwave/

Sources: https://github.com/gtkwave/gtkwave

Installation: https://github.com/gtkwave/gtkwave
'''

from siliconcompiler.tools._common import \
    get_tool_task


def setup(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'gtkwave')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=v3.3.116', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)


################################
# Version Check
################################
def parse_version(stdout):
    # First line: GTKWave Analyzer v3.3.116 (w)1999-2023 BSI
    return stdout.split()[2]


def normalize_version(version):
    if version[0] == 'v':
        return version[1:]
    return version
