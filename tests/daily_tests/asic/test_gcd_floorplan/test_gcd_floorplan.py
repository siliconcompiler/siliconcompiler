import os
if __name__ != '__main__':
    from tests.fixtures import *
else:
    from tests.utils import *

from siliconcompiler.floorplan import Floorplan

import gcd_floorplan

##################################
def test_gcd_floorplan(gcd_chip):
    '''Floorplan API test: build the GCD example using a Python-based floorplan
    '''

    # Clear existing dimensions to ensure we use the DEF file
    gcd_chip.set('asic', 'diearea', [])
    gcd_chip.set('asic', 'corearea', [])

    def_file = 'gcd.def'
    fp = Floorplan(gcd_chip)
    gcd_floorplan.setup_floorplan(fp)
    fp.write_def(def_file)
    gcd_chip.set('asic', 'def', def_file)

    gcd_chip.run()

    assert gcd_chip.find_result('gds', step='export') is not None

if __name__ == '__main__':
    test_gcd_floorplan(gcd_chip())
