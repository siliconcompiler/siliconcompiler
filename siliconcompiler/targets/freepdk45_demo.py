import siliconcompiler
from siliconcompiler.targets import utils

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    Demonstration target for compiling ASICs with FreePDK45 and the open-source
    asicflow.
    '''

    chip = siliconcompiler.Chip('<design>')
    setup(chip)
    return chip


####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Target setup
    '''

    #1. Load PDK, flow, libs combo
    from pdks import freepdk45
    from flows import lintflow, asicflow, asictopflow
    from libs import nangate45
    chip.use(freepdk45)
    chip.use(lintflow)
    chip.use(asicflow)
    chip.use(asictopflow)
    chip.use(asicflow)
    chip.use(nangate45)

    #2. Setup default show tools
    utils.set_common_showtools(chip)

    #3. Set flow and pdk
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'freepdk45')
    chip.set('option', 'stackup', '10M')

    #4. Select libraries
    chip.set('asic', 'logiclib', 'nangate45')

    #5 Set project specific design choices
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('constraint', 'density', 10)
    chip.set('constraint', 'coremargin', 1.9)

    #6. Timing corners
    corner = 'typical'
    chip.set('constraint', 'timing', 'worst', 'libcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'pexcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'mode', 'func')
    chip.set('constraint', 'timing', 'worst', 'check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
