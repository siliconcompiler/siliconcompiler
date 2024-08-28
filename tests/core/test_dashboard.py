import siliconcompiler
from siliconcompiler.targets import freepdk45_demo


def test_dashboard(wait_for_port):
    chip = siliconcompiler.Chip('dashboard')
    chip.use(freepdk45_demo)

    dashboard = chip._dashboard(wait=False)

    wait_for_port(8501)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
