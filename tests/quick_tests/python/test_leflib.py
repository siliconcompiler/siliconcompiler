from siliconcompiler import leflib

def test_leflib():
    data = leflib.parse(b'/home/noah/zeroasic/siliconcompiler/third_party/foundry/skywater/skywater130/pdk/v0_0_2/apr/sky130_fd_sc_hd.tlef')
    assert data['version'] == 5.7

def test_leflib_garbage():
    assert leflib.parse(b'asdf') is None
