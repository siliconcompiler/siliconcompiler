import pytest
import os
import re

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

def _fp(datadir):
    c = Chip('test')
    c.load_target('freepdk45_demo')
    stackup = '10M'
    lib = 'ram'
    c.add('asic', 'macrolib', lib)
    c.set('library', lib, 'type', 'component')
    c.add('library', lib, 'lef', stackup, os.path.join(datadir, 'ram.lef'))

    fp = Floorplan(c)
    cell_w = fp.stdcell_width
    cell_h = fp.stdcell_height
    fp.create_diearea([(0, 0), (72 * cell_h, 72 * cell_h)], corearea=[(8 * cell_h, 8 * cell_h), (64 * cell_h, 64 * cell_h)])

    n = 4 # pins per side

    hmetal = c.get('asic', 'hpinlayer')
    vmetal = c.get('asic', 'vpinlayer')
    hwidth = 30 * fp.layers[hmetal]['width']
    hheight = 10 * fp.layers[hmetal]['width']
    vwidth = 10 * fp.layers[vmetal]['width']
    vheight = 30 * fp.layers[vmetal]['width']

    fp.place_macros([('myram', 'RAM')], 25 * cell_w, 25 * cell_h, 0, 0, 'N')

    die_w, die_h = fp.diearea[1]

    spacing_x = die_w / (n + 1)
    spacing_y = die_h / (n + 1)

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pins(pins[0:n], spacing_x - vwidth/2, die_h - vheight, spacing_x, 0, vwidth, vheight, vmetal, snap=True) # n
    fp.place_pins(pins[3*n:4*n], spacing_x - vwidth/2, 0, spacing_x, 0, vwidth, vheight, vmetal, snap=True) # s
    fp.place_pins(pins[n:2*n], die_w - hwidth, spacing_y - hheight/2, 0, spacing_y, hwidth, hheight, hmetal, snap=True) # e
    fp.place_pins(pins[2*n:3*n], 0, spacing_y - hheight/2, 0, spacing_y, hwidth, hheight, hmetal, snap=True) # w

    fp.place_blockage(10, 10, 10, 10)
    fp.place_blockage(10, 10, 10, 10, 'm1')

    fp.place_obstruction(0, 0, die_w, die_h, ['m1', 'm2'])

    return fp

@pytest.fixture
def fp(datadir):
    return _fp(datadir)

def test_floorplan_def(fp, datadir):
    output_path = 'output.def'
    fp.write_def(output_path)

    with open(os.path.join(datadir, 'golden.def'), 'r') as golden, \
         open(output_path, 'r') as result:
        assert result.read() == golden.read()

def test_floorplan_lef(fp, datadir):
    output_path = 'output.lef'
    fp.write_lef(output_path)

    with open(os.path.join(datadir, 'golden.lef'), 'r') as golden, \
         open(output_path, 'r') as result:
        assert result.read() == golden.read()

def test_padring(datadir):
    ''' Replicates Yosys padring from here:
    https://github.com/YosysHQ/padring/tree/master/example

    TODO: actually check the output (it will probably change a bit, so for now
    running this file will just manually validate it)
    '''

    test_dir = os.path.dirname(os.path.abspath(__file__))

    chip = Chip('mypadring')
    chip.load_target('freepdk45_demo')

    macro = 'io'
    stackup = '10M'
    chip.add('asic', 'macrolib', macro)
    chip.set('library', macro, 'lef', stackup, os.path.join(datadir, 'iocells.lef'))
    chip.set('library', macro, 'cells', 'IOPAD', 'IOPAD')

    macro = 'sram_32x2048_1rw'
    chip.add('asic', 'macrolib', macro)
    chip.set('library', macro, 'lef', stackup, os.path.join(datadir, f'{macro}.lef'))
    chip.set('library', macro, 'cells', 'ram', 'sram_32x2048_1rw')

    fp = Floorplan(chip)

    die_w = 1200
    die_h = 1200

    fp.create_diearea([(0, 0), (die_w, die_h)])

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
    fp.fill_io_region([(0, 0), (die_w, io_h)], io_fill_cells, 'N', 'h')
    fp.fill_io_region([(0, 0), (io_h, die_h)], io_fill_cells, 'W', 'v')
    fp.fill_io_region([(die_w - io_h, 0), (die_w, die_h)], io_fill_cells, 'E', 'v')
    fp.fill_io_region([(0, die_h - io_h), (die_w, die_h)], io_fill_cells, 'S', 'h')

    fp.add_net('VDD', 'VDD', 'POWER')
    fp.add_net('VSS', 'VSS', 'GROUND')

    hlayer = chip.get('asic', 'hpinlayer')
    vlayer = chip.get('asic', 'vpinlayer')

    fp.place_wires(['VDD'] * 11, 100, 100, 0, 100, 1000, 10, hlayer, 'STRIPE', snap=True)
    fp.place_wires(['VSS'] * 11, 100, 100, 100, 0, 10, 1000, vlayer, 'STRIPE', snap=True)

    fp.write_def('padring.def')

def test_vias_at_intersection():
    c = Chip('test')
    c.load_target('skywater130_demo')

    fp = Floorplan(c)
    fp.create_diearea([(0, 0), (100, 100)])

    fp.add_net('vdd', [], 'power')
    fp.add_net('vss', [], 'ground')
    # fp.add_viarule('via4_1600x1600', 'M4M5_PR', (0.8, 0.8), ('m4', 'via4', 'm5'), (.8, .8), (.04,  .04, .04, .04))

    fp.place_wires(['vdd'] * 2, 0, 0, 10, 0, 1.6, 100, 'm5', 'stripe')
    fp.place_wires(['vdd'] * 2, 0, 0, 0, 10, 100, 1.6, 'm2', 'stripe')

    fp.insert_vias()

    fp.write_def('test.def')

def test_place_vias(datadir):
    c = Chip('test')
    c.load_target('freepdk45_demo')
    stackup = '10M'
    lib = 'ram'
    c.add('asic', 'macrolib', lib)
    c.set('library', lib, 'type', 'component')
    c.add('library', lib, 'lef', stackup, os.path.join(datadir, 'ram.lef'))

    fp = Floorplan(c)

    fp.create_diearea([(0, 0), (1000, 1000)])

    shapes = [
        ((-10, -10), (-2.5, -2.5)),
        ((2.5, -10), (10, -2.5)),
        ((-10, 2.5), (-2.5, 10)),
        ((2.5, 2.5), (10, 10))
    ]
    fp.add_via('myvia', 'm1', shapes, 'via1', shapes, 'm2', shapes)

    fp.add_net('vdd', [], use='power')

    fp.place_vias(['vdd'] * 5, 50, 50, 25, 0, 'myvia')

    outfile = 'test_place_vias.def'
    fp.write_def(outfile)

    with open(outfile, 'r') as resultfile:
        result = resultfile.read()
        specnets = re.search(r'SPECIALNETS (\d+) ;\n(.*)END SPECIALNETS', result, re.MULTILINE|re.DOTALL)
        vias = re.search(r'VIAS (\d+) ;\n(.*)END VIAS', result, re.MULTILINE|re.DOTALL)

    expected_specnets = '''
    - vdd  + USE power
        + ROUTED
        metal1 0 + SHAPE STRIPE ( 100000 100000 ) myvia
        NEW
        metal1 0 + SHAPE STRIPE ( 150000 100000 ) myvia
        NEW
        metal1 0 + SHAPE STRIPE ( 200000 100000 ) myvia
        NEW
        metal1 0 + SHAPE STRIPE ( 250000 100000 ) myvia
        NEW
        metal1 0 + SHAPE STRIPE ( 300000 100000 ) myvia ;
    '''.split()

    assert specnets.group(1) == '1'
    assert specnets.group(2).split() == expected_specnets

    expected_vias = '''
        - myvia
      + RECT metal1 ( -20000 -20000 ) ( -5000 -5000 )
      + RECT metal1 ( 5000 -20000 ) ( 20000 -5000 )
      + RECT metal1 ( -20000 5000 ) ( -5000 20000 )
      + RECT metal1 ( 5000 5000 ) ( 20000 20000 )
      + RECT via1 ( -20000 -20000 ) ( -5000 -5000 )
      + RECT via1 ( 5000 -20000 ) ( 20000 -5000 )
      + RECT via1 ( -20000 5000 ) ( -5000 20000 )
      + RECT via1 ( 5000 5000 ) ( 20000 20000 )
      + RECT metal2 ( -20000 -20000 ) ( -5000 -5000 )
      + RECT metal2 ( 5000 -20000 ) ( 20000 -5000 )
      + RECT metal2 ( -20000 5000 ) ( -5000 20000 )
      + RECT metal2 ( 5000 5000 ) ( 20000 20000 ) ;
    '''.split()

    assert vias.group(1) == '1'
    assert vias.group(2).split() == expected_vias

if __name__ == "__main__":
    from tests.fixtures import datadir

    mydatadir = datadir(__file__)
    # test_floorplan_def(_fp(mydatadir), mydatadir)
    # test_floorplan_lef(_fp(mydatadir), mydatadir)
    # test_padring(mydatadir)
    # test_vias_at_intersection()
    test_place_vias(mydatadir)
