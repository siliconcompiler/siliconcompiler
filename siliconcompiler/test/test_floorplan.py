import pytest
import os

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

@pytest.fixture
def fp():
    test_dir = os.path.dirname(os.path.abspath(__file__))

    c = Chip()
    c.set('design', 'test')
    c.target('freepdk45')
    c.add('asic', 'macrolib', 'ram')
    c.add('macro', 'ram', 'lef', test_dir + '/test_floorplan/ram.lef')
    c.set('macro', 'ram', 'cells', 'ram', 'RAM')

    fp = Floorplan(c)
    fp.create_die_area(72, 72, core_area=(8, 8, 64, 64))

    n = 4 # pins per side
    width = 10
    depth = 30
    metal = 'm3'

    fp.place_macro('myram', 'ram', (25, 25), 'N')

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

    fp.create_die_area(die_w, die_h, units='absolute')

    io_h = fp.available_cells['corner'].height

    # Distance between corner cells on each side
    io_dist_hori = die_w - 2 * io_h
    io_dist_vert = die_h - 2 * io_h

    # north
    pad_w = fp.available_cells['gpio'].width
    spacing = (io_dist_hori - 8 * pad_w) // 9
    fp.place_macros([(f'GPIO[{i}]', 'gpio') for i in range(4)], (io_h + spacing, die_h - io_h), 'S', 'H', spacing=spacing)
    fp.place_macros([(f'GPIO[{i}]', 'gpio') for i in range(4, 8)], (die_w // 2 + spacing // 2, die_h - io_h), 'FS', 'H', spacing=spacing)

    # south
    spacing = (io_dist_hori - 8 * pad_w) // 9
    fp.place_macros([('CLK', 'gpio'), ('RESET', 'gpio'), ('MISO', 'gpio'), ('MOSI', 'gpio'), ('SCK', 'gpio'), ('SPI_CS_N', 'gpio')], (io_h + spacing, 0), 'N', 'H', spacing=spacing)
    start = io_h + 7 * spacing + 6 * pad_w
    fp.place_macros([('UART_TX', 'gpio'), ('UART_RX', 'gpio')], (start, 0), 'FN', 'H', spacing=spacing)

    # east
    pad_w = fp.available_cells['pwr'].width
    fp.place_macros_spaced([('PWM_1', 'gpio'), ('PWM_2', 'gpio')], (die_w - io_h, io_h), 'W', 'V', die_h/2 - pad_w - io_h)
    fp.place_macros([('VDD_1', 'pwr'), ('GND_1', 'pwr')], (die_w - io_h, die_h/2 - pad_w), 'W', 'V')
    fp.place_macros_spaced([('PWM_3', 'gpio'), ('PWM_4', 'gpio')], (die_w - io_h, die_h/2 + pad_w), 'FE', 'V', die_h/2 - pad_w - io_h)

    # west
    fp.place_macros_spaced([('DAC_0', 'gpio'), ('DAC_1', 'gpio')], (0, io_h), 'E', 'V', die_h/2 - pad_w - io_h)
    fp.place_macros([('VDD_2', 'pwr'), ('GND_2', 'pwr')], (0, die_h/2 - pad_w), 'E', 'V')
    fp.place_macros_spaced([('DAC_2', 'gpio'), ('DAC_3', 'gpio')], (0, die_h/2 + pad_w), 'W', 'V', die_h/2 - pad_w - io_h)

    fp.place_macros([('CORNER_1', 'corner')], (die_w - io_h, 0), 'W', 'V') # SE
    fp.place_macros([('CORNER_2', 'corner')], (0, 0), 'N', 'H') # SW
    fp.place_macros([('CORNER_3', 'corner')], (die_w - io_h, die_h - io_h), 'S', 'V') # NE
    fp.place_macros([('CORNER_4', 'corner')], (0, die_h - io_h), 'E', 'H') # NW

    fp.place_macros([('ram1', 'ram'), ('ram2', 'ram')], (die_w / 2, die_h / 2), 'N', 'H', spacing=50)

    io_fill_cells = ['fill1', 'fill2', 'fill5', 'fill10', 'fill25', 'fill50']
    fp.fill_io_region([(0, 0), (die_w, io_h)], io_fill_cells, 'N')
    fp.fill_io_region([(0, 0), (io_h, die_h)], io_fill_cells, 'W')
    fp.fill_io_region([(die_w - io_h, 0), (die_w, die_h)], io_fill_cells, 'E')
    fp.fill_io_region([(0, die_h - io_h), (die_w, die_h)], io_fill_cells, 'S')

    fp.configure_net('VDD', 'VDD', 'POWER')
    fp.configure_net('VSS', 'VSS', 'GROUND')
    fp.place_wires(['VDD'] * 11, 'm3', 10, 1000, 'STRIPE', (100, 100), 100, 'h')
    fp.place_wires(['VSS'] * 11, 'm4', 10, 1000, 'STRIPE', (100, 100), 100, 'v')

    fp.write_def('padring.def')

if __name__ == "__main__":
    test_padring()
