import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_gcd_checks():
    '''Test EDA flow with LVS and DRC
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.abspath(__file__)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/gcd/'

    # Inserting value into configuration
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('design', 'gcd')
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('clock', 'core_clock', 'pin', 'clk')
    chip.set('clock', 'core_clock', 'period', 2)
    chip.add('constraint', gcd_ex_dir + 'gcd_noclock.sdc')
    chip.set('target', 'asicflow_skywater130')
    chip.set('flowarg', 'verify', 'true')
    chip.set('asic', 'diearea', [(0, 0), (200.56, 201.28)])
    chip.set('asic', 'corearea', [(20.24, 21.76), (180.32, 184.96)])

    chip.target()

    # Run the chip's build process synchronously.
    chip.run()

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'lvs', '0', 'errors', 'real') == 0
    assert chip.get('metric', 'drc', '0', 'errors', 'real') == 0

if __name__ == "__main__":
    test_gcd_checks()
