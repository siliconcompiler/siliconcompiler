import logging
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import ASICProject, Design, Flowgraph
from siliconcompiler.asic import ASICTask, ASICConstraint
from siliconcompiler.library import ToolLibrarySchema

from siliconcompiler.asic import CellArea

from siliconcompiler import StdCellLibrary, PDK
from siliconcompiler.metrics import ASICMetricsSchema
from siliconcompiler.constraints import ASICTimingConstraintSchema, \
    ASICPinConstraints, ASICAreaConstraint, ASICComponentConstraints
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.scheduler import SchedulerNode


@pytest.fixture
def running_project():
    class TestProject(ASICProject):
        def __init__(self):
            super().__init__()

            design = Design("testdesign")
            with design.active_fileset("rtl"):
                design.set_topmodule("designtop")
            self.set_design(design)
            self.add_fileset("rtl")

            self._Project__logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)

            flow = Flowgraph("testflow")
            flow.node("running", NOPTask())
            flow.node("notrunning", NOPTask())
            flow.edge("running", "notrunning")

            self.set_flow(flow)

    return TestProject()


@pytest.fixture
def running_node(running_project):
    return SchedulerNode(running_project, "running", "0")


def test_keys():
    assert ASICProject().getkeys() == (
        'arg',
        'asic',
        'checklist',
        'constraint',
        'flowgraph',
        'history',
        'library',
        'metric',
        'option',
        'record',
        'schemaversion',
        'tool')


def test_keys_asic():
    assert ASICProject().getkeys("asic") == (
        'asiclib',
        'delaymodel',
        'mainlib',
        'maxlayer',
        'minlayer',
        'pdk')


def test_keys_constraint():
    assert isinstance(ASICProject().get("constraint", field="schema"), ASICConstraint)
    assert ASICProject().getkeys("constraint") == (
        'area',
        'component',
        'pin',
        'timing'
    )


def test_metrics():
    assert isinstance(ASICProject().get("metric", field="schema"), ASICMetricsSchema)


def test_getdict_type():
    assert ASICProject._getdict_type() == "ASICProject"


@pytest.mark.parametrize("type", [1, None])
def test_set_mainlib_invalid(type):
    with pytest.raises(TypeError,
                       match="main library must be string or standard cell library object"):
        ASICProject().set_mainlib(type)


def test_set_mainlib_string():
    proj = ASICProject()

    assert proj.get("asic", "mainlib") is None
    proj.set_mainlib("mainlib")
    assert proj.get("asic", "mainlib") == "mainlib"


def test_set_mainlib_obj():
    lib = StdCellLibrary("thislib")
    proj = ASICProject()

    assert proj.get("asic", "mainlib") is None
    proj.set_mainlib(lib)
    assert proj.get("asic", "mainlib") == "thislib"
    assert proj.get("library", "thislib", field="schema") is lib


@pytest.mark.parametrize("type", [1, None])
def test_set_pdk_invalid(type):
    with pytest.raises(TypeError,
                       match="pdk must be string or PDK object"):
        ASICProject().set_pdk(type)


def test_set_pdk_string():
    proj = ASICProject()

    assert proj.get("asic", "pdk") is None
    proj.set_pdk("thispdk")
    assert proj.get("asic", "pdk") == "thispdk"


def test_set_pdk_obj():
    pdk = PDK("thispdk")
    proj = ASICProject()

    assert proj.get("asic", "pdk") is None
    proj.set_pdk(pdk)
    assert proj.get("asic", "pdk") == "thispdk"
    assert proj.get("library", "thispdk", field="schema") is pdk


@pytest.mark.parametrize("type", [1, None])
def test_add_asiclib_invalid(type):
    with pytest.raises(TypeError,
                       match="asic library must be string or standard cell library object"):
        ASICProject().add_asiclib(type)


def test_add_asiclib_string():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib("thislib")
    assert proj.get("asic", "asiclib") == ["thislib"]


def test_add_asiclib_obj():
    lib = StdCellLibrary("thislib")
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(lib)
    assert proj.get("asic", "asiclib") == ["thislib"]
    assert proj.get("library", "thislib", field="schema") is lib


def test_add_asiclib_list():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]


def test_add_asiclib_list_clobber():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]
    proj.add_asiclib(["lib3", "lib2"], clobber=True)
    assert proj.get("asic", "asiclib") == ["lib3", "lib2"]


def test_add_asiclib_clobber():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]
    proj.add_asiclib("lib2", clobber=True)
    assert proj.get("asic", "asiclib") == ["lib2"]


def test_constraint():
    proj = ASICProject()
    assert isinstance(proj.constraint, ASICConstraint)
    assert proj.get("constraint", field="schema") is proj.constraint


def test_set_asic_routinglayers():
    proj = ASICProject()
    proj.set_asic_routinglayers("M1", "M5")
    assert proj.get("asic", "minlayer") == "M1"
    assert proj.get("asic", "maxlayer") == "M5"


def test_set_asic_delaymodel():
    proj = ASICProject()
    proj.set_asic_delaymodel("ccs")
    assert proj.get("asic", "delaymodel") == "ccs"


def test_add_dep_list():
    lib0 = StdCellLibrary("thislib")
    lib1 = StdCellLibrary("thatlib")
    proj = ASICProject()

    proj.add_dep([lib0, lib1])
    assert proj.get("library", "thislib", field="schema") is lib0
    assert proj.get("library", "thatlib", field="schema") is lib1


def test_add_dep_handoff():
    proj = ASICProject()

    with patch("siliconcompiler.Project.add_dep") as add_dep:
        proj.add_dep(None)
        add_dep.assert_called_once_with(None)


def test_check_manifest_empty(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "[asic,pdk] has not been set" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_missing_pdk(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set("asic", "pdk", "thispdk")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thispdk library has not been loaded" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_incorrect_type_pdk(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.add_dep(StdCellLibrary("thislib"))
    proj.set("asic", "pdk", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thislib must be a PDK" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_main_libmissing(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDK("thispdk"))
    proj.set("asic", "mainlib", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thislib library has not been loaded" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "thislib library must be added to [asic,asiclib]" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_asiclib_missing(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDK("thispdk"))
    proj.set("asic", "asiclib", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "thislib library has not been loaded" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_pass(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDK("thispdk"))
    proj.set_mainlib(StdCellLibrary("thislib"))
    proj.add_asiclib("thislib")
    proj.set_asic_delaymodel("nldm")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is True

    assert caplog.text == ""


def test_check_manifest_pass_missing_mainlib(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDK("thispdk"))
    proj.add_asiclib(StdCellLibrary("thislib"))
    proj.set_asic_delaymodel("nldm")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is True

    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text


def test_init_run_set_mainlib(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDK("thispdk"))
    proj.add_asiclib(StdCellLibrary("thislib"))

    assert proj.get("asic", "mainlib") is None
    with patch("siliconcompiler.Project._init_run") as pinit:
        proj._init_run()
        pinit.assert_called_once()
    assert proj.get("asic", "mainlib") == "thislib"

    assert "Setting main library to: thislib" in caplog.text


def test_init_run_set_pdk_asiclib(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    lib = StdCellLibrary("thislib")
    lib.add_asic_pdk(PDK("thispdk"))

    proj.set_mainlib(lib)

    assert proj.get("asic", "asiclib") == []
    assert proj.get("asic", "pdk") is None
    with patch("siliconcompiler.Project._init_run") as pinit:
        proj._init_run()
        pinit.assert_called_once()
    assert proj.get("asic", "pdk") == "thispdk"
    assert proj.get("asic", "asiclib") == ["thislib"]

    assert "Setting pdk to: thispdk" in caplog.text
    assert "Adding thislib to [asic,asiclib]" in caplog.text


def test_init_run_handling_missing_lib(monkeypatch, caplog):
    proj = ASICProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_mainlib("thislib")

    assert proj.get("asic", "asiclib") == []
    assert proj.get("asic", "pdk") is None
    with patch("siliconcompiler.Project._init_run") as pinit:
        proj._init_run()
        pinit.assert_called_once()
    assert proj.get("asic", "pdk") is None
    assert proj.get("asic", "asiclib") == ["thislib"]

    assert "Adding thislib to [asic,asiclib]" in caplog.text


def test_summary_headers():
    proj = ASICProject()

    proj.set_pdk("thispdk")
    proj.set_mainlib("thislib")
    proj.add_asiclib(["thislib", "thatlib"])

    with patch("siliconcompiler.Project._summary_headers") as parent:
        parent.return_value = [("parent", "stuff")]
        assert proj._summary_headers() == [
            ("parent", "stuff"),
            ('pdk', 'thispdk'),
            ('mainlib', 'thislib'),
            ('asiclib', 'thislib, thatlib')
        ]
        parent.assert_called_once()


def test_cell_area():
    report = CellArea()

    assert report.size() == 0

    report.add_cell()
    assert report.size() == 0

    report.add_cell(name="test1", module="mod")
    assert report.size() == 0

    report.add_cell(name="test1", module="mod", cellcount=1, cellarea=2)
    assert report.size() == 1

    report.add_cell(module="mod", cellcount=1, cellarea=2)
    assert report.size() == 2

    report.add_cell(module="mod", cellcount=1, cellarea=2)
    assert report.size() == 3

    report.write_report("test.json")

    assert os.path.isfile("test.json")


def test_asic_mainlib_not_set(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")

    with ASICTask().runtime(running_node) as runtool:
        with pytest.raises(ValueError, match=r"mainlib has not been defined in \[asic,mainlib\]"):
            runtool.mainlib


def test_asic_mainlib_not_loaded(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")

    with ASICTask().runtime(running_node) as runtool:
        with pytest.raises(LookupError, match="testlib has not been loaded"):
            runtool.mainlib


def test_asic_mainlib(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = BaseSchema()
    EditableSchema(project).insert("library", "testlib", lib)

    with ASICTask().runtime(running_node) as runtool:
        assert runtool.mainlib is lib


def test_asic_pdk_not_set(running_node):
    project = running_node.project
    project.set("asic", "mainlib", "testlib")
    lib = BaseSchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))

    with ASICTask().runtime(running_node) as runtool:
        with pytest.raises(ValueError,
                           match=r"pdk has not been defined in \[asic,pdk\]"):
            runtool.pdk


def test_asic_pdk_not_loaded(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = BaseSchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")

    with ASICTask().runtime(running_node) as runtool:
        with pytest.raises(LookupError, match="testpdk has not been loaded"):
            runtool.pdk


def test_asic_pdk(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = BaseSchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    pdk = BaseSchema()
    EditableSchema(project).insert("library", "testpdk", pdk)

    with ASICTask().runtime(running_node) as runtool:
        assert runtool.pdk is pdk


def test_asic_set_asic_var_from_lib(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.set("tool", "testtool", "test_param", "libvalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue")
        assert runtool.get("var", "test_param") == "libvalue"
        assert runtool.get("require") == ['task,var,test_param',
                                          'library,testlib,tool,testtool,test_param',
                                          'task,var,test_param']


def test_asic_set_asic_var_from_pdk(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue")
        assert runtool.get("var", "test_param") == "pdkvalue"
        assert runtool.get("require") == ['task,var,test_param',
                                          'library,testpdk,tool,testtool,test_param',
                                          'task,var,test_param']


def test_asic_set_asic_var_from_defvalue(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue")
        assert runtool.get("var", "test_param") == "defvalue"
        assert runtool.get("require") == ['task,var,test_param']


def test_asic_set_asic_var_no_value(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param") is None
        assert runtool.get("var", "test_param") is None
        assert runtool.get("require") == []


def test_asic_set_asic_var_require_set(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param",
                                    require=True, require_mainlib=True, require_pdk=True) is None
        assert runtool.get("var", "test_param") is None
        assert runtool.get("require") == ['library,testpdk,tool,testtool,test_param',
                                          'library,testlib,tool,testtool,test_param',
                                          'task,var,test_param']


def test_asic_set_asic_var_skip_main(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.set("tool", "testtool", "test_param", "libvalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue", check_mainlib=False)
        assert runtool.get("var", "test_param") == "pdkvalue"
        assert runtool.get("require") == ['task,var,test_param',
                                          'library,testpdk,tool,testtool,test_param',
                                          'task,var,test_param']


def test_asic_set_asic_var_skip_pdk(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue", check_pdk=False)
        assert runtool.get("var", "test_param") == "defvalue"
        assert runtool.get("require") == ['task,var,test_param']


def test_asic_set_asic_var_dontoverwrite(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    lib.define_tool_parameter("testtool", "test_param", "str", "help")
    task.set("var", "test_param", "uservalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue") is None
        assert runtool.get("var", "test_param") == "uservalue"
        assert runtool.get("require") == ['task,var,test_param']


def test_asic_set_asic_var_custom_keys(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_parampdk", "str", "help")
    lib.define_tool_parameter("testtool", "test_paramlib", "str", "help")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param",
                                    require=True, require_mainlib=True, require_pdk=True,
                                    pdk_key="test_parampdk",
                                    mainlib_key="test_paramlib") is None
        assert runtool.get("var", "test_param") is None
        assert runtool.get("require") == ['library,testpdk,tool,testtool,test_parampdk',
                                          'library,testlib,tool,testtool,test_paramlib',
                                          'task,var,test_param']


def test_asic_set_asic_var_skip_main_notdefined(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "str", "help")
    pdk.define_tool_parameter("testtool", "test_param", "str", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param")
        assert runtool.get("var", "test_param") == "pdkvalue"
        assert runtool.get("require") == ['library,testpdk,tool,testtool,test_param',
                                          'task,var,test_param']


def test_asic_set_asic_var_from_pdk_as_list(running_node):
    project = running_node.project
    project.set("asic", "pdk", "testpdk")
    project.set("asic", "mainlib", "testlib")
    lib = ToolLibrarySchema()
    pdk = ToolLibrarySchema()
    EditableSchema(project).insert("library", "testlib", lib)
    EditableSchema(lib).insert("asic", "pdk", Parameter("str"))
    lib.set("asic", "pdk", "testpdk")
    EditableSchema(project).insert("library", "testpdk", pdk)
    EditableSchema(pdk).insert("asic", "pdk", Parameter("str"))

    class TestTask(ASICTask):
        def tool(self):
            return "testtool"
    task = TestTask()
    EditableSchema(project).insert("task", task)
    task.add_parameter("test_param", "[str]", "help")
    pdk.define_tool_parameter("testtool", "test_param", "[str]", "help")
    lib.define_tool_parameter("testtool", "test_param", "[str]", "help")
    pdk.set("tool", "testtool", "test_param", "pdkvalue")
    with task.runtime(running_node) as runtool:
        assert runtool.set_asic_var("test_param", defvalue="defvalue")
        assert runtool.get("var", "test_param") == ["pdkvalue"]
        assert runtool.get("require") == ['task,var,test_param',
                                          'library,testpdk,tool,testtool,test_param',
                                          'task,var,test_param']


@pytest.mark.parametrize(
    "sdc_file,scale,period",
    [
        ("sdc_with_variable.sdc", 1, 10),
        ("sdc_with_nested.sdc", 1, 10),
        ("sdc_with_number0.sdc", 1, 10),
        ("sdc_with_number1.sdc", 1, 10.5),
        ("sdc_with_variable.sdc", 1e-12, 10e-12),
        ("sdc_with_number0.sdc", 1e-12, 10e-12),
        ("sdc_with_number1.sdc", 1e-12, 10.5e-12),
        ("sdc_with_nested.sdc", 1e-9, 10e-9),
    ])
def test_get_clock_sdc(datadir, sdc_file, scale, period, running_project, running_node):
    task = ASICTask()
    EditableSchema(running_project).insert("tool", "dummy", "task", "asic", task)

    design = running_project.design
    with design.active_fileset("sdc"):
        design.add_file(os.path.join(datadir, "asic", sdc_file))
    running_project.add_fileset("sdc")

    with task.runtime(running_node) as runtool:
        name, sdc_period = runtool.get_clock(scale)

    assert name is None
    assert sdc_period == period


def test_get_clock_none(running_project, running_node):
    task = ASICTask()
    EditableSchema(running_project).insert("tool", "dummy", "task", "asic", task)

    with task.runtime(running_node) as runtool:
        name, sdc_period = runtool.get_clock()

    assert name is None
    assert sdc_period is None


def test_snapshot_info_empty():
    proj = ASICProject(Design("testdesign"))

    assert proj._snapshot_info() == [
        ("Design", "testdesign")
    ]


def test_snapshot_info_pdk():
    proj = ASICProject(Design("testdesign"))
    proj.set("asic", "pdk", "testpdk")

    assert proj._snapshot_info() == [
        ("Design", "testdesign"),
        ("PDK", "testpdk")
    ]


def test_snapshot_info_metrics(running_project):
    running_project.set("asic", "pdk", "testpdk")
    running_project.set("metric", "totalarea", 10, step="running", index="0")
    running_project.set("metric", "fmax", 5, step="running", index="0")
    running_project.set("metric", "totalarea", 20, step="notrunning", index="0")
    running_project.set("metric", "fmax", 30, step="notrunning", index="0")

    assert running_project._snapshot_info() == [
        ("Design", "testdesign"),
        ("PDK", "testpdk"),
        ("Area", "20.000um^2"),
        ("Fmax", "30.000Hz")
    ]


def test_snapshot_info_metrics_mixed_nodes(running_project):
    running_project.set("asic", "pdk", "testpdk")
    running_project.set("metric", "totalarea", 10, step="running", index="0")
    running_project.set("metric", "fmax", 5, step="running", index="0")
    running_project.set("metric", "totalarea", 20, step="notrunning", index="0")

    assert running_project._snapshot_info() == [
        ("Design", "testdesign"),
        ("PDK", "testpdk"),
        ("Area", "20.000um^2"),
        ("Fmax", "5.000Hz")
    ]


def test_constraint_timing():
    const = ASICConstraint()
    assert isinstance(const.timing, ASICTimingConstraintSchema)
    assert const.get("timing", field="schema") is const.timing


def test_constraint_pin():
    const = ASICConstraint()
    assert isinstance(const.pin, ASICPinConstraints)
    assert const.get("pin", field="schema") is const.pin


def test_constraint_component():
    const = ASICConstraint()
    assert isinstance(const.component, ASICComponentConstraints)
    assert const.get("component", field="schema") is const.component


def test_constraint_area():
    const = ASICConstraint()
    assert isinstance(const.area, ASICAreaConstraint)
    assert const.get("area", field="schema") is const.area
