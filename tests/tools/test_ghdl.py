# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.ghdl import convert


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
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
def test_ghdl(datadir):
    design = Design("adder")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("adder")
        design.add_file("adder.vhdl")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/adder/job0/convert/0/outputs/adder.v")


def test_runtime_args(datadir):
    design = Design("adder")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("adder")
        design.add_file("adder.vhdl")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        # Verify key arguments are present
        assert any('adder.vhdl' in arg for arg in arguments)
        assert '--synth' in arguments
        assert any(arg.startswith('--out=') for arg in arguments)


def test_ghdl_parameter_use_fsynopsys():
    task = convert.ConvertTask()
    task.set_ghdl_usefsynopsys(True)
    assert task.get("var", "use_fsynopsys") is True
    task.set_ghdl_usefsynopsys(False, step='convert', index='1')
    assert task.get("var", "use_fsynopsys", step='convert', index='1') is False
    assert task.get("var", "use_fsynopsys") is True


def test_ghdl_parameter_use_latches():
    task = convert.ConvertTask()
    task.set_ghdl_uselatches(True)
    assert task.get("var", "use_latches") is True
    task.set_ghdl_uselatches(False, step='convert', index='1')
    assert task.get("var", "use_latches", step='convert', index='1') is False
    assert task.get("var", "use_latches") is True
