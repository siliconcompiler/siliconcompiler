
import os
import siliconcompiler


####################################################
# PDK Setup
####################################################
def setup_pdk(chip):
    '''
    Setup package for the scalable lambda technology.
    The lambda technology uses the technology node to
    approximate performannce of a design at different
    nodes.
    '''

    ###############################################
    # Process
    ###############################################

    # Process details
    chip.set('pdk', 'foundry', 'virtual')
    chip.set('pdk', 'process', 'lambda')
    chip.set('pdk', 'version', 'r1p0')

    # User arguments
    if 'node' in chip.getkeys('techarg'):
        node = float(chip.get('techarg', 'node')[0])
        stackup = chip.get('techarg', 'stackup')
    else:
        node = 45
        stackup = "M10"

    chip.set('pdk', 'node', node)
    chip.set('pdk', 'stackup', stackup)

    # Wafer Size
    if node > 130:
        wafersize = 300
    else:
        wafersize = 200

    ##################
    # DPW Settings
    ##################

    chip.set('pdk', 'wafersize', wafersize)
    chip.set('pdk', 'edgemargin', 2)
    chip.set('pdk', 'hscribe', 0.1)
    chip.set('pdk', 'vscribe', 0.1)
    chip.set('pdk', 'd0', 1.25)

    # LUT + interpolation
    tapmax = 100
    tapoffset = 0
    chip.set('pdk', 'tapmax', tapmax)
    chip.set('pdk', 'tapoffset', tapoffset)

    ##################
    # APR Settings
    ##################

    # 1. Derive lambda value from node
    # 2. Parse metalstack value
    # 3. Specify metal stack relative to ambda value
    # 4. Auto-generate design rules and lambda.tech

    # Routing Grid Definitions

    # TODO: variable based on metalstack

    ###############################################
    # Libraries (TBD)
    ###############################################

    ###############################################
    # Methodology (TBD)
    ###############################################


#########################
if __name__ == "__main__":

    prefix = os.path.splitext(os.path.basename(__file__))[0]
    chip = siliconcompiler.Chip()
    chip.set('techarg', 'node', '45')
    chip.set('techarg', 'stackup', 'M10')
    setup_pdk(chip)
    chip.writecfg(prefix + '.json')
