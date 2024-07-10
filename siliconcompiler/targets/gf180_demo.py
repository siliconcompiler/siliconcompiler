import siliconcompiler
from siliconcompiler.flows import asicflow, asictopflow, signoffflow, synflow
from siliconcompiler.checklists import oh_tapeout
from siliconcompiler.tools.openroad import openroad
from siliconcompiler.tools._common import get_tool_tasks

from lambdapdk import gf180
from lambdapdk.gf180.libs import gf180mcu


####################################################
# Target Setup
####################################################
def setup(chip, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1, route_np=1,
          timing_np=1):
    '''
    Global foundries 180 Demo Target
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
    chip.use(gf180)
    chip.use(gf180mcu)
    chip.use(asicflow, **asic_flow_args)
    chip.use(synflow, syn_np=syn_np, timing_np=timing_np)
    chip.use(asictopflow)
    chip.use(signoffflow)
    chip.use(oh_tapeout)

    # 2. Set default targets
    chip.set('option', 'flow', 'asicflow', clobber=False)
    chip.set('option', 'pdk', 'gf180', clobber=False)
    chip.set('option', 'stackup', '5LM_1TM_9K', clobber=False)

    # 3. Set project specific design choices
    chip.set('asic', 'logiclib', 'gf180mcu_fd_sc_mcu9t5v0', clobber=False)

    # 4. get project specific design choices
    chip.set('asic', 'delaymodel', 'nldm', clobber=False)
    chip.set('constraint', 'density', 40, clobber=False)
    chip.set('constraint', 'coremargin', 1, clobber=False)

    # 5. Timing corners
    chip.set('constraint', 'timing', 'slow', 'libcorner', 'slow', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'pexcorner', 'wst', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'fast', 'libcorner', 'fast', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'pexcorner', 'bst', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'typical', 'libcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'pexcorner', 'typ', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'check', ['power'], clobber=False)

    # PSM gets stuck in a loop, must be disabled for now on gf180
    for task in get_tool_tasks(chip, openroad):
        chip.set('tool', 'openroad', 'task', task, 'var', 'psm_enable', 'false')
    chip.set('tool', 'openroad', 'task', 'route', 'var', 'ant_check', 'false')


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('gf180_demo.json')
