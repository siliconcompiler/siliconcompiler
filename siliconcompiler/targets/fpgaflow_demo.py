import siliconcompiler
from siliconcompiler import SiliconCompilerError
from siliconcompiler.fpgas import lattice_ice40

from siliconcompiler.flows import fpgaflow


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')


####################################################
# Target Setup
####################################################
def setup(chip, partname=None):
    '''
    Demonstration target for running the open-source fpgaflow.
    '''

    # 1. Configure fpga part
    if not partname:
        partname = chip.get('fpga', 'partname')

    if not partname:
        raise SiliconCompilerError('FPGA partname has not been set.', chip=chip)

    # 2.  Load all available FPGAs
    chip.use(lattice_ice40)

    # 3. Load flow
    chip.use(fpgaflow, partname=partname)

    # 4. Select default flow
    chip.set('option', 'flow', 'fpgaflow', clobber=False)


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('fpgaflow_demo.json')
