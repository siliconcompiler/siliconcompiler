from siliconcompiler import Chip
from siliconcompiler.flows import interposerflow, drcflow

from lambdapdk import interposer
from lambdapdk.interposer.libs import bumps


####################################################
# Target Setup
####################################################
def setup(chip):
    '''
    Interposer Demo Target
    '''

    # 1. Load PDK, flow, libs
    chip.use(interposer)
    chip.use(bumps)
    chip.use(interposerflow)
    chip.use(drcflow)

    # 2. Set default targets
    chip.set('option', 'flow', 'interposerflow', clobber=False)
    chip.set('option', 'pdk', 'interposer', clobber=False)
    chip.set('option', 'stackup', '3ML_0400', clobber=False)
    chip.set('option', 'var', 'openroad_libtype', 'none', clobber=False)
    chip.set('option', 'var', 'klayout_libtype', 'none', clobber=False)

    # 3. Set project specific design choices
    chip.set('asic', 'macrolib', 'interposer_bumps', clobber=False)

    # 4. get project specific design choices
    chip.set('asic', 'delaymodel', 'nldm', clobber=False)

    # 5. Timing corners
    chip.set('constraint', 'timing', 'slow', 'libcorner', 'slow', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'pexcorner', 'maximum', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'slow', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'fast', 'libcorner', 'fast', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'pexcorner', 'minimum', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'fast', 'check', ['setup', 'hold'], clobber=False)

    chip.set('constraint', 'timing', 'typical', 'libcorner', 'typ', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'pexcorner', 'typical', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'mode', 'func', clobber=False)
    chip.set('constraint', 'timing', 'typical', 'check', ['setup', 'hold'], clobber=False)


#########################
if __name__ == "__main__":
    target = Chip('<target>')
    setup(target)
    target.write_manifest('interposer_demo.json')
