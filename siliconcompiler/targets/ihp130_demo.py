import siliconcompiler
from siliconcompiler.flows import asicflow, asictopflow, signoffflow, synflow
from siliconcompiler.checklists import oh_tapeout
from lambdapdk import ihp130
from lambdapdk.ihp130.libs import sg13g2_stdcell


####################################################
# Target Setup
####################################################
def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1,
          timing_np=1):
    '''
    IHP130 Demo Target
    '''

    asic_flow_args = {
        "syn_np": syn_np,
        "floorplan_np": floorplan_np,
        "physyn_np": physyn_np,
        "place_np": place_np,
        "cts_np": cts_np,
        "route_np": route_np
    }
    # 1. Load PDK, flow, libs
    chip.use(ihp130)
    chip.use(sg13g2_stdcell)
    chip.use(asicflow, **asic_flow_args)
    chip.use(synflow, syn_np=syn_np, timing_np=timing_np)
    chip.use(asictopflow)
    chip.use(signoffflow)
    chip.use(oh_tapeout)

    # 2. Set default targets
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'ihp130', clobber=False)
    chip.set('option', 'stackup', '5M2TL', clobber=False)

    # 3. Set project specific design choices
    chip.set('asic', 'logiclib', 'sg13g2_stdcell', clobber=False)

    # 4. get project specific design choices
    chip.set('asic', 'delaymodel', 'nldm', clobber=False)
    chip.set('constraint', 'density', 40, clobber=False)
    chip.set('constraint', 'coremargin', 4.8, clobber=False)

    # 5. Timing corners
    chip.set('constraint', 'timing', 'slow', 'libcorner', 'slow', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'pexcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'fast', 'libcorner', 'fast', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'pexcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'typical', 'libcorner', 'typ', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'pexcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'check', ['power'], clobber=False)


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('ihp130_demo.json')
