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
    part_name = chip.get('fpga', 'partname')
    if not part_name:
        chip.error('FPGA partname has not been set.', fatal=True)

    fpga_family, fpga_tool_chain = select_fpga_family(chip, part_name)
    chip.use(fpga_family)

    if part_name not in chip.getkeys('fpga'):
        chip.error(f'{part_name} has not been loaded', fatal=True)

    # 2. Load flow
    chip.use(fpgaflow, tool_chain=fpga_tool_chain)

    # 3. Setup default show tools
    utils.set_common_showtools(chip)

    # 4. Select default flow
    chip.set('option', 'mode', 'fpga', clobber=False)
    chip.set('option', 'flow', 'fpgaflow', clobber=False)


def select_fpga_family(chip, part_name):

    if (part_name.startswith('ice40')):
        fpga_family = lattice_ice40
        fpga_tool_chain = 'nextpnr'
    elif (part_name.startswith('example_arch')):
        fpga_family = vpr_example
        fpga_tool_chain = 'vpr'
    else:
        chip.error(f"Cannot determine FPGA family from part name {part_name}", fatal=True)

    return fpga_family, fpga_tool_chain


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
