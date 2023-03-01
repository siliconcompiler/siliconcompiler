import os
import siliconcompiler

def setup(chip):
    '''
    "Self-test" target which builds a small 8-bit counter design as an ASIC,
    targeting the Skywater130 PDK.

    This target is not intended for general-purpose use.
    It is intended to quickly verify that SiliconCompiler is installed and configured correctly.
    '''

    # Load the Sky130 PDK/standard cell library target.
    design = 'heartbeat'
    chip.load_target('skywater130_demo')

    # Set die area.
    chip.set('constraint', 'outline', [(0, 0), (50, 50)])
    chip.set('constraint', 'corearea', [(5, 5), (45, 45)])

    # Set design name and source files.
    chip.set('design', design)
    src_prefix = os.path.join(os.path.dirname(__file__), 'asic_demo', design)
    for suffix in ['.v', '.sdc']:
        chip.input(f'{src_prefix}{suffix}')

#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asic_demo.json')
