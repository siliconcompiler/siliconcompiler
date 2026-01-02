import pytest
import shutil

import os.path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASIC, Design, Flowgraph, FPGA
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.keplerformal.lec import LECTask

from tools.inputimporter import ImporterTask

from siliconcompiler.utils import sc_open


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
