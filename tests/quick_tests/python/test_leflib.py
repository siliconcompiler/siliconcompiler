from siliconcompiler import leflib

def test_leflib():
    assert leflib.parse('/home/noah/zeroasic/siliconcompiler/third_party/foundry/skywater/skywater130/pdk/v0_0_2/apr/sky130_fd_sc_hd.tlef') == 'SUCCESS'
