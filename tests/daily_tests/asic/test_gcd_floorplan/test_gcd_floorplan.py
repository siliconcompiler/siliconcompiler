import os
from tests.fixtures import test_wrapper

import siliconcompiler
from siliconcompiler.floorplan import Floorplan

import gcd_floorplan

##################################
def test_gcd_floorplan():
    '''Floorplan API test: build the GCD example using a Python-based floorplan
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.abspath(__file__)
    print(gcd_ex_dir)
    gcd_ex_dir = gcd_ex_dir[:gcd_ex_dir.rfind('/tests/daily_tests/asic/test_gcd_floorplan')] + '/examples/gcd/'
    print(gcd_ex_dir)
    
    # Inserting value into configuration
    chip.set('design', 'gcd')
    chip.target("freepdk45_asicflow")
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('asic', 'diesize', "0 0 100.13 100.8")
    chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
    chip.set('quiet', 'true')
    chip.set('relax', 'true')

    def_file = 'gcd.def'
    fp = Floorplan(chip)
    gcd_floorplan.setup_floorplan(fp)
    fp.write_def(def_file)
    chip.set('asic', 'def', def_file)

    # Run the chip's build process synchronously.
    chip.run()

    assert os.path.isfile('build/gcd/job0/export0/outputs/gcd.gds')

if __name__ == '__main__':
    test_gcd_floorplan()
