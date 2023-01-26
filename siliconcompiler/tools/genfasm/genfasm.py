import importlib
import os
import siliconcompiler
import re

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''
    To-Do: Add details here
    '''

    chip = siliconcompiler.Chip('<design>')
    step = 'bitstream'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.genfasm.bitstream import setup
    setup(chip)
    return chip

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("genfasm.json")
