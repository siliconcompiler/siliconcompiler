import siliconcompiler
from siliconcompiler.targets import utils

from siliconcompiler.flows import fpgaflow


####################################################
# Target Setup
####################################################
def setup(chip):
    '''
    Demonstration target for running the open-source fpgaflow.
    '''

    # 1. Load flow
    chip.use(fpgaflow)

    # 2. Setup default show tools
    utils.set_common_showtools(chip)

    # 3. Select default flow
    chip.set('option', 'mode', 'fpga', clobber=False)
    chip.set('option', 'flow', 'fpgaflow', clobber=False)

    # 4. Target-specific synthesis settings
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', '4')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'memmap', 'None')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap', 'None')


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
