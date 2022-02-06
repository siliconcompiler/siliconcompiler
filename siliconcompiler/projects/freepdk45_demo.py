import os
import sys
import re
import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    Template project file.
    '''

    chip = siliconcompiler.Chip()
    setup_project(chip)
    return chip


####################################################
# PDK Setup
####################################################

def setup_project(chip):
    '''
    Template project file.
    '''

    #1. Set PDK
    chip.set('target', 'pdk', 'freepdk45')

    #2. Specify flow
    chip.set('target', 'flow', 'asicflow')

    #3. Specify target libs
    chip.add('target', 'lib', 'nangate45')

    #4. Project specific design choices
    chip.set('asic', 'stackup', '10M')
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

    # Timing corners
    corner = 'typical'
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.set('mcmm','worst','check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
