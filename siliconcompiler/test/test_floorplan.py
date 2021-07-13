import pytest
import os

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan, snap

def make_fp():
    test_dir = os.path.dirname(os.path.abspath(__file__))

    c = Chip()
    c.set('design', 'test')
    c.target('freepdk45')
    c.add('asic', 'macrolib', 'ram')
    c.add('macro', 'ram', 'lef', test_dir + '/test_floorplan/ram.lef')
    c.set('macro', 'ram', 'cells', 'ram', 'RAM')

    fp = Floorplan(c)
    cell_w = fp.std_cell_width
    cell_h = fp.std_cell_height
    fp.create_die_area(72 * cell_h, 72 * cell_h, core_area=(8 * cell_h, 8 * cell_h, 64 * cell_h, 64 * cell_h))

    n = 4 # pins per side
    metal = 'm3'
    width = 10 * fp.layers[metal]['width']
    depth = 30 * fp.layers[metal]['width']

    fp.place_macros([('myram', 'ram')], (25 * cell_w, 25 * cell_h), 0, 'h', 'N')

    die_w, die_h = fp.die_area
    spacing_x = die_w / (n + 1)
    pitch_x = snap(spacing_x, fp.layers[metal]['xpitch'])
    offset_x = fp.snap_to_x_track(spacing_x, metal)

    spacing_y = die_h / (n + 1)
    pitch_y = snap(spacing_y, fp.layers[metal]['ypitch'])
    offset_y = fp.snap_to_y_track(spacing_y, metal)

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pins(pins[0:n], offset_x, pitch_x, 'n', width, depth, metal)
    fp.place_pins(pins[n:2*n], offset_y, pitch_y, 'e', width, depth, metal)
    fp.place_pins(pins[2*n:3*n], offset_y, pitch_y, 'w', width, depth, metal)
    fp.place_pins(pins[3*n:4*n], offset_x, pitch_x, 's', width, depth, metal)

    fp.place_blockage(['m1', 'm2'])

    return fp

@pytest.fixture
def fp():
    return make_fp()

def test_floorplan_def(fp, tmpdir):
    file = tmpdir.join('output.def')
    fp.write_def(file.strpath)

    test_dir = os.path.dirname(os.path.abspath(__file__))

    with open(test_dir + '/test_floorplan/golden.def', 'r') as golden:
        assert file.read() == golden.read()

def test_floorplan_lef(fp, tmpdir):
    file = tmpdir.join('output.lef')
    fp.write_lef(file.strpath)

    test_dir = os.path.dirname(os.path.abspath(__file__))

    with open(test_dir + '/test_floorplan/golden.lef', 'r') as golden:
        assert file.read() == golden.read()

def test_padring():
    ''' Replicates Yosys padring from here:
    https://github.com/YosysHQ/padring/tree/master/example

    TODO: actually check the output (it will probably change a bit, so for now
    running this file will just manually validate it)
    '''

    test_dir = os.path.dirname(os.path.abspath(__file__))

    chip = Chip()
    chip.set('design', 'mypadring')
    chip.target('freepdk45')

    macro = 'io'
    chip.add('asic', 'macrolib', macro)
    chip.set('macro', macro, 'lef', f'{test_dir}/test_floorplan/iocells.lef')
    chip.set('macro', macro, 'cells', 'gpio', 'IOPAD')
    chip.set('macro', macro, 'cells', 'pwr', 'PWRPAD')
    chip.set('macro', macro, 'cells', 'corner', 'CORNER')
    chip.set('macro', macro, 'cells', 'fill1',  'FILLER01')
    chip.set('macro', macro, 'cells', 'fill2',  'FILLER02')
    chip.set('macro', macro, 'cells', 'fill5',  'FILLER05')
    chip.set('macro', macro, 'cells', 'fill10', 'FILLER10')
    chip.set('macro', macro, 'cells', 'fill25', 'FILLER25')
    chip.set('macro', macro, 'cells', 'fill50', 'FILLER50')

    macro = 'sram_32x2048_1rw'
    chip.add('asic', 'macrolib', macro)
    chip.set('macro', macro, 'lef', f'{test_dir}/test_floorplan/{macro}.lef')
    chip.set('macro', macro, 'cells', 'ram', 'sram_32x2048_1rw')

    fp = Floorplan(chip, db_units=1000)

    die_w = 1200
    die_h = 1200

    fp.create_die_area(die_w, die_h)

    io_h = fp.available_cells['corner'].height

    # Distance between corner cells on each side
    io_dist_hori = die_w - 2 * io_h
    io_dist_vert = die_h - 2 * io_h

    pad_w = fp.available_cells['gpio'].width
    spacing = (io_dist_hori - 8 * pad_w) // 9

    # north
    start = io_h + spacing
    y = die_h - io_h
    fp.place_macros([(f'GPIO[{i}]', 'gpio') for i in range(4)], (start, y), spacing, 'H', 'N')
    fp.place_macros([(f'GPIO[{i}]', 'gpio') for i in range(4, 8)], (start + 4 * (spacing + pad_w), y), spacing, 'H', 'FS')

    # south
    fp.place_macros([('CLK', 'gpio'), ('RESET', 'gpio'), ('MISO', 'gpio'), ('MOSI', 'gpio'), ('SCK', 'gpio'), ('SPI_CS_N', 'gpio')], (start, 0), spacing, 'H', 'N')
    fp.place_macros([('UART_TX', 'gpio'), ('UART_RX', 'gpio')], (start + 6 * (spacing + pad_w), 0), spacing, 'H', 'FN')

    # east
    assert pad_w == fp.available_cells['pwr'].width, "making bad assumption about pads being same width..."

    spacing = (io_dist_vert - 6 * pad_w) // 6
    x = die_w - io_h
    start = io_h + spacing
    fp.place_macros([('PWM_1', 'gpio'), ('PWM_2', 'gpio')], (x, start), spacing, 'V', 'W')
    fp.place_macros([('VDD_1', 'pwr'), ('GND_1', 'pwr')], (x, start + 2 * (spacing + pad_w)), 0, 'V', 'W')
    fp.place_macros([('PWM_3', 'gpio'), ('PWM_4', 'gpio')], (x, start + 3 * (spacing + pad_w) + pad_w), spacing, 'V', 'FE')

    # west
    fp.place_macros([('DAC_0', 'gpio'), ('DAC_1', 'gpio')], (0, start), spacing, 'V', 'E')
    fp.place_macros([('VDD_2', 'pwr'), ('GND_2', 'pwr')], (0, start + 2 * (spacing + pad_w)), 0, 'V', 'E')
    fp.place_macros([('DAC_2', 'gpio'), ('DAC_3', 'gpio')], (0, start + 3 * (spacing + pad_w) + pad_w), spacing, 'V', 'W')

    fp.place_macros([('CORNER_1', 'corner')], (die_w - io_h, 0), 0, 'V', 'W') # SE
    fp.place_macros([('CORNER_2', 'corner')], (0, 0), 0, 'H', 'N') # SW
    fp.place_macros([('CORNER_3', 'corner')], (die_w - io_h, die_h - io_h), 0,  'V', 'S') # NE
    fp.place_macros([('CORNER_4', 'corner')], (0, die_h - io_h), 0, 'H', 'E') # NW

    fp.place_macros([('ram1', 'ram'), ('ram2', 'ram')], (die_w / 2, die_h / 2), 50, 'H', 'N')

    io_fill_cells = ['fill1', 'fill2', 'fill5', 'fill10', 'fill25', 'fill50']
    fp.fill_io_region([(0, 0), (die_w, io_h)], io_fill_cells, 'N')
    fp.fill_io_region([(0, 0), (io_h, die_h)], io_fill_cells, 'W')
    fp.fill_io_region([(die_w - io_h, 0), (die_w, die_h)], io_fill_cells, 'E')
    fp.fill_io_region([(0, die_h - io_h), (die_w, die_h)], io_fill_cells, 'S')

    fp.configure_net('VDD', 'VDD', 'POWER')
    fp.configure_net('VSS', 'VSS', 'GROUND')
    fp.place_wires(['VDD'] * 11, (100, 100), 100, 'h', 'm3', 10, 1000, 'STRIPE')
    fp.place_wires(['VSS'] * 11, (100, 100), 100, 'v', 'm4', 10, 1000, 'STRIPE')

    fp.write_def('padring.def')

if __name__ == "__main__":
    import py

    #test_floorplan_def(make_fp(), py.path.local('.'))
    #test_floorplan_lef(make_fp(), py.path.local('.'))
    test_padring()
