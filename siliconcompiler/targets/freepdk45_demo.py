import siliconcompiler

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

    #0. Defining the project
    chip.set('option', 'target', 'freepdk45_demo')

    #1. Setting to ASIC mode
    chip.set('option', 'mode','asic')

    #2. Load PDK, flow, libs combo
    from pdks import freepdk45
    from flows import lintflow, asicflow, asictopflow
    from libs import nangate45
    chip.use(freepdk45)
    chip.use(lintflow)
    chip.use(asicflow)
    chip.use(asictopflow)
    chip.use(nangate45)

    #3. Set flow and pdk
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'freepdk45')
    chip.set('option', 'stackup', '10M')

    #4. Select libraries
    chip.set('asic', 'logiclib', 'nangate45')

    #5. Set project specific design choices
    chip.set('constraint', 'density', 10)
    chip.set('constraint', 'coremargin', 1.9)

    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('asic', 'rclayer', 'clk', "m5")
    chip.set('asic', 'rclayer', 'data',"m3")
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")

    #6. Timing corners
    corner = 'typical'
    chip.set('constraint', 'timing', 'worst', 'libcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'pexcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'mode', 'func')
    chip.set('constraint', 'timing', 'worst', 'check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
