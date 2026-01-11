import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.gtkwave import show


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design, display):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", show.ShowTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_args(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("show", show.ShowTask())
    proj.set_flow(flow)

    # GTKWave expects a VCD or similar file as input
    show.ShowTask.find_task(proj).set("var", "showfilepath", "test.vcd")
    with open("test.vcd", "w") as f:
        f.write("test\n")

    node = SchedulerNode(proj, "show", "0")
    with node.runtime():
        with patch("siliconcompiler.utils.get_cores") as get_cores:
            get_cores.return_value = 2
            assert node.setup() is True
            get_cores.assert_called_once()
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            '--cpu=2',
            f'--script={node.task.find_files("script")[0]}',
            f'--dump={os.path.abspath("test.vcd")}'
        ]
