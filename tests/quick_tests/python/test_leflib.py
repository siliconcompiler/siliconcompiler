from siliconcompiler import leflib

import os

test_dir = os.path.dirname(os.path.abspath(__file__))
sc_root = test_dir + '/../../..'

def test_leflib():
    data = leflib.parse(f'{sc_root}/third_party/foundry/skywater/skywater130/pdk/v0_0_2/apr/sky130_fd_sc_hd.tlef')
    assert data['version'] == 5.7

def test_leflib_garbage():
    assert leflib.parse('asdf') is None

def test_leflib_complete():
    import pprint
    pp = pprint.PrettyPrinter()

    data = leflib.parse(f'{sc_root}/third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef/TEST/complete.5.8.lef')
    pp.pprint(data)
        
if __name__ == '__main__':
    test_leflib_complete()
