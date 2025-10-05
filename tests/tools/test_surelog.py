import pytest

import os.path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.surelog.parse import ElaborateTask


@pytest.mark.eda
@pytest.mark.quick
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", ElaborateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
def test_surelog(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("elaborate", ElaborateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "elaborate", "0")
    with node.runtime():
        assert node.setup() is True
        node.run()

    output = proj.find_result('v', step="elaborate")
    assert os.path.isfile(output)


@pytest.mark.eda
@pytest.mark.quick
def test_surelog_preproc_regression(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("test_preproc")
        design.add_file(os.path.join(datadir, 'test_preproc.v'))
        design.add_define("MEM_ROOT=test")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("elaborate", ElaborateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "elaborate", "0")
    with node.runtime():
        assert node.setup() is True
        node.run()

    output = proj.find_result('v', step="elaborate")
    assert os.path.isfile(output)
    with open(output, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()


@pytest.mark.eda
@pytest.mark.quick
def test_github_issue_1789(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("encode_stream_sc_module_8")
        design.add_file(os.path.join(datadir, 'gh1789', 'encode_stream_sc_module_8.v'))
        design.add_define("MEM_ROOT=test")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("elaborate", ElaborateTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "elaborate", "0")
    with node.runtime():
        assert node.setup() is True
        node.run()

    output = proj.find_result('v', step="elaborate")
    assert os.path.isfile(output)
    with open(output, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()

    i_file_data = None
    with open(os.path.join(datadir, 'gh1789', 'encode_stream_sc_module_8.v'), 'r') as f:
        i_file_data = f.read()
    i_file_data = "\n".join(i_file_data.splitlines())

    o_file_data = None
    o_file = output
    with open(o_file, 'r') as f:
        o_file_data = f.read()

    # Remove SC header and footer
    o_file_data = "\n".join(o_file_data.splitlines()[3:-4])

    assert i_file_data == o_file_data
