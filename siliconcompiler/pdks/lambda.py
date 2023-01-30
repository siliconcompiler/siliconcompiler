
import os
import sys
import re
import numpy as np
import siliconcompiler

####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Setup package for the scalable lambda technology.
    The lambda technology uses the technology node to
    approximate performannce of a design at different
    nodes.
    '''

    ###############################################
    # Process
    ###############################################

    pdk = siliconcompiler.PDK()

    # Process details
    pdk.set('pdk','foundry', 'virtual')
    pdk.set('pdk','process', 'lambda')
    pdk.set('pdk','version', 'r1p0')

    #User arguments
    if 'node' in chip.getkeys('techarg'):
        node = float(chip.get('techarg', 'node')[0])
        stackup = chip.get('techarg', 'stackup')
    else:
        node = 45
        stackup = "M10"

    pdk.set('pdk','node', node)
    pdk.set('pdk','stackup', stackup)

    # Wafer Size
    if node > 130:
        wafersize = 300
    else:
        wafersize = 200

    ##################
    # DPW Settings
    ##################

    pdk.set('pdk','edgemargin', 2)
    pdk.set('pdk','hscribe', 0.1)
    pdk.set('pdk','vscribe', 0.1)
    pdk.set('pdk','d0', 1.25)

    # LUT + interpolation
    tapmax = 100
    tapoffset = 0
    pdk.set('pdk','tapmax', tapmax)
    pdk.set('pdk','tapoffset', tapoffset)

    ##################
    # APR Settings
    ##################

    #1. Derive lambda value from node
    #2. Parse metalstack value
    #3. Specify metal stack relative to ambda value
    #4. Auto-generate design rules and lambda.tech

    # Routing Grid Definitions

    #TODO: variable based on metalstack

    ###############################################
    # Libraries (TBD)
    ###############################################

    ###############################################
    # Methodology (TBD)
    ###############################################

    return pdk

#########################
if __name__ == "__main__":

    prefix = os.path.splitext(os.path.basename(__file__))[0]
    chip = siliconcompiler.Chip()
    chip.set('techarg', 'node', '45')
    chip.set('techarg', 'stackup', 'M10')
    setup_pdk(chip)
    chip.writecfg(prefix + '.json')
