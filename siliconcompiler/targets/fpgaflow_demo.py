import siliconcompiler
from siliconcompiler.fpgas import lattice_ice40
from siliconcompiler.fpgas import vpr_example

from siliconcompiler.targets import utils

from siliconcompiler.flows import fpgaflow


####################################################
# Target Setup
####################################################
def setup(chip):
    '''
    Demonstration target for running the open-source fpgaflow.
    '''

    # 1. Configure fpga part
    chip.use(select_fpga_family(chip))

    # 2. Load flow
    chip.use(fpgaflow,
             syn_tool=select_syn_tool(chip),
             pnr_tool=select_pnr_tool(chip))

    # 3. Setup default show tools
    utils.set_common_showtools(chip)

    # 4. Select default flow
    chip.set('option', 'mode', 'fpga', clobber=False)
    chip.set('option', 'flow', 'fpgaflow', clobber=False)


def select_fpga_family(chip):

    partname = chip.get('fpga', 'partname')

    fpga_family = None

    if (partname.startswith("ice40")):
        fpga_family = lattice_ice40
    elif (partname.startswith("example_arch")):
        fpga_family = vpr_example
    else:
        chip.error("Unsupported partname {partname} found", fatal=True)

    return fpga_family


def select_syn_tool(chip):

    partname = chip.get('fpga', 'partname')

    syn_tool = None

    if (partname.startswith("ice40")):
        syn_tool = 'yosys'
    elif (partname.startswith("example_arch")):
        syn_tool = 'yosys'
    else:
        chip.error("Unsupported partname {partname} found", fatal=True)

    return syn_tool


def select_pnr_tool(chip):

    partname = chip.get('fpga', 'partname')

    pnr_tool = None

    if (partname.startswith("ice40")):
        pnr_tool = 'nextpnr'
    elif (partname.startswith("example_arch")):
        pnr_tool = 'vpr'
    else:
        chip.error("Unsupported partname {partname} found", fatal=True)

    return pnr_tool


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
