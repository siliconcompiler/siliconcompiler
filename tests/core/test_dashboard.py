import siliconcompiler
from siliconcompiler.targets import freepdk45_demo


def test_dashboard(unused_tcp_port, wait_for_port):
    chip = siliconcompiler.Chip('dashboard')
    chip.use(freepdk45_demo)

    dashboard = chip.dashboard(wait=False, port=unused_tcp_port)

    wait_for_port(unused_tcp_port)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
