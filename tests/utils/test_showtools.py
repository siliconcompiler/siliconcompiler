# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest
import subprocess
import sys

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


def task_spec(cls):
    """
    The ``"tool/task"`` hint that pins get_task() to exactly this class.

    Registering a task does not make it the one get_task() picks -- discovery
    registers every built-in viewer, and the tool with the last registration
    wins the extension. Ask for the task by name instead, which is what a user
    who wants a particular viewer does.
    """
    inst = cls()
    return f"{inst.tool()}/{inst.task()}"


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

    spec = task_spec(task)
    assert isinstance(ShowTask.get_task("def", tool=spec), task)

    proj.show(os.path.join(datadir, testfile), tool=spec)


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

    spec = task_spec(task)
    assert isinstance(ScreenshotTask.get_task("def", tool=spec), task)

    path = proj.show(os.path.join(datadir, testfile), screenshot=True, tool=spec)
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

    spec = task_spec(klayout_show.ShowTask)
    assert isinstance(ShowTask.get_task("def", tool=spec), klayout_show.ShowTask)

    proj.show(os.path.join(datadir, 'heartbeat_freepdk45.def'), tool=spec)


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

    spec = task_spec(SurferShow)
    assert isinstance(ShowTask.get_task("vcd", tool=spec), SurferShow)

    proj.show(os.path.join(datadir, 'random.vcd'), tool=spec)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_show_vcd_gtkwave(disable_mp_process, datadir, display, gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    spec = task_spec(GtkwaveShow)
    assert isinstance(ShowTask.get_task("vcd", tool=spec), GtkwaveShow)

    proj.show(os.path.join(datadir, 'random.vcd'), tool=spec)


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


def test_later_registration_takes_precedence(isolated_tasks):
    """Test that later-registered tasks take precedence for supported extensions."""
    from siliconcompiler.tools.klayout.show import ShowTask as KlayoutShow
    from siliconcompiler.tools.openroad.show import ShowTask as OpenROADShow

    # isolated_tasks skips discovery, so the registry holds only the two
    # viewers registered below and the precedence logic is what is under test.

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


# The viewer preference in showtools only takes effect if the module is imported after
# the subclass recursion in __populate_tasks has run, so this has to be checked in a
# fresh interpreter where nothing has imported showtools yet.
VCD_PREFERENCE_PROBE = """
import sys, shutil
want = sys.argv[1] if len(sys.argv) > 1 else None
shutil.which = lambda name, *a, **k: ("/usr/bin/" + name) if name == want else None

from unittest.mock import patch
import siliconcompiler.utils as utils
with patch.object(utils, "entry_points", lambda group: []):
    from siliconcompiler import ShowTask
    assert "siliconcompiler.utils.showtools" not in sys.modules, "showtools imported early"
    print(ShowTask.get_task("vcd").tool())
"""


@pytest.mark.parametrize("available,expected", [
    ("surfer", "surfer"),
    ("gtkwave", "gtkwave")
])
def test_vcd_viewer_preference(available, expected):
    """The installed VCD viewer is preferred, with no plugins involved."""
    proc = subprocess.run([sys.executable, "-c", VCD_PREFERENCE_PROBE, available],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


# ---------------------------------------------------------------------------
# Tool-hint resolution against the real built-in registry.
#
# showtasks() registers OpenROADWeb *before* OpenROADShow so that the
# "later registration wins" rule makes openroad/show the default viewer for
# odb/def/vg. These pin that the -tool hint agrees with the default instead of
# inverting it.
# ---------------------------------------------------------------------------

OPENROAD_SHOW_EXTS = ["odb", "def", "vg"]


@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("ext", OPENROAD_SHOW_EXTS)
def test_openroad_default_viewer_is_show_not_web(ext):
    """The unhinted default for OpenROAD's extensions is the GUI, not the webviewer."""
    task = ShowTask.get_task(ext)

    assert (task.tool(), task.task()) == ("openroad", "show")


@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("ext", OPENROAD_SHOW_EXTS)
def test_openroad_tool_only_hint_matches_default(ext):
    """"-tool openroad" must not downgrade the choice to openroad/web.

    Regression: find_task_by_spec() walked the registry forward while the
    automatic fallback walked it backward, so naming the tool selected the
    task the registration order was set up to lose.
    """
    task = ShowTask.get_task(ext, tool="openroad")

    assert (task.tool(), task.task()) == ("openroad", "show"), \
        f"-tool openroad picked openroad/{task.task()} for '{ext}'"


@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("ext", OPENROAD_SHOW_EXTS)
@pytest.mark.parametrize("task_name", ["show", "web"])
def test_openroad_tool_task_hint_is_exact(ext, task_name):
    """The full "tool/task" form still reaches either viewer."""
    task = ShowTask.get_task(ext, tool=f"openroad/{task_name}")

    assert (task.tool(), task.task()) == ("openroad", task_name)


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_3dblox_tool_only_hint_matches_default():
    """The same ordering holds for the 3dbx pair."""
    assert ShowTask.get_task("3dbx").task() == "show3dblox"
    assert ShowTask.get_task("3dbx", tool="openroad").task() == "show3dblox"


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_klayout_tool_only_hint_matches_default():
    """A tool with a single task is unaffected by the reversed walk."""
    task = ShowTask.get_task("gds", tool="klayout")

    assert (task.tool(), task.task()) == ("klayout", "show")


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_extension_map_tool_hint_matches_default():
    """sc-show -list stars the same task the hint resolves to."""
    default_map = ShowTask.get_extension_map()
    hinted_map = ShowTask.get_extension_map(tool="openroad")

    for ext in OPENROAD_SHOW_EXTS:
        assert type(default_map[ext]) is type(hinted_map[ext])
        assert hinted_map[ext].task() == "show"


@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("bad_tool", ["openrroad", "openrroad/web", "openroad/wbe"])
def test_misspelled_tool_is_refused_not_substituted(bad_tool):
    """A typo must not silently resolve to some other viewer."""
    assert ShowTask.get_task("odb", tool=bad_tool) is None


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_tool_without_extension_support_is_refused():
    """klayout cannot read odb, so asking for it is an error, not a fallback."""
    assert ShowTask.get_task("odb", tool="klayout") is None
    assert ShowTask.get_task("gds", tool="openroad") is None


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_tasks_for_extension_reports_openroad_viewers():
    """The candidate list backing the error message is in priority order."""
    names = [f"{t.tool()}/{t.task()}" for t in ShowTask._get_tasks_for_extension("odb")]

    assert names == ["openroad/show", "openroad/web"]


@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("bad_tool", ["openrroad/web", "klayout"])
def test_project_show_refuses_unusable_tool(bad_tool, monkeypatch, caplog, gcd_design):
    """Project.show() reports the bad tool instead of running a different one."""
    proj = Project(gcd_design)
    proj.add_fileset("rtl")
    proj.logger.setLevel("INFO")

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.path.abspath", lambda x: x)

    def no_run(self):
        raise AssertionError("show() ran a flow despite an unusable -tool")

    monkeypatch.setattr(Project, "run", no_run)

    assert proj.show("/path/to/design.odb", tool=bad_tool) is None

    assert f"Filetype 'odb' not available for '{bad_tool}'." in caplog.text
    assert "Tasks supporting 'odb': openroad/show, openroad/web" in caplog.text


@pytest.mark.quick
@pytest.mark.timeout(300)
def test_project_show_tool_hint_selects_default_task(monkeypatch, gcd_design):
    """Project.show() with "-tool openroad" builds a flow around openroad/show."""
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.path.abspath", lambda x: x)

    picked = []

    def capture_run(self):
        flow = self.get_flow(self.option.get_flow())
        for step, index in flow.get_nodes():
            task = flow.get_task_module(step, index)()
            picked.append(f"{task.tool()}/{task.task()}")

    monkeypatch.setattr(Project, "run", capture_run)

    proj.show("/path/to/design.odb", tool="openroad")

    assert picked == ["openroad/show"]


# An early import of a viewer module lets the subclass recursion in
# __build_tasks register it before showtasks() gets a say. register_task()
# re-orders on re-registration so showtools still decides, but that has to be
# checked in a fresh interpreter -- this module imports openroad.show at the
# top, so the "early" case is already baked in by the time a test runs here.
IMPORT_ORDER_PROBE = """
import sys
if len(sys.argv) > 1 and sys.argv[1] == "early":
    import siliconcompiler.tools.openroad.show  # noqa: F401

from unittest.mock import patch
import siliconcompiler.utils as utils
with patch.object(utils, "entry_points", lambda group: []):
    from siliconcompiler import ShowTask
    order = []
    for cls in ShowTask.get_task(None):
        try:
            inst = cls()
            order.append(inst.tool() + "/" + inst.task())
        except NotImplementedError:
            continue
    print(",".join(order))
    for hint in (None, "openroad"):
        task = ShowTask.get_task("odb", tool=hint)
        print(task.tool() + "/" + task.task())
"""


@pytest.mark.parametrize("when", ["late", "early"])
def test_registry_order_independent_of_viewer_import_order(when):
    """showtools decides priority even if a viewer module was imported first.

    Regression: register_task() wrote through to a dict, and assigning an
    existing key leaves it in place. Importing openroad.show before the first
    get_task() therefore let the module-path-sorted subclass recursion pin
    WebTask after ShowTask, making openroad/web the default for odb.
    """
    proc = subprocess.run([sys.executable, "-c", IMPORT_ORDER_PROBE, when],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    order, unhinted, hinted = proc.stdout.strip().splitlines()

    assert order.split(",") == [
        "klayout/show",
        "openroad/web",
        "openroad/show",
        "openroad/web3dblox",
        "openroad/show3dblox",
        "graphviz/show",
        "vpr/show",
        "gtkwave/show",
        "surfer/show",
    ]
    assert unhinted == "openroad/show"
    assert hinted == "openroad/show"
