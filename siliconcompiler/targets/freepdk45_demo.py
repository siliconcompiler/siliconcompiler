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
    chip.load_pdk('freepdk45')
    chip.load_flow('lintflow')
    chip.load_flow('asicflow')
    chip.load_flow('asictopflow')
    chip.load_lib('nangate45')

    #3. Set flow and pdk
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'freepdk45')

    #4. Select libraries
    chip.set('asic', 'logiclib', 'nangate45')

    #5. Set project specific design choices
    chip.set('asic', 'stackup', '10M')
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('asic', 'minlayer', "m1")
    chip.set('asic', 'maxlayer', "m10")
    chip.set('asic', 'maxfanout', 64)
    chip.set('asic', 'maxlength', 1000)
    chip.set('asic', 'maxslew', 0.2e-9)
    chip.set('asic', 'maxcap', 0.2e-12)
    chip.set('asic', 'rclayer', 'clk', "m5")
    chip.set('asic', 'rclayer', 'data',"m3")
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")
    chip.set('asic', 'density', 10)
    chip.set('asic', 'aspectratio', 1)
    chip.set('asic', 'coremargin', 1.9)

    #6. Timing corners
    corner = 'typical'
    chip.set('constraint','worst','libcorner', corner)
    chip.set('constraint','worst','pexcorner', corner)
    chip.set('constraint','worst','mode', 'func')
    chip.set('constraint','worst','check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
