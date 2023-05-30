import siliconcompiler
from siliconcompiler.targets import utils

from siliconcompiler.flows import fpga_nextpnr_flow


def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')


####################################################
# Target Setup
####################################################
def setup(chip, toolflow='vpr'):
    '''
    Demonstration target for running the open-source fpgaflow.
    '''

    # 1. Load flow
    chip.use(fpga_nextpnr_flow)

    # 2. Setup default show tools
    utils.set_common_showtools(chip)

    # 3. Select default flow
    chip.set('option', 'mode', 'fpga', clobber=False)
    chip.set('option', 'flow', 'fpga_nextpnr_flow', clobber=False)


#########################
if __name__ == "__main__":
    target = make_docs(siliconcompiler.Chip('<target>'))
    setup(target)
    target.write_manifest('fpga_nextpnr_flow_demo.json')
