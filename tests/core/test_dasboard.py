import siliconcompiler
from siliconcompiler.targets import freepdk45_demo
import time


def test_dashboard():
    chip = siliconcompiler.Chip('dashboard')
    chip.load_target(freepdk45_demo)

    dashboard = chip._dashboard(wait=False)

    time.sleep(10)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
