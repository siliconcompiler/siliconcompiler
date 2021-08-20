
import os
import sys
import re
import numpy as np
import siliconcompiler
import matplotlib.pyplot as plt

####################################################
# PDK Setup
####################################################

def setup_platform(chip):
    '''
    Setup package for the scalable lambda technology.
    The lambda technology uses the technology node to
    approximate performannce of a design at different
    nodes.
    '''

    foundry = 'virtual'
    process = 'lambda'
    libtype = 'default'
    rev = 'r1p0'
    # TODO: fix, constants for now
    hscribe = 0.1
    vscribe = 0.1
    edgemargin = 2
    d0 = 1.25

    #Checking that all parameters have been set
    chip.set('pdk','node',45)
    chip.set('pdk','stackup','m10')
    if not chip.get('pdk', 'node'):
        chip.logger.error("Required PDK node parameter unspecified!!")
        os.sys.exit()
    elif not chip.get('pdk', 'stackup'):
        chip.logger.error("Required PDK stackup parameter unspecified!!")
        os.sys.exit()
    else:
        node = chip.get('pdk', 'node')
        stackup = chip.get('pdk', 'stackup')[0]


    # Process details
    chip.set('pdk','foundry', foundry)
    chip.set('pdk','process', process)
    chip.set('pdk','rev', rev)

    ##################
    # Wafer Size
    ##################

    if node > 130:
        wafersize = 300
    else:
        wafersize = 200

    ##################
    # DPW Settings
    ##################

    chip.set('pdk','edgemargin', edgemargin)
    chip.set('pdk','hscribe', hscribe)
    chip.set('pdk','vscribe', vscribe)
    chip.set('pdk','d0', d0)

    ##################
    # Tap settings
    ##################
    tapmax = {}
    tapmax['45'] = 120
    tapmax['7'] =  25

    #TODO: turn into a core function!
    samples = len(tapmax)
    x = np.zeros((samples,))
    y = np.zeros((samples,))
    i = 0
    for node,val in tapmax.items():
        x[i] = int(node)
        y[i] = val
        i=i+1

    #plt.plot(x, y)
    #plt.show()

    tapmax = 120 #predict! TODO
    tapoffset = 0 #predict! TODO

    chip.set('pdk','tapmax', tapmax)
    chip.set('pdk','tapoffset', tapoffset)

    ##################
    # APR Settings
    ##################

    #1. Derive lambda value from node
    #2. Parse metalstack value
    #3. Specify metal stack relative to ambda value
    #4. Auto-generate design rules and lambda.tech

    chip.set('pdk','aprtech',stackup, libtype, 'lef','lambda.tech.lef')

    # Routing Grid Definitions

    #TODO: variable based on metalstack
    for sc_name in ['m1','m2']:
        xoffset = 1
        xpitch = 1
        yoffset = 1
        ypitch = 1
        adj = 1
        chip.set('pdk','grid', stackup, sc_name, 'name', sc_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', xoffset)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch', xpitch)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', yoffset)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch', ypitch)
        chip.set('pdk','grid', stackup, sc_name, 'adj', adj)


####################################################
# Library Setup
####################################################
def setup_libs(chip, vendor=None, type=None):

    libname = 'lambdalib'
    rev = 'r1p0'
    sitename = 'lambdasite'

    foundry = chip.get('pdk','foundry')
    process = chip.get('pdk','process')
    pdkrev  = chip.get('pdk','rev')
    stackup = chip.get('pdk','stackup')[0]
    #TODO: ugly and circular still...
    libtype = chip.getkeys('pdk','aprtech',stackup)

    ###################
    # Static settings
    ###################

    chip.set('stdcell',libname,'rev', rev)
    chip.set('stdcell',libname,'site', sitename)
    chip.set('stdcell',libname,'libtype',libtype)


    ###################
    # Library Cells
    ###################

    #TODO: Fill in with asic cell values

    #driver
    chip.set('stdcell',libname,'driver', "BUF_X4")

    # clock buffers
    chip.set('stdcell',libname,'cells','clkbuf', "BUF_X4")

    # tie cells
    chip.set('stdcell',libname,'cells','tie', ["LOGIC1_X1",
                                               "LOGIC0_X1"])


    # hold cells
    chip.set('stdcell',libname,'cells','hold', "BUF_X1")

    # filler
    chip.set('stdcell',libname,'cells','filler', ["FILLCELL_X1",
                                                  "FILLCELL_X2",
                                                  "FILLCELL_X4",
                                                  "FILLCELL_X8",
                                                  "FILLCELL_X16",
                                                  "FILLCELL_X32"])

    # Stupid small cells
    chip.set('stdcell',libname,'cells','ignore', ["AOI211_X1",
                                                  "OAI211_X1"])

    # Tapcell
    chip.set('stdcell',libname,'cells','tapcell', "FILLCELL_X1")

    # Endcap
    chip.set('stdcell',libname,'cells','endcap', "FILLCELL_X1")

    #####################
    # Dynamic variables
    #####################

    libwidth = 0
    libheight = 0
    chip.set('stdcell',libname,'width', libwidth)
    chip.set('stdcell',libname,'height', libheight)

    #####################
    # Auto-generate files
    #####################
    #LOTS OF CODE...
    corner = 'typical'
    chip.set('stdcell',libname, 'model', corner, 'nldm', 'lib','lambda.lib')
    chip.set('stdcell',libname,'lef','lambda.lef')


#########################
def setup_design(chip):

    chip.set('asic', 'stackup', chip.get('pdk', 'stackup')[0])
    chip.set('asic', 'targetlib', chip.getkeys('stdcell'))
    chip.set('asic', 'minlayer', "m1")
    chip.set('asic', 'maxlayer', "m10")
    chip.set('asic', 'maxfanout', 64)
    chip.set('asic', 'maxlength', 1000)
    chip.set('asic', 'maxslew', 0.2e-9)
    chip.set('asic', 'maxcap', 0.2e-12)
    chip.set('asic', 'clklayer', "m5")
    chip.set('asic', 'rclayer', "m3")
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")
    chip.set('asic', 'density', 1.0)

    corner = 'typical'
    # hard coded mcmm settings (only one corner!)
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.set('mcmm','worst','check', ['setup','hold'])

#########################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    chip.set('pdk','node','1')
    chip.set('pdk','stackup','m10')
    # load configuration
    setup_platform(chip)
    setup_libs(chip)
    # write out result
    chip.writecfg(output)
