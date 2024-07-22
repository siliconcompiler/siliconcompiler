import siliconcompiler
from siliconcompiler.flows import lintflow, asicflow, asictopflow, synflow

from lambdapdk import freepdk45
from lambdapdk.freepdk45.libs import nangate45


####################################################
# Target Setup
####################################################
def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1,
          timing_np=1):
    '''
    FreePDK45 demo target
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
    chip.use(freepdk45)
    chip.use(nangate45)
    chip.use(lintflow)
    chip.use(asicflow, **asic_flow_args)
    chip.use(synflow, syn_np=syn_np, timing_np=timing_np)
    chip.use(asictopflow)

    # 2. Set flow and pdk
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'freepdk45', clobber=False)
    chip.set('option', 'stackup', '10M', clobber=False)

    # 3. Select libraries
    chip.set('asic', 'logiclib', 'nangate45', clobber=False)

    # 4. Set project specific design choices
    chip.set('asic', 'delaymodel', 'nldm', clobber=False)
    chip.set('constraint', 'density', 40, clobber=False)
    chip.set('constraint', 'coremargin', 1, clobber=False)

    # 5. Timing corners
    corner = 'typical'
    chip.set('constraint', 'timing', 'worst', 'libcorner', corner, clobber=False)
    chip.set('constraint', 'timing', 'worst', 'pexcorner', corner, clobber=False)
    chip.set('constraint', 'timing', 'worst', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'worst', 'check', ['setup', 'hold'], clobber=False)


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('freepdk45_demo.json')
