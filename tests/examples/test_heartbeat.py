import pytest
import shutil

import os.path

from siliconcompiler import Project
from siliconcompiler.tools.klayout.screenshot import ScreenshotTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_heartbeat():
    from heartbeat import heartbeat
    heartbeat.main()

    assert os.path.exists('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz')


def test_py_make_check():
    from heartbeat import make
    make.check()


@pytest.mark.timeout(300)
def test_py_make_lint():
    from heartbeat import make
    make.lint()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("pdk", ("freepdk45", "asap7"))
def test_py_make_syn(pdk):
    from heartbeat import make
    make.syn(pdk=pdk)

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')


@pytest.mark.eda
@pytest.mark.timeout(600)
@pytest.mark.parametrize("pdk", (
    pytest.param("freepdk45", marks=pytest.mark.quick),
    "asap7",
))
def test_py_make_asic(pdk):
    from heartbeat import make
    make.asic(pdk=pdk)

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.exists('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_icarus():
    from heartbeat import make
    make.sim(tool="icarus")

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.isfile('build/heartbeat/job0/simulate/0/reports/heartbeat_tb.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_verilator_v():
    from heartbeat import make
    make.sim()

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.isfile('build/heartbeat/job0/simulate/0/reports/heartbeat_tb.vcd')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_make_sim_verilator_cc():
    from heartbeat import make
    make.sim(tb_type='cc')

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
    assert os.path.isfile('build/heartbeat/job0/simulate/0/reports/heartbeat.vcd')


@pytest.mark.eda
@pytest.mark.timeout(1200)
def test_py_make_sim_postpnr():
    from heartbeat import make
    # Auto-runs PnR ('pnr') then the gate-level simulation ('sim').
    make.sim_postpnr(show_vcd=False)

    assert os.path.isfile('build/heartbeat/pnr/heartbeat.pkg.json')
    assert os.path.isfile('build/heartbeat/sim/simulate/0/reports/heartbeat8_tb.vcd')


@pytest.mark.eda
@pytest.mark.timeout(1800)
def test_py_make_power():
    from heartbeat import make
    # Runs the full chain: PnR ('pnr') -> gate-level sim ('sim') -> signoff.
    make.power()

    # Gate-level simulation produced a switching-activity waveform.
    assert os.path.isfile('build/heartbeat/sim/simulate/0/reports/heartbeat8_tb.vcd')

    # Timing signoff annotated the VCD and reported activity coverage.
    annotation = 'build/heartbeat/timingsignoff/signoff/0/reports/activity_annotation.rpt'
    assert os.path.isfile(annotation)

    # Every pin's activity should be annotated from the VCD (a wrong scope would
    # leave pins unannotated). The report prints "unannotated <count>"; the
    # vcd/saif/input lines only appear when non-zero, so match on content rather
    # than a fixed line number.
    with open(annotation) as f:
        counts = [line.split() for line in f.read().splitlines()]
    assert ["unannotated", "0"] in counts


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("vivado") is None, reason="Vivado is not available in CI")
def test_py_make_fpga():
    from heartbeat import make
    make.make()

    assert os.path.isfile('build/heartbeat/job0/bitstream/0/outputs/heartbeat.bit')


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_py_make_screenshot(monkeypatch):
    from heartbeat import make
    make.asic()
    assert os.path.exists('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz')

    org_init = Project._init_run

    def limit_res(self):
        org_init(self)
        ScreenshotTask.find_task(self).set_klayout_resolution(1024, 1024)

    monkeypatch.setattr(Project, '_init_run', limit_res)
    make.screenshot()

    assert os.path.isfile('build/heartbeat/screenshot/merge/0/outputs/heartbeat.png')
