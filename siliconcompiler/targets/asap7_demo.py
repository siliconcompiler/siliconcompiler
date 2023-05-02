import siliconcompiler
from siliconcompiler.targets import utils

from siliconcompiler.pdks import asap7
from siliconcompiler.flows import asicflow
from siliconcompiler.libs import asap7sc7p5t


####################################################
# Target Setup
####################################################
def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1):
    '''
    ASAP7 Demo Target
    '''

    asic_flow_args = {
        "syn_np": syn_np,
        "floorplan_np": floorplan_np,
        "physyn_np": physyn_np,
        "place_np": place_np,
        "cts_np": cts_np,
        "route_np": route_np
    }

    # 1. Load PDK, flow, libs combo
    chip.use(asap7)
    chip.use(asicflow, **asic_flow_args)
    chip.use(asap7sc7p5t)

    # 2. Setup default show tools
    utils.set_common_showtools(chip)

    # 3. Select default flow/PDK
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'flow', 'asicflow')
    chip.set('option', 'pdk', 'asap7')
    chip.set('option', 'stackup', '10M')

    # 4. Select libraries
    chip.set('asic', 'logiclib', 'asap7sc7p5t_rvt')

    # 5. Project specific design choices
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('constraint', 'density', 10)
    chip.set('constraint', 'coremargin', 0.270)

    # 6. Timing corners
    pex_corner = 'typical'

    chip.set('constraint', 'timing', 'slow', 'libcorner', 'slow')
    chip.set('constraint', 'timing', 'slow', 'pexcorner', pex_corner)
    chip.set('constraint', 'timing', 'slow', 'mode', 'func')
    chip.set('constraint', 'timing', 'slow', 'check', ['setup', 'hold'])

    chip.set('constraint', 'timing', 'fast', 'libcorner', 'fast')
    chip.set('constraint', 'timing', 'fast', 'pexcorner', pex_corner)
    chip.set('constraint', 'timing', 'fast', 'mode', 'func')
    chip.set('constraint', 'timing', 'fast', 'check', ['setup', 'hold'])

    chip.set('constraint', 'timing', 'typical', 'libcorner', 'typical')
    chip.set('constraint', 'timing', 'typical', 'pexcorner', pex_corner)
    chip.set('constraint', 'timing', 'typical', 'mode', 'func')
    chip.set('constraint', 'timing', 'typical', 'check', ['power'])


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asap7_demo.json')
