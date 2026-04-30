# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import os.path

from siliconcompiler import Project, ASIC, Design, PDK
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

    yield


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize('task', [klayout_show.ShowTask, openroad_show.ShowTask],
                         ids=generate_id)
@pytest.mark.parametrize('target, testfile',
                         [(freepdk45_demo, 'heartbeat_freepdk45.def'),
                          (skywater130_demo, 'heartbeat_sky130.def')])
def test_show_def(target, testfile, task, datadir, display):
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASIC(design)
    target(proj)
    proj.add_fileset("rtl")

    ShowTask.register_task(task)
    assert isinstance(ShowTask.get_task("def"), task)

    proj.show(os.path.join(datadir, testfile))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
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
    proj = ASIC(design)
    target(proj)
    proj.add_fileset("rtl")

    ScreenshotTask.register_task(task)
    assert isinstance(ScreenshotTask.get_task("def"), task)

    path = proj.show(os.path.join(datadir, testfile), screenshot=True)
    assert os.path.isfile(path)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_lyp_tool_klayout(datadir, display):
    ''' Test sc-show with only a KLayout .lyp file for layer properties '''
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASIC(design)
    freepdk45_demo(proj)
    proj.add_fileset("rtl")
    pdk: PDK = proj.get("library", "freepdk45", field="schema")
    pdk.set("pdk", "layermapfileset", "klayout", "def", "klayout", [], clobber=True)

    ShowTask.register_task(klayout_show.ShowTask)
    assert isinstance(ShowTask.get_task("def"), klayout_show.ShowTask)

    proj.show(os.path.join(datadir, 'heartbeat_freepdk45.def'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_nopdk_tool_klayout(datadir, display):
    design = Design("heartbeat")
    with design.active_fileset("rtl"):
        design.set_topmodule("heartbeat")
    proj = ASIC(design)
    freepdk45_demo(proj)
    proj.add_fileset("rtl")

    assert isinstance(ShowTask.get_task("gds"), klayout_show.ShowTask)
    testfile = os.path.join(datadir, 'heartbeat.gds.gz')

    proj.show(testfile)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.skip(reason='exit not supported until surfer release 0.4')
def test_show_vcd_surfer(datadir, display, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    ShowTask.register_task(SurferShow)
    assert isinstance(ShowTask.get_task("vcd"), SurferShow)

    proj.show(os.path.join(datadir, 'random.vcd'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_vcd_gtkwave(disable_mp_process, datadir, display, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    ShowTask.register_task(GtkwaveShow)
    assert isinstance(ShowTask.get_task("vcd"), GtkwaveShow)

    proj.show(os.path.join(datadir, 'random.vcd'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_screenshot_dot(datadir, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")
    assert isinstance(ScreenshotTask.get_task("dot"), GraphvizScreenshot)
    file = proj.show(os.path.join(datadir, 'mkDotProduct_nt_Int32.dot'), screenshot=True)
    assert os.path.isfile(file)


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_tasks_stable_ordering():
    """Test that ShowTask returns tasks in a stable order across multiple calls."""
    # Get tasks multiple times to ensure stable ordering
    tasks_1 = ShowTask.get_task(None)
    tasks_2 = ShowTask.get_task(None)
    tasks_3 = ShowTask.get_task(None)

    # Convert to task class names for comparison
    names_1 = [(t.__module__, t.__name__) for t in tasks_1]
    names_2 = [(t.__module__, t.__name__) for t in tasks_2]
    names_3 = [(t.__module__, t.__name__) for t in tasks_3]

    # All three calls should return tasks in the same order
    assert names_1 == names_2, "ShowTask order changed between calls"
    assert names_2 == names_3, "ShowTask order changed between calls"


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_screenshot_tasks_stable_ordering():
    """Test that ScreenshotTask returns tasks in a stable order across multiple calls."""
    # Get tasks multiple times to ensure stable ordering
    tasks_1 = ScreenshotTask.get_task(None)
    tasks_2 = ScreenshotTask.get_task(None)
    tasks_3 = ScreenshotTask.get_task(None)

    # Convert to task class names for comparison
    names_1 = [(t.__module__, t.__name__) for t in tasks_1]
    names_2 = [(t.__module__, t.__name__) for t in tasks_2]
    names_3 = [(t.__module__, t.__name__) for t in tasks_3]

    # All three calls should return tasks in the same order
    assert names_1 == names_2, "ScreenshotTask order changed between calls"
    assert names_2 == names_3, "ScreenshotTask order changed between calls"


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_extension_search_order_stable():
    """Test that extension search order is stable when gathering supported extensions."""
    # Get all tasks
    tasks = ShowTask.get_task(None)

    # Collect extensions multiple times
    exts_1 = []
    exts_2 = []
    exts_3 = []

    for ext_list in [exts_1, exts_2, exts_3]:
        seen = set()
        for cls in tasks:
            try:
                for ext in sorted(cls().get_supported_task_extentions()):
                    if ext not in seen:
                        ext_list.append(ext)
                        seen.add(ext)
            except NotImplementedError:
                pass

    # All three collections should be identical
    assert exts_1 == exts_2, "Extension search order changed between calls"
    assert exts_2 == exts_3, "Extension search order changed between calls"


def test_later_registration_takes_precedence(monkeypatch):
    """Test that later-registered tasks take precedence for supported extensions."""
    from siliconcompiler.tools.klayout.show import ShowTask as KlayoutShow
    from siliconcompiler.tools.openroad.show import ShowTask as OpenROADShow
    from siliconcompiler.utils.multiprocessing import MPManager

    # Isolate registry by clearing the transient settings category for this test
    # This ensures the test exercises registration precedence logic deterministically
    # without being affected by previous test runs
    settings = MPManager.get_transient_settings()

    # Clear the ShowTask category if it exists
    try:
        del settings._settings[ShowTask.__name__]
    except (AttributeError, KeyError):
        pass

    # Register klayout first
    ShowTask.register_task(KlayoutShow)
    task_1 = ShowTask.get_task("def")
    assert isinstance(task_1, KlayoutShow), "First registration should return KlayoutShow for 'def'"

    # Register openroad after (openroad also supports 'def')
    ShowTask.register_task(OpenROADShow)
    task_2 = ShowTask.get_task("def")
    # Later registration (OpenROAD) should take precedence via reversed iteration
    from siliconcompiler.tools.openroad.show import ShowTask as OpenROADShowClass
    assert isinstance(task_2, OpenROADShowClass), \
        f"Later-registered OpenROAD should take precedence, but got {type(task_2).__name__}"


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_task_core_tools_ordered():
    """Test that core siliconcompiler tools are registered in a stable order."""
    # Get all registered tasks
    all_tasks = ShowTask.get_task(None)

    # Find indices of known core tools by checking instances
    task_indices = {}
    for idx, task_cls in enumerate(all_tasks):
        try:
            task_inst = task_cls()
            task_indices[task_inst.tool()] = idx
        except NotImplementedError:
            pass

    # Verify core tools are all present
    assert 'klayout' in task_indices, "KLayout should be registered"
    assert 'openroad' in task_indices, "OpenROAD should be registered"
    assert 'graphviz' in task_indices, "Graphviz should be registered"

    # Store the indices for comparison
    prev_order = (task_indices['klayout'], task_indices['openroad'], task_indices['graphviz'])

    # Get tasks again and verify order hasn't changed
    all_tasks_2 = ShowTask.get_task(None)
    task_indices_2 = {}
    for idx, task_cls in enumerate(all_tasks_2):
        try:
            task_inst = task_cls()
            task_indices_2[task_inst.tool()] = idx
        except NotImplementedError:
            pass

    curr_order = (task_indices_2['klayout'], task_indices_2['openroad'], task_indices_2['graphviz'])

    assert prev_order == curr_order, \
        f"Core tool registration order should be stable: {prev_order} vs {curr_order}"
