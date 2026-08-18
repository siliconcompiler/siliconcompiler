import pytest

import os.path

from siliconcompiler.demos import asic_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    proj = asic_demo.ASICDemo()
    assert proj.run()
    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz')
    assert proj.history("job0").get('metric', 'holdslack', step='write.views', index='0') >= 0.0
    assert proj.history("job0").get('metric', 'holdslack', step='write.views', index='0') < 10.0
    assert proj.history("job0").get('metric', 'setupslack', step='write.views', index='0') >= 0.0
    assert proj.history("job0").get('metric', 'setupslack', step='write.views', index='0') < 10.0


def test_asic_demo_pdk():
    ''' The self-test target must build against Skywater130, and only Skywater130 '''
    proj = asic_demo.ASICDemo()

    assert proj.get("asic", "pdk") == "skywater130"
    assert proj._has_library("skywater130") is True

    assert proj.get("asic", "mainlib") == "sky130hd"
    assert proj._has_library("sky130hd") is True

    # Loading the demo must not drag in any of the other demo PDKs.
    assert set(proj.getkeys("library")) == {"heartbeat", "sky130hd", "skywater130"}


def test_asic_demo_design():
    ''' The self-test target builds the 8-bit heartbeat counter '''
    proj = asic_demo.ASICDemo()

    assert proj.get("option", "design") == "heartbeat"
    assert proj.get("option", "fileset") == ["rtl", "sdc"]
    assert proj.get("option", "flow") == "asicflow-verilog"
