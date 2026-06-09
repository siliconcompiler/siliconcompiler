import os

import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.xdm import convert
from siliconcompiler.tools.xyce import simulate


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_xdm_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_xyce_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", simulate.SimulateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_xdm_runtime_options(gcd_design):
    # Regression: ConvertTask.runtime_options() previously had no `return options`,
    # so it returned None and get_runtime_arguments() raised
    # "runtime_options() returned None".
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    # xdm resolves its input from inputs/<top>.spice at runtime.
    os.makedirs("inputs", exist_ok=True)
    with open("inputs/gcd.spice", "w") as f:
        f.write("* spice\n")

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments == [
        '--auto',
        '--source_file_format', 'hspice',
        '--dir_out', 'outputs/gcd.xyce',
        'inputs/gcd.spice',
    ]


def test_xdm_parameter_rename():
    task = convert.ConvertTask()
    task.set_xdm_rename(False)
    assert task.get("var", "rename") is False
    task.set_xdm_rename(True, step='convert', index='1')
    assert task.get("var", "rename", step='convert', index='1') is True
    assert task.get("var", "rename") is False
