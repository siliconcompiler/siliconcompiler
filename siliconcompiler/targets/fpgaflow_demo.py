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
    part_name = chip.get('option', 'fpga')
    chip.use(select_fpga_family(chip, part_name))

    # 2. Load flow
    syn_tool = chip.get('fpga', part_name, 'syntool')
    pnr_tool = chip.get('fpga', part_name, 'pnrtool')
    chip.use(fpgaflow, syn_tool=syn_tool, pnr_tool=pnr_tool)

    # 3. Setup default show tools
    utils.set_common_showtools(chip)

    # 4. Select default flow
    chip.set('option', 'mode', 'fpga', clobber=False)
    chip.set('option', 'flow', 'fpgaflow', clobber=False)


def select_fpga_family(chip, part_name):

    if (part_name.startswith('ice40')):
        fpga_family = lattice_ice40
    elif (part_name.startswith('example_arch')):
        fpga_family = vpr_example
    else:
        chip.error(f"Cannot determine FPGA family from part name {part_name}", fatal=True)

    return fpga_family


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
