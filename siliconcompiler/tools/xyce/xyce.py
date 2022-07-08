import os

import siliconcompiler


#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    Xyce is a high performance SPICE-compatible circuit simulator
    capable capable of solving extremely large circuit problems by
    supporting large-scale parallel computing platforms. It also
    supports serial execution on all common desktop platforms,
    and small-scale parallel runs on Unix-like systems.

    Documentation: https://xyce.sandia.gov/documentation

    Sources: https://github.com/Xyce/Xyce

    Installation: https://xyce.sandia.gov/documentation/BuildingGuide.html

    Status: SC integration WIP

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'spice')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################
def setup(chip):

     tool = 'xyce'
     step = chip.get('arg','step')
     index = chip.get('arg','index')
     clobber = False

     chip.set('tool', tool, 'exe', tool)
     chip.set('tool', tool, 'version', '0.0', clobber=clobber)
     chip.set('tool', tool, 'threads', step, index, os.cpu_count(), clobber=clobber)

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("xyce.json")
