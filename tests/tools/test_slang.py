import pyslang
import pytest

import os.path

from siliconcompiler.project import Project
from siliconcompiler import Flowgraph
from siliconcompiler.tools.slang import lint
from siliconcompiler.tools.slang import elaborate


@pytest.mark.parametrize("task", [elaborate.Elaborate, lint.Lint])
def test_version_fail(task, monkeypatch):
    class Version(pyslang.VersionInfo):
        @staticmethod
        def getMajor():
            return 8

        @staticmethod
        def getMinor():
            return 9

        @staticmethod
        def getPatch():
            return 10

    monkeypatch.setattr(pyslang, "VersionInfo", Version)
    with pytest.raises(RuntimeError, match="incorrect pyslang version: 8.9.10"):
        task()


@pytest.mark.parametrize("task", [elaborate.Elaborate, lint.Lint])
def test_version_pass(task):
    assert task()


def test_lint(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("lint")
    flow.node("lint", lint.Lint())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0


def test_elaborate(heartbeat_design):
    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("elaborate")
    flow.node("elaborate", elaborate.Elaborate())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='elaborate', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='elaborate', index='0') == 0

    assert proj.find_result("v", step="elaborate") == \
        os.path.abspath("build/heartbeat/job0/elaborate/0/outputs/heartbeat.v")


def test_slang_duplicate_inputs(heartbeat_design):
    heartbeat_design.copy_fileset("rtl", "rtl_double")
    heartbeat_design.add_file(heartbeat_design.get_file("rtl", "verilog"), "rtl_double")

    proj = Project(heartbeat_design)
    proj.add_fileset("rtl_double")

    flow = Flowgraph("lint")
    flow.node("lint", lint.Lint())
    proj.set_flow(flow)

    assert proj.run()

    assert proj.history("job0").get('metric', 'errors', step='lint', index='0') == 0
    assert proj.history("job0").get('metric', 'warnings', step='lint', index='0') == 0
