import siliconcompiler
from siliconcompiler.flows import asicflow, synflow

from lambdapdk import asap7
from lambdapdk.asap7.libs import asap7sc7p5t


####################################################
# Target Setup
####################################################
def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1,
          timing_np=1):
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
    chip.use(asap7sc7p5t)
    chip.use(asicflow, **asic_flow_args)
    chip.use(synflow, syn_np=syn_np, timing_np=timing_np)

    # 2. Select default flow/PDK
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'asap7', clobber=False)
    chip.set('option', 'stackup', '10M', clobber=False)

    # 3. Select libraries
    chip.set('asic', 'logiclib', 'asap7sc7p5t_rvt', clobber=False)

    # 4. Project specific design choices
    chip.set('asic', 'delaymodel', 'nldm', clobber=False)
    chip.set('constraint', 'density', 40, clobber=False)
    chip.set('constraint', 'coremargin', 1, clobber=False)

    # 5. Timing corners
    pex_corner = 'typical'

    chip.set('constraint', 'timing', 'slow', 'libcorner', 'slow', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'pexcorner', pex_corner, clobber=False)
    chip.set('constraint', 'timing', 'slow', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'fast', 'libcorner', 'fast', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'pexcorner', pex_corner, clobber=False)
    chip.set('constraint', 'timing', 'fast', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'typical', 'libcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'pexcorner', pex_corner, clobber=False)
    chip.set('constraint', 'timing', 'typical', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'check', ['power'], clobber=False)


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asap7_demo.json')
