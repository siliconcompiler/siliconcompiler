import os
import siliconcompiler
from siliconcompiler.targets import skywater130_demo


def setup(chip):
    '''
    "Self-test" target which builds a small 8-bit counter design as an ASIC,
    targeting the Skywater130 PDK.

    This target is intended for testing purposes only,
    to verify that SiliconCompiler is installed and configured correctly.
    '''

    # Set design name
    design = 'heartbeat'
    chip.set('design', design)

    # Load the Sky130 PDK/standard cell library target.
    chip.load_target(skywater130_demo)

    # Set quiet flag
    chip.set('option', 'quiet', True, clobber=False)

    # Set die area and clock constraint.
    chip.set('constraint', 'outline', [(0, 0), (50, 50)], clobber=False)
    chip.set('constraint', 'corearea', [(5, 5), (45, 45)], clobber=False)
    chip.clock('clk', period=10)

    # Add source files.
    chip.input(os.path.join(os.path.dirname(__file__), '..', 'data', f'{design}.v'))


#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asic_demo.json')
