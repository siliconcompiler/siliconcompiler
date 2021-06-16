import pytest
import os

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

@pytest.fixture
def fp():
    c = Chip()
    c.set('design', 'test')
    c.target('freepdk45')

    fp = Floorplan(c)
    fp.create_die_area(72, 72, core_area=(8, 8, 64, 64))

    n = 4 # pins per side
    width = 10
    depth = 30
    metal = 'm3'

    fp.place_macro('myram', 'RAM', (25, 25), 'N')

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pins(pins[0:n], 'n', width, depth, metal)
    fp.place_pins(pins[n:2*n], 'e', width, depth, metal)
    fp.place_pins(pins[2*n:3*n], 'w', width, depth, metal)
    fp.place_pins(pins[3*n:4*n], 's', width, depth, metal)

    fp.place_blockage(['m1', 'm2'])

    return fp

def test_floorplan_def(fp, tmpdir):
    file = tmpdir.join('output.def')
    fp.write_def(file.strpath)

    test_dir = os.path.dirname(os.path.abspath(__file__))

    with open(test_dir + '/test_floorplan/golden.def', 'r') as golden:
        assert file.read() == golden.read()

def test_floorplan_lef(fp, tmpdir):
    file = tmpdir.join('output.lef')
    fp.write_lef(file.strpath, 'test')

    test_dir = os.path.dirname(os.path.abspath(__file__))

    with open(test_dir + '/test_floorplan/golden.lef', 'r') as golden:
        assert file.read() == golden.read()
