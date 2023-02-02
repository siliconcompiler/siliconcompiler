import siliconcompiler
from siliconcompiler.targets import utils

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

def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1, dfm_np=1):
    '''
    Skywater130 Demo Target
    '''

    #1. Load PDK, flow, libs
    from pdks import skywater130
    from flows import asicflow, asictopflow, signoffflow
    from libs import sky130hd
    from checklists.oh_tapeout import oh_tapeout
    chip.use(skywater130)
    chip.use(asicflow, syn_np=syn_np, floorplan_np=floorplan_np, physyn_np=physyn_np, place_np=place_np, cts_np=cts_np, route_np=route_np, dfm_np=dfm_np)
    chip.use(asictopflow)
    chip.use(signoffflow)
    chip.use(sky130hd)
    chip.use(oh_tapeout)

    #2. Setup default show tools
    utils.set_common_showtools(chip)

    #3. Set default targets
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'skywater130')
    chip.set('option', 'stackup', '5M1LI')

    #4. Set project specific design choices
    chip.set('asic', 'logiclib', 'sky130hd')

    #5. get project specific design choices
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('constraint', 'density', 10)
    chip.set('constraint', 'coremargin', 4.6)

    #6. Timing corners
    corner = 'typical'
    chip.set('constraint', 'timing', 'worst', 'libcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'pexcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'mode', 'func')
    chip.add('constraint', 'timing', 'worst', 'check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
