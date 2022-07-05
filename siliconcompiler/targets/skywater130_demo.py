import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    Demonstration target for compiling ASICs with Skywater130 and the
    open-source asicflow.
    '''

    chip = siliconcompiler.Chip('<design>')
    setup(chip)
    return chip


####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Skywater130 Demo Target
    '''

    #0. Defining the project
    project = 'skywater130_demo'
    chip.set('option', 'target', project)

    #1. Setting to ASIC mode
    chip.set('option', 'mode','asic')

    #2. Load PDK, flow, libs
    chip.load_pdk('skywater130')
    chip.load_flow('asicflow')
    chip.load_flow('asictopflow')
    chip.load_flow('signoffflow')
    chip.load_lib('sky130hd')
    chip.load_checklist('oh_tapeout')

    #3. Set default targets
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'skywater130')

    #4. Set project specific design choices
    chip.set('asic', 'logiclib', 'sky130hd')

    #5. et project specific design choices
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('asic', 'stackup', '5M1LI')
    # TODO: how does LI get taken into account?
    chip.set('asic', 'minlayer', "m1")
    chip.set('asic', 'maxlayer', "m5")
    chip.set('asic', 'maxfanout', 5) # TODO: fix this
    chip.set('asic', 'maxlength', 21000)
    chip.set('asic', 'maxslew', 1.5e-9)
    chip.set('asic', 'maxcap', .1532e-12)
    chip.set('asic', 'rclayer', 'clk', 'm5')
    chip.set('asic', 'rclayer', 'data', 'm3')
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")
    chip.set('asic', 'density', 10)
    chip.set('asic', 'aspectratio', 1)
    # Least common multiple of std. cell width (0.46) and height (2.72)
    chip.set('asic', 'coremargin', 62.56)

    #5. Timing corners
    corner = 'typical'
    chip.set('constraint', 'worst', 'libcorner', corner)
    chip.set('constraint', 'worst', 'pexcorner', corner)
    chip.set('constraint', 'worst', 'mode', 'func')
    chip.add('constraint', 'worst', 'check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
