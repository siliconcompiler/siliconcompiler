import pytest
import shutil

import os.path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASIC, Design, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.keplerformal.lec import LECTask
from siliconcompiler.tools.keplerformal.sec import SECTask

from siliconcompiler.flows.formalflow import LECFlow

from tools.inputimporter import ImporterTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = ASIC(gcd_design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node("version", LECTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_keplerformal_lec(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('importa', ImporterTask())
    flow.node('importb', ImporterTask())
    flow.node("lec", LECTask())
    flow.edge('importa', 'lec')
    flow.edge('importb', 'lec')
    proj.set_flow(flow)

    os.makedirs("a", exist_ok=True)
    os.makedirs("b", exist_ok=True)
    shutil.copy(os.path.join(datadir, 'lec', 'foo.vg'), 'a/foo.lec.vg')
    shutil.copy(os.path.join(datadir, 'lec', 'foo.vg'), 'b/foo.lec.vg')

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join('a', 'foo.lec.vg'), step='importa')
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join('b', 'foo.lec.vg'), step='importb')

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_keplerformal_lec_broken(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('importa', ImporterTask())
    flow.node('importb', ImporterTask())
    flow.node("lec", LECTask())
    flow.edge('importa', 'lec')
    flow.edge('importb', 'lec')
    proj.set_flow(flow)

    os.makedirs("a", exist_ok=True)
    os.makedirs("b", exist_ok=True)
    shutil.copy(os.path.join(datadir, 'lec', 'foo.vg'), 'a/foo.lec.vg')
    shutil.copy(os.path.join(datadir, 'lec', 'broken', 'foo.vg'), 'b/foo.lec.vg')

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join('a', 'foo.lec.vg'), step='importa')
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join('b', 'foo.lec.vg'), step='importb')

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 1


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_keplerformal_sec(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("sec")
    flow.node('importa', ImporterTask())
    flow.node('importb', ImporterTask())
    flow.node("sec", SECTask())
    flow.edge('importa', 'sec')
    flow.edge('importb', 'sec')
    proj.set_flow(flow)

    # SEC needs a reset to anchor the state to, so it uses its own resettable
    # design rather than the reset-less counter the LEC tests compare.
    SECTask.find_task(proj).add_reset_port("rst")

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'sec', 'foo.v'), step='importa')
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'sec', 'foo.vg'), step='importb')

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='sec', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_keplerformal_sec_broken(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("sec")
    flow.node('importa', ImporterTask())
    flow.node('importb', ImporterTask())
    flow.node("sec", SECTask())
    flow.edge('importa', 'sec')
    flow.edge('importb', 'sec')
    proj.set_flow(flow)

    SECTask.find_task(proj).add_reset_port("rst")

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'sec', 'foo.v'), step='importa')
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'sec', 'broken', 'foo.vg'),
                                     step='importb')

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='sec', index='0') == 1


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("netlist,drvs", [
    (os.path.join('sec', 'foo.vg'), 0),
    (os.path.join('sec', 'broken', 'foo.vg'), 1)])
def test_lecflow_sequential(datadir, netlist, drvs):
    # LECFlow holds only the check, so it is grafted onto the nodes which supply
    # the two views it compares. Both cases run the same graph and differ only in
    # the netlist handed to it: a mismatch has to come back as a drv rather than
    # as an unset metric, which would read as a pass.
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lecflowtest")
    flow.node('rtl', ImporterTask())
    flow.node('netlist', ImporterTask())
    flow.graph(LECFlow(tool="kepler-sec"))
    flow.edge('rtl', 'sec')
    flow.edge('netlist', 'sec')
    proj.set_flow(flow)

    SECTask.find_task(proj).add_reset_port("rst")

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'sec', 'foo.v'), step='rtl')
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, netlist), step='netlist')

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='sec', index='0') == drvs
