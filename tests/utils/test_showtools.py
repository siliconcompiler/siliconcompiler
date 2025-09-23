# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Project, ASICProject, Design, PDK
from siliconcompiler import ShowTask, ScreenshotTask

from siliconcompiler.tools.klayout import show as klayout_show
from siliconcompiler.tools.openroad import show as openroad_show
from siliconcompiler.tools.klayout import screenshot as klayout_screenshot
from siliconcompiler.tools.openroad import screenshot as openroad_screenshot
from siliconcompiler.targets import freepdk45_demo, skywater130_demo

from siliconcompiler.tools.graphviz.screenshot import ScreenshotTask as GraphvizScreenshot
from siliconcompiler.tools.gtkwave.show import ShowTask as GtkwaveShow
from siliconcompiler.tools.surfer.show import ShowTask as SurferShow


def generate_id(cls):
    return f"tool_{cls().tool()}"


@pytest.fixture(autouse=True)
def exit_on_show(monkeypatch):
    org_setup = ShowTask.setup

    def mock_setup(self):
        org_setup(self)
        self.set("var", "showexit", True, clobber=True)

    monkeypatch.setattr(ShowTask, "setup", mock_setup)

    with patch.dict("siliconcompiler.ShowTask._ShowTask__TASKS", clear=True):
        yield


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.parametrize('task', [klayout_show.ShowTask, openroad_show.ShowTask],
                         ids=generate_id)
@pytest.mark.parametrize('target, testfile',
                         [(freepdk45_demo, 'heartbeat_freepdk45.def'),
                          (skywater130_demo, 'heartbeat_sky130.def')])
def test_show_def(target, testfile, task, datadir, display):
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASICProject(design)
    target.setup(proj)

    ShowTask.register_task(task)
    assert isinstance(ShowTask.get_task("def"), task)

    proj.show(os.path.join(datadir, testfile))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.parametrize('task', [klayout_screenshot.ScreenshotTask,
                                  openroad_screenshot.ScreenshotTask],
                         ids=generate_id)
@pytest.mark.parametrize('target, testfile',
                         [(freepdk45_demo, 'heartbeat_freepdk45.def'),
                          (skywater130_demo, 'heartbeat_sky130.def')])
def test_screenshot_def(target, testfile, task, datadir, display):
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASICProject(design)
    target.setup(proj)

    ScreenshotTask.register_task(task)
    assert isinstance(ScreenshotTask.get_task("def"), task)

    path = proj.show(os.path.join(datadir, testfile), screenshot=True)
    assert os.path.isfile(path)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_show_lyp_tool_klayout(datadir, display):
    ''' Test sc-show with only a KLayout .lyp file for layer properties '''
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASICProject(design)
    freepdk45_demo.setup(proj)
    pdk: PDK = proj.get("library", "freepdk45", field="schema")
    pdk.set("pdk", "layermapfileset", "klayout", "def", "klayout", [], clobber=True)

    ShowTask.register_task(klayout_show.ShowTask)
    assert isinstance(ShowTask.get_task("def"), klayout_show.ShowTask)

    proj.show(os.path.join(datadir, 'heartbeat_freepdk45.def'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_show_nopdk_tool_klayout(datadir, display):
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASICProject(design)
    freepdk45_demo.setup(proj)

    assert isinstance(ShowTask.get_task("gds"), klayout_show.ShowTask)
    testfile = os.path.join(datadir, 'heartbeat.gds.gz')

    proj.show(testfile)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.skip(reason='exit not supported until surfer release 0.4')
def test_show_vcd_surfer(datadir, display, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    ShowTask.register_task(SurferShow)
    assert isinstance(ShowTask.get_task("vcd"), SurferShow)

    proj.show(os.path.join(datadir, 'random.vcd'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_show_vcd_gtkwave(datadir, display, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    ShowTask.register_task(GtkwaveShow)
    assert isinstance(ShowTask.get_task("vcd"), GtkwaveShow)

    proj.show(os.path.join(datadir, 'random.vcd'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_screenshot_dot(datadir, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")
    assert isinstance(ScreenshotTask.get_task("dot"), GraphvizScreenshot)
    file = proj.show(os.path.join(datadir, 'mkDotProduct_nt_Int32.dot'), screenshot=True)
    assert os.path.isfile(file)
