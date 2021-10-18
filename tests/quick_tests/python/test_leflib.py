from siliconcompiler import leflib

import os

test_dir = os.path.dirname(os.path.abspath(__file__))
sc_root = test_dir + '/../../..'

def test_leflib():
    data = leflib.parse(f'{sc_root}/third_party/pdks/skywater/skywater130/pdk/v0_0_2/apr/sky130_fd_sc_hd.tlef')
    assert data['version'] == 5.7

def test_leflib_garbage():
    assert leflib.parse('asdf') is None

def test_leflib_complete():
    # This file contains nonsense and some things that are technically illegal,
    # but good coverage of what you might see in a LEF. I've left comments where
    # the contents of `data` don't perfectly match the LEF contents, with
    # explanations as to why.
    data = leflib.parse(f'{sc_root}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef/TEST/complete.5.8.lef')

    assert data['version'] == 5.8
    assert data['fixedmask'] == True
    # There's a "USEMINSPACING PIN" statement, but it gets skipped since it's
    # obsolete syntax in 5.8
    assert data['useminspacing'] == {'OBS': 'OFF'}
    # There are two CLEARANCEMEASURE statements, we only take the second one
    assert data['clearancemeasure'] == 'MAXXY'
    assert data['busbitchars'] == '<>'
    assert data['dividerchar'] == ':'
    assert data['units'] == {
        'capacitance': 10.0,
        'current': 10000.0,
        'database': 20000.0,
        'frequency': 10.0,
        'power': 10000.0,
        'resistance': 10000.0,
        'time': 100.0,
        'voltage': 1000.0
    }
    assert data['manufacturinggrid'] == 3.5

    assert len(data['layers']) == 26
    assert data['layers']['POLYS']['type'] == 'MASTERSLICE'

    cut01 = data['layers']['CUT01']
    assert cut01['type'] == 'CUT'
    assert cut01['offset'] == (0.5, 0.6)
    assert cut01['pitch'] == (1.2, 1.3)

    rx = data['layers']['RX']
    assert rx['type'] == 'ROUTING'
    assert rx['pitch'] == 1.8
    assert rx['offset'] == 0.9
    assert rx['width'] == 1
    assert rx['direction'] == 'HORIZONTAL'

    assert data['maxviastack'] == { 'value': 4, 'range': {'bottom': 'm1', 'top': 'm7'}}
    assert data

    # 11 viarules defined, but two are skipped because they are "turn-vias"
    # (obsolete in 5.8)
    assert len(data['viarules']) == 9

    vialist12 = data['viarules']['VIALIST12']
    assert len(vialist12['layers']) == 2
    assert vialist12['layers'][0] == {
        'name': 'M1',
        'direction': 'VERTICAL',
        'width': {'min': 9.0, 'max': 9.6}
    }
    assert vialist12['layers'][1] == {
        'name': 'M2',
        'direction': 'HORIZONTAL',
        'width': {'min': 3.0, 'max': 3.0}
    }
    assert vialist12['vias'] == ['VIACENTER12']

    via12 = data['viarules']['via12']
    assert via12['generate'] == True
    assert via12['default'] == True

    assert len(via12['layers']) == 3
    assert via12['layers'][0] == {
        'name': 'm1',
        'enclosure': {'overhang1': 0.03, 'overhang2': 0.01}
    }
    assert via12['layers'][1] == {
        'name': 'm2',
        'enclosure': {'overhang1': 0.05, 'overhang2': 0.01}
    }
    assert via12['layers'][2] == {
        'name': 'cut12',
        'spacing': {'x': 0.4, 'y': 0.4},
        'rect': (-0.1, -0.1, 0.1, 0.1),
        'resistance': 20
    }

    assert len(data['sites']) == 10
    cover = data['sites']['COVER']
    assert cover['class'] == 'PAD'
    assert cover['symmetry'] == ['R90']
    assert cover['size'] == {'width': 10, 'height': 10}

    assert len(data['macros']) == 14
    chk3a = data['macros']['CHK3A']
    assert chk3a['size'] == {'width': 10.8, 'height': 28.8}
    assert len(chk3a['pins']) == 7
    vdd = chk3a['pins']['VDD']
    assert len(vdd['ports']) == 2
    port = vdd['ports'][1]
    assert port['class'] == 'NONE'
    assert len(port['layer_geometries']) == 1
    geo = port['layer_geometries'][0]
    assert geo['layer'] == 'M1'
    assert geo['shapes'] == [{
        'rect': (-0.9, 21, 9.9, 24),
        'mask': 0,
        'iterate': {
            'num_x': 1,
            'num_y': 2,
            'step_x': 1,
            'step_y': 1
        }
    }]

    assert len(chk3a['obs']) == 1
    obs = chk3a['obs'][0][0]
    assert obs['layer'] == 'M1'
    assert obs['spacing'] == 5.6
    assert len(obs['shapes']) == 10
    assert obs['shapes'][0] == {
        'rect': (6.6, -0.6, 9.6, 0.6),
        'mask': 0
    }

if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter()
    data = leflib.parse(f'{sc_root}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef/TEST/complete.5.8.lef')
    pp.pprint(data)
