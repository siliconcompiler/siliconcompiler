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

def setup(chip):
    '''
    Template project file.
    '''

    #1. Defining the project
    project = 'freepdk45_demo'
    chip.set('target', project)

    #2. Load PDK, flow, libs
    chip.load_pdk('freepdk45')
    chip.load_flow('asicflow')
    chip.load_lib('nangate45')

    #3. Set default flow
    chip.set('flow', 'asicflow')

    #4. Set project specific design choices
    chip.set('asic', 'logiclib', 'nangate45')
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

    #5. Timing corners
    corner = 'typical'
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.set('mcmm','worst','check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
