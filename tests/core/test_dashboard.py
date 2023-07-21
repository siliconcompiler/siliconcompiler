import siliconcompiler
from siliconcompiler.targets import freepdk45_demo
import time
import sys
import pytest


@pytest.mark.skipif(sys.version_info.major == 3 and sys.version_info.minor == 6,
                    reason="Dashboard not available in 3.6")
def test_dashboard():
    chip = siliconcompiler.Chip('dashboard')
    chip.load_target(freepdk45_demo)

    dashboard = chip._dashboard(wait=False)

    time.sleep(10)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
