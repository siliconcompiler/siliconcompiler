import pytest
import os

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

def make_fp():
    test_dir = os.path.dirname(os.path.abspath(__file__))

    c = Chip(loglevel='INFO')
    c.set('design', 'test')
    c.target('freepdk45_asicflow')
    lib = 'ram'
    c.add('asic', 'macrolib', lib)
    c.set('library', lib, 'type', 'component')
    c.add('library', lib, 'lef', test_dir + '/test_floorplan/ram.lef')

    fp = Floorplan(c)
    cell_w = fp.std_cell_width
    cell_h = fp.std_cell_height
    fp.create_die_area([(0, 0), (72 * cell_h, 72 * cell_h)], core_area=[(8 * cell_h, 8 * cell_h), (64 * cell_h, 64 * cell_h)])

    n = 4 # pins per side

    hmetal = c.get('asic', 'hpinlayer')
    vmetal = c.get('asic', 'vpinlayer')
    hwidth = 30 * fp.layers[hmetal]['width']
    hheight = 10 * fp.layers[hmetal]['width']
    vwidth = 10 * fp.layers[vmetal]['width']
    vheight = 30 * fp.layers[vmetal]['width']

    fp.place_macros([('myram', 'RAM')], 25 * cell_w, 25 * cell_h, 0, 0, 'N')

    die_w, die_h = fp.die_area[1]

    spacing_x = die_w / (n + 1)
    spacing_y = die_h / (n + 1)

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pins(pins[0:n], spacing_x - vwidth/2, die_h - vheight, spacing_x, 0, vwidth, vheight, vmetal, snap=True) # n
    fp.place_pins(pins[3*n:4*n], spacing_x - vwidth/2, 0, spacing_x, 0, vwidth, vheight, vmetal, snap=True) # s
    fp.place_pins(pins[n:2*n], die_w - hwidth, spacing_y - hheight/2, 0, spacing_y, hwidth, hheight, hmetal, snap=True) # e
    fp.place_pins(pins[2*n:3*n], 0, spacing_y - hheight/2, 0, spacing_y, hwidth, hheight, hmetal, snap=True) # w

    fp.place_obs(['m1', 'm2'])

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

    chip = Chip(loglevel='INFO')
    chip.set('design', 'mypadring')
    chip.target('freepdk45_asicflow')

    macro = 'io'
    chip.add('asic', 'macrolib', macro)
    chip.set('library', macro, 'lef', f'{test_dir}/test_floorplan/iocells.lef')
    chip.set('library', macro, 'cells', 'IOPAD', 'IOPAD')

    macro = 'sram_32x2048_1rw'
    chip.add('asic', 'macrolib', macro)
    chip.set('library', macro, 'lef', f'{test_dir}/test_floorplan/{macro}.lef')
    chip.set('library', macro, 'cells', 'ram', 'sram_32x2048_1rw')

    fp = Floorplan(chip, db_units=1000)

    die_w = 1200
    die_h = 1200

    fp.create_die_area([(0, 0), (die_w, die_h)])

    io_h = fp.available_cells['CORNER'].height

    # Distance between CORNER cells on each side
    io_dist_hori = die_w - 2 * io_h
    io_dist_vert = die_h - 2 * io_h

    pad_w = fp.available_cells['IOPAD'].width
    spacing = (io_dist_hori - 8 * pad_w) // 9

    # north
    start = fp.snap(io_h + spacing, 1)
    y = die_h - io_h
    pitch = fp.snap(spacing + pad_w, 1)
    fp.place_macros([(f'IOPAD[{i}]', 'IOPAD') for i in range(4)], start, y, pitch, 0, 'N', snap=False)
    fp.place_macros([(f'IOPAD[{i}]', 'IOPAD') for i in range(4, 8)], start + 4 * pitch, y, pitch, 0, 'FS', snap=False)

    # south
    fp.place_macros([('CLK', 'IOPAD'), ('RESET', 'IOPAD'), ('MISO', 'IOPAD'), ('MOSI', 'IOPAD'), ('SCK', 'IOPAD'), ('SPI_CS_N', 'IOPAD')], start, 0, spacing + pad_w, 0, 'N', snap=False)
    fp.place_macros([('UART_TX', 'IOPAD'), ('UART_RX', 'IOPAD')], start + 6 * pitch, 0, pitch, 0, 'FN', snap=False)

    # east
    assert pad_w == fp.available_cells['PWRPAD'].width, "making bad assumption about pads being same width..."

    spacing = (io_dist_vert - 6 * pad_w) // 6
    x = die_w - io_h
    start = fp.snap(io_h + spacing, 1)
    pitch = fp.snap(spacing + pad_w, 1)
    fp.place_macros([('PWM_1', 'IOPAD'), ('PWM_2', 'IOPAD')], x, start, 0, pitch, 'W', snap=False)
    fp.place_macros([('VDD_1', 'PWRPAD'), ('GND_1', 'PWRPAD')], x, start + 2 * pitch, 0, pad_w, 'W', snap=False)
    fp.place_macros([('PWM_3', 'IOPAD'), ('PWM_4', 'IOPAD')], x, start + 3 * pitch + pad_w, 0, pitch, 'FE', snap=False)

    # west
    fp.place_macros([('DAC_0', 'IOPAD'), ('DAC_1', 'IOPAD')], 0, start, 0, pitch, 'E', snap=False)
    fp.place_macros([('VDD_2', 'PWRPAD'), ('GND_2', 'PWRPAD')], 0, start + 2 * pitch, 0, pad_w, 'E', snap=False)
    fp.place_macros([('DAC_2', 'IOPAD'), ('DAC_3', 'IOPAD')], 0, start + 3 * pitch + pad_w, 0, pitch, 'W', snap=False)

    fp.place_macros([('CORNER_1', 'CORNER')], die_w - io_h, 0, 0, 0, 'W', snap=False) # SE
    fp.place_macros([('CORNER_2', 'CORNER')], 0, 0, 0, 0, 'N', snap=False) # SW
    fp.place_macros([('CORNER_3', 'CORNER')], die_w - io_h, die_h - io_h, 0, 0, 'S', snap=False) # NE
    fp.place_macros([('CORNER_4', 'CORNER')], 0, die_h - io_h, 0, 0, 'E', snap=False) # NW

    ram_w = fp.available_cells['sram_32x2048_1rw'].width
    fp.place_macros([('ram1', 'sram_32x2048_1rw'), ('ram2', 'sram_32x2048_1rw')], die_w / 2, die_h / 2, 50 + ram_w, 0, 'N', snap=True)

    io_fill_cells = ['FILLER01', 'FILLER02', 'FILLER05', 'FILLER10', 'FILLER25', 'FILLER50']
    fp.fill_io_region([(0, 0), (die_w, io_h)], io_fill_cells, 'N')
    fp.fill_io_region([(0, 0), (io_h, die_h)], io_fill_cells, 'W')
    fp.fill_io_region([(die_w - io_h, 0), (die_w, die_h)], io_fill_cells, 'E')
    fp.fill_io_region([(0, die_h - io_h), (die_w, die_h)], io_fill_cells, 'S')

    fp.configure_net('VDD', 'VDD', 'POWER')
    fp.configure_net('VSS', 'VSS', 'GROUND')

    hlayer = chip.get('asic', 'hpinlayer')
    vlayer = chip.get('asic', 'vpinlayer')

    fp.place_wires(['VDD'] * 11, 100, 100, 0, 100, 1000, 10, hlayer, 'STRIPE', snap=True)
    fp.place_wires(['VSS'] * 11, 100, 100, 100, 0, 10, 1000, vlayer, 'STRIPE', snap=True)

    fp.write_def('padring.def')

if __name__ == "__main__":
    import py

    #test_floorplan_def(make_fp(), py.path.local('.'))
    #test_floorplan_lef(make_fp(), py.path.local('.'))
    test_padring()
