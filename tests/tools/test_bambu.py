import pytest

import os.path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.bambu import convert


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
def test_bambu(datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/gcd/job0/convert/0/outputs/gcd.v")


def test_runtime_args(gcd_design, datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.c")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            os.path.abspath(os.path.join(datadir, 'gcd.c')),
            '--soft-float',
            '--memory-allocation-policy=NO_BRAM',
            '--channels-number=1',
            '--disable-function-proxy',
            '--top-fname=gcd'
        ]


def test_parameter_memorychannels():
    task = convert.ConvertTask()
    task.set_bambu_memorychannels(2)
    assert task.get("var", "memorychannels") == 2
    task.set_bambu_memorychannels(4, step='convert', index='1')
    assert task.get("var", "memorychannels", step='convert', index='1') == 4
    assert task.get("var", "memorychannels") == 2
