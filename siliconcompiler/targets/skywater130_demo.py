import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    Demonstration target for compiling ASICs with Skywater130 and the
    open-source asicflow.
    '''

    chip = siliconcompiler.Chip()
    setup(chip)
    return chip


####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Template project file.
    '''

    #1. Defining the project
    project = 'skywater130_demo'
    chip.set('target', project)

    #2. Load PDK, flow, libs
    chip.load_pdk('skywater130')
    chip.load_flow('asicflow')
    chip.load_lib('sky130')

    #3. Set default targets
    chip.set('flow', 'asicflow')

    #4. Set project specific design choices
    chip.set('asic', 'logiclib', 'sky130hd')

    #5. et project specific design choices
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
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.add('mcmm','worst','check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
