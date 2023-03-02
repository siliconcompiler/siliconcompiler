import os
import siliconcompiler

def setup(chip):
    '''
    "Self-test" target which builds a small 8-bit counter design as an ASIC,
    targeting the Skywater130 PDK.

    This target is intended for testing purposes only,
    to verify that SiliconCompiler is installed and configured correctly.
    '''

    # Load the Sky130 PDK/standard cell library target.
    design = 'heartbeat'
    chip.load_target('skywater130_demo')

    # Set die area and clock constraint.
    chip.set('constraint', 'outline', [(0, 0), (50, 50)])
    chip.set('constraint', 'corearea', [(5, 5), (45, 45)])
    chip.clock('clk', period=10)

    # Set design name and source files.
    chip.set('design', design)
    chip.input(os.path.join(os.path.dirname(__file__), '..', 'data', f'{design}.v'))

#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asic_demo.json')
