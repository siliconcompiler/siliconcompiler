from siliconcompiler.floorplan import Floorplan
import pytest

def setup_floorplan(fp):
    cell_h = fp.stdcell_height
    fp.create_diearea([(0, 0), (72 * cell_h, 72 * cell_h)], corearea=[(8 * cell_h, 8 * cell_h), (64 * cell_h, 64 * cell_h)])
    die_w, die_h = fp.diearea[1]

    in_pins = ['clk']
    in_pins += [f'req_msg[{i}]' for i in range(32)]
    in_pins += ['req_val', 'reset', 'resp_rdy']

    out_pins = ['req_rdy']
    out_pins += [f'resp_msg[{i}]' for i in range(16)]
    out_pins += ['resp_val']

    metal = fp.chip.get('asic', 'hpinlayer')
    width = 3 * fp.layers[metal]['width']
    height = 1 * fp.layers[metal]['width']

    spacing_we = die_h / (len(in_pins) + 1)
    fp.place_pins(in_pins, 0, spacing_we - height/2, 0, spacing_we, width, height, metal, snap=True) # west

    spacing_ea = die_h / (len(out_pins) + 1)
    fp.place_pins(out_pins, die_w - width, spacing_ea - height/2, 0, spacing_ea, width, height, metal, snap=True) # east

##################################
@pytest.mark.eda
def test_gcd_floorplan(gcd_chip):
    '''Floorplan API test: build the GCD example using a Python-based floorplan
    '''
    # Clear existing dimensions to ensure we use the DEF file
    gcd_chip.set('asic', 'diearea', [])
    gcd_chip.set('asic', 'corearea', [])

    def_file = 'gcd.def'
    fp = Floorplan(gcd_chip)
    setup_floorplan(fp)
    fp.write_def(def_file)
    gcd_chip.set('read', 'def', 'floorplan', '0', def_file)

    gcd_chip.run()

    assert gcd_chip.find_result('gds', step='export') is not None

if __name__ == '__main__':
    from tests.fixtures import gcd_chip
    test_gcd_floorplan(gcd_chip())
