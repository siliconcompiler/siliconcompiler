from siliconcompiler import leflib

import os

tests_dir = os.path.dirname(__file__)

def test_basic():
    d = leflib.parse(f'{tests_dir}/test_leflib/test.lef')
    assert d.version == 5.8
    assert d.units['db'] == 1000
    assert 'test' in d.macros
    assert d.macros['test']['width'] == 5
    assert d.macros['test']['height'] == 5

def test_complete():
    d = leflib.parse(f'{tests_dir}/../../../third_party/lef/TEST/complete.5.8.lef')
    assert d.version == 5.8
    assert d.mfg_grid == 3.5

    print(d.layers)
    print(d.units)
    print(d.macros)

if __name__ == '__main__':
    test_complete()
