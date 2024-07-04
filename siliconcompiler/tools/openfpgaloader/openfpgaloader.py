'''
The OpenFPGALoader is a universal utility for programming
FPGAs. Compatible with many boards, cables and FPGA from
major manufacturers (Xilinx, Altera/Intel, Lattice, Gowin,
Efinix, Anlogic). openFPGALoader works on Linux, Windows and
macOS.

Documentation: https://github.com/trabucayre/openFPGALoader

Sources: https://github.com/trabucayre/openFPGALoader

Installation: https://github.com/trabucayre/openFPGALoader

Status: SC integration WIP
'''
from siliconcompiler.tools._common import get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    ''' openFPGALoader setup function
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'openfpgaloader'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # tool setup
    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--Version', clobber=False)
    chip.set('tool', tool, 'version', '0.5.0', clobber=False)

    options = []
    options.append("inputs" + chip.top() + ".bit")
    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)
