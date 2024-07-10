import siliconcompiler
from siliconcompiler import SiliconCompilerError
from siliconcompiler.fpgas import lattice_ice40
from siliconcompiler.fpgas import vpr_example

from siliconcompiler.flows import fpgaflow


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')


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
        raise SiliconCompilerError('FPGA partname has not been set.', chip=chip)

    # 2.  Load all available FPGAs
    chip.use(lattice_ice40)
    chip.use(vpr_example)

    if part_name not in chip.getkeys('fpga'):
        raise SiliconCompilerError(f'{part_name} has not been loaded', chip=chip)

    # 3. Load flow
    chip.use(fpgaflow)

    # 4. Select default flow
    chip.set('option', 'flow', 'fpgaflow', clobber=False)


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
