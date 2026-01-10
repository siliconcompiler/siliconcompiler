import pytest

import os.path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.chisel import convert


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
def test_chisel(datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("GCD")
        design.add_file("GCD.scala")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/gcd/job0/convert/0/outputs/GCD.v")


def test_chisel_parameter_application():
    task = convert.ConvertTask()
    task.set_chisel_application('test_app')
    assert task.get("var", "application") == 'test_app'
    task.set_chisel_application('other_app', step='convert', index='1')
    assert task.get("var", "application", step='convert', index='1') == 'other_app'
    assert task.get("var", "application") == 'test_app'


def test_chisel_parameter_argument():
    task = convert.ConvertTask()
    task.add_chisel_argument('--threads 2')
    assert task.get("var", "argument") == ['--threads 2']
    task.add_chisel_argument('--no-mem-init')
    assert task.get("var", "argument") == ['--threads 2', '--no-mem-init']
    task.add_chisel_argument('--no-check-comb-loops', step='convert', index='1')
    assert task.get("var", "argument", step='convert', index='1') == ['--no-check-comb-loops']
    assert task.get("var", "argument") == ['--threads 2', '--no-mem-init']
    task.add_chisel_argument(['--no-reset'], clobber=True)
    assert task.get("var", "argument") == ['--no-reset']


def test_chisel_parameter_targetdir():
    task = convert.ConvertTask()
    task.set_chisel_targetdir('build')
    assert task.get("var", "targetdir") == 'build'
    task.set_chisel_targetdir('gen', step='convert', index='1')
    assert task.get("var", "targetdir", step='convert', index='1') == 'gen'
    assert task.get("var", "targetdir") == 'build'
