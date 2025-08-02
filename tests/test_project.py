import logging
import pickle
import pytest

import os.path

from pathlib import Path

from unittest.mock import patch

from siliconcompiler import Project
from siliconcompiler import DesignSchema, FlowgraphSchema, TaskSchema, \
    ToolSchema, ChecklistSchema, LibrarySchema

from siliconcompiler.schema import NamedSchema, EditableSchema, Parameter

from siliconcompiler.utils.logging import SCColorLoggerFormatter, SCLoggerFormatter

from siliconcompiler.project import SCColorLoggerFormatter as dut_sc_color_logger


def test_key_groups():
    assert Project().getkeys() == (
        'arg',
        'checklist',
        'flowgraph',
        'history',
        'library',
        'metric',
        'option',
        'record',
        'schemaversion',
        'tool'
    )


def test_cwd():
    assert Project().cwd == os.path.abspath(".")


def test_init_logger(monkeypatch):
    monkeypatch.setattr(dut_sc_color_logger, "supports_color", lambda _: True)

    project = Project()
    assert isinstance(project.logger, logging.Logger)
    assert isinstance(project._logger_console, logging.StreamHandler)
    assert isinstance(project._logger_console.formatter, SCColorLoggerFormatter)
    assert project._logger_console in project.logger.handlers

    assert project.logger.name.startswith("siliconcompiler.project_")


def test_init_logger_no_color(monkeypatch):
    monkeypatch.setattr(dut_sc_color_logger, "supports_color", lambda _: False)

    project = Project()
    assert isinstance(project.logger, logging.Logger)
    assert isinstance(project._logger_console, logging.StreamHandler)
    assert isinstance(project._logger_console.formatter, SCLoggerFormatter)
    assert project._logger_console in project.logger.handlers

    assert project.logger.name.startswith("siliconcompiler.project_")


def test_name_not_set():
    assert Project().name is None


def test_name_set_from_init():
    assert Project("testname").name == "testname"


def test_name_set_from_init_with_design():
    assert Project(DesignSchema("testname")).name == "testname"


def test_name_set_from_set_design():
    project = Project()
    assert project.name is None
    project.set_design("testname")
    assert project.name == "testname"


def test_design_not_set():
    with pytest.raises(ValueError, match="design name is not set"):
        Project().design


def test_design_not_imported():
    with pytest.raises(KeyError, match="testname design has not been loaded"):
        Project("testname").design


def test_design():
    design = DesignSchema("testname")
    project = Project(design)

    assert project.design is design


def test_set_design_str():
    project = Project("oldname")
    assert project.name == "oldname"
    project.set_design("testname")
    assert project.name == "testname"


def test_set_design_not_valid():
    with pytest.raises(TypeError, match="design must be string or Design object"):
        Project().set_design(2)


def test_set_design_obj():
    project = Project("oldname")
    assert project.name == "oldname"

    design = DesignSchema("testname")
    project.set_design(design)
    assert project.name == "testname"
    assert project.design is design


def test_set_flow_str():
    project = Project()
    project.set_flow("testflow")
    assert project.get("option", "flow") == "testflow"


def test_set_flow_not_valid():
    with pytest.raises(TypeError, match="flow must be string or Flowgraph object"):
        Project().set_flow(2)


def test_set_flow_obj():
    project = Project()
    flow = FlowgraphSchema("testflow")
    project.set_flow(flow)
    assert project.get("option", "flow") == "testflow"
    assert project.get("flowgraph", "testflow", field="schema") is flow


def test_pickling(monkeypatch):
    monkeypatch.setattr(dut_sc_color_logger, "supports_color", lambda _: True)

    org_prj = Project()
    new_prj = pickle.loads(pickle.dumps(org_prj))

    assert org_prj.logger is not new_prj.logger
    assert isinstance(new_prj.logger, logging.Logger)
    assert isinstance(new_prj._logger_console, logging.StreamHandler)
    assert isinstance(new_prj._logger_console.formatter, SCColorLoggerFormatter)
    assert new_prj._logger_console in new_prj.logger.handlers


def test_builddir():
    assert Project()._Project__getbuilddir() == os.path.abspath("build")


def test_builddir_abspath():
    project = Project()
    project.set("option", "builddir", os.path.abspath("diffdir/buildhere"))

    assert project._Project__getbuilddir() == \
        Path(os.path.abspath("diffdir/buildhere")).as_posix()


def test_builddir_diff_build():
    project = Project()
    project.set("option", "builddir", "testbuild")
    assert project._Project__getbuilddir() == os.path.abspath("testbuild")


def test_getworkdir_no_name():
    with pytest.raises(ValueError, match="name has not been set"):
        Project().getworkdir()


def test_getworkdir():
    assert Project("testname").getworkdir() == \
        os.path.abspath(os.path.join("build", "testname", "job0"))


def test_getworkdir_diff_jobname():
    prj = Project("testname")
    prj.set("option", "jobname", "thisjob")
    assert prj.getworkdir() == os.path.abspath(os.path.join("build", "testname", "thisjob"))


def test_getworkdir_step():
    assert Project("testname").getworkdir(step="thisstep") == \
        os.path.abspath(os.path.join("build", "testname", "job0", "thisstep", "0"))


def test_getworkdir_step_index():
    assert Project("testname").getworkdir(step="thisstep", index="thisindex") == \
        os.path.abspath(os.path.join("build", "testname", "job0", "thisstep", "thisindex"))


def test_getcollectiondir():
    assert Project("testname").getcollectiondir() == \
        os.path.abspath(os.path.join("build", "testname", "job0", "sc_collected_files"))


def test_record_history():
    proj = Project("testname")
    assert proj.getkeys("history") == tuple()
    proj._record_history()
    assert proj.getkeys("history") == ("job0",)
    assert isinstance(proj.get("history", "job0", field="schema"), Project)
    assert proj.get("history", "job0", field="schema") is not proj
    assert proj.get("history", "job0", field="schema").getkeys("history") == tuple()


def test_record_history_recursive_history():
    proj = Project("testname")
    proj._record_history()
    proj.set("option", "jobname", "job1")
    proj._record_history()

    assert proj.get("history", "job0", field="schema").getkeys("history") == tuple()
    assert proj.get("history", "job1", field="schema").getkeys("history") == tuple()


def test_record_history_warn(caplog):
    proj = Project("testname")
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.WARNING)
    proj._record_history()
    proj._record_history()

    assert "Overwriting job job0" in caplog.text


def test_history():
    proj = Project("testname")
    proj._record_history()

    proj.set_design("newname")
    assert proj.name == "newname"

    assert isinstance(proj.history("job0"), Project)
    assert proj.history("job0").name == "testname"


def test_history_missing():
    with pytest.raises(KeyError, match="job0 is not a valid job"):
        Project().history("job0")


def test_add_fileset():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    with design.active_fileset("rtl.other"):
        design.set_topmodule("top2")
    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.get("option", "fileset") == ["rtl"]
    assert proj.add_fileset("rtl.other")
    assert proj.get("option", "fileset") == ["rtl", "rtl.other"]


def test_add_fileset_list():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    with design.active_fileset("rtl.other"):
        design.set_topmodule("top2")
    proj = Project(design)
    assert proj.add_fileset(["rtl", "rtl.other"])
    assert proj.get("option", "fileset") == ["rtl", "rtl.other"]


def test_add_fileset_list_invalid():
    design = DesignSchema("test")
    proj = Project(design)
    with pytest.raises(TypeError, match="fileset must be a string"):
        proj.add_fileset(["rtl", 1])


def test_add_fileset_clobber():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    with design.active_fileset("rtl.other"):
        design.set_topmodule("top2")
    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.get("option", "fileset") == ["rtl"]
    assert proj.add_fileset("rtl.other", clobber=True)
    assert proj.get("option", "fileset") == ["rtl.other"]


def test_add_fileset_invalid_type():
    design = DesignSchema("test")
    proj = Project(design)
    with pytest.raises(TypeError, match="fileset must be a string"):
        proj.add_fileset(1)


def test_add_fileset_invalid():
    design = DesignSchema("test")
    proj = Project(design)
    with pytest.raises(ValueError, match="rtl is not a valid fileset in test"):
        proj.add_fileset("rtl")


def test_convert():
    class ASICProject(Project):
        def __init__(self, design=None):
            super().__init__(design)

            EditableSchema(self).insert("asic", Parameter("str"))

    class FPGAProject(Project):
        def __init__(self, design=None):
            super().__init__(design)

            EditableSchema(self).insert("fpga", Parameter("str"))

    design = DesignSchema("design0")
    proj0 = ASICProject(design)

    proj1 = FPGAProject.convert(proj0)

    assert proj0.allkeys("library") == proj1.allkeys("library")
    assert proj0.allkeys("library") == proj1.allkeys("library")


def test_convert_invalid():
    with pytest.raises(TypeError, match="source object must be a Project"):
        Project.convert("this")


def test_add_dep_design():
    design = DesignSchema("test")
    proj = Project()
    proj.add_dep(design)
    assert proj.getkeys("library") == ("test",)
    assert proj.get("library", "test", field="schema") is design


def test_add_dep_design_with_deps():
    dep = DesignSchema("test0")
    design = DesignSchema("test")
    design.add_dep(dep)

    proj = Project()
    proj.add_dep(design)
    assert proj.getkeys("library") == ("test", "test0")
    assert proj.get("library", "test", field="schema") is design
    assert proj.get("library", "test0", field="schema") is dep


def test_add_dep_flowgraph():
    flow = FlowgraphSchema("test")
    proj = Project()
    proj.add_dep(flow)
    assert proj.getkeys("flowgraph") == ("test",)
    assert proj.get("flowgraph", "test", field="schema") is flow


@pytest.mark.skip(reason="flowgraph needs to be updated")
def test_add_dep_flowgraph_with_tasks():
    class Task0(TaskSchema):
        def tool(self):
            return "tool0"

        def task(self):
            return "task0"

    class Task1(TaskSchema):
        def tool(self):
            return "tool1"

        def task(self):
            return "task1"

    class Task2(TaskSchema):
        def tool(self):
            return "tool1"

        def task(self):
            return "task2"

    flow = FlowgraphSchema("test")
    flow.node("step0", Task0())
    flow.node("step1", Task1())
    flow.node("step2", Task2())

    proj = Project()
    proj.add_dep(flow)
    assert proj.getkeys("flowgraph") == ("test",)
    assert proj.get("flowgraph", "test", field="schema") is flow
    assert proj.getkeys("tools") == ("tool0", "tool1")
    assert proj.getkeys("tools", "tool0", "task") == ("task0",)
    assert proj.getkeys("tools", "tool1", "task") == ("task1", "task2")
    assert isinstance(proj.get("tools", "tool0", "task", "task0", field="schema"), Task0)
    assert isinstance(proj.get("tools", "tool1", "task", "task1", field="schema"), Task1)
    assert isinstance(proj.get("tools", "tool1", "task", "task2", field="schema"), Task2)


def test_add_dep_checklist():
    checklist = ChecklistSchema("test")
    proj = Project()
    proj.add_dep(checklist)
    assert proj.getkeys("checklist") == ("test",)
    assert proj.get("checklist", "test", field="schema") is checklist


def test_add_dep_library():
    lib = LibrarySchema("test")
    proj = Project()
    proj.add_dep(lib)
    assert proj.getkeys("library") == ("test",)
    assert proj.get("library", "test", field="schema") is lib


def test_get_filesets_empty():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    assert Project(design).get_filesets() == []


def test_get_filesets_single():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.get_filesets() == [
        (design, "rtl")
    ]


def test_get_filesets_with_deps():
    dep = DesignSchema("dep")
    with dep.active_fileset("rtl.dep"):
        dep.set_topmodule("top")

    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_depfileset(dep, "rtl.dep")

    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.get_filesets() == [
        (design, "rtl"),
        (dep, "rtl.dep")
    ]


def test_add_alias_invalid_src_type():
    proj = Project()
    with pytest.raises(TypeError, match="source dep is not a valid type"):
        proj.add_alias(1, "rtl", 2, "rtl")


def test_add_alias_src_name_not_loaded():
    dst = DesignSchema("dst")
    with dst.active_fileset("rtl"):
        dst.set_topmodule("top")

    proj = Project()
    assert proj.has_library("test0") is False
    proj.add_alias("test0", "rtl", dst, "rtl")
    assert proj.has_library("test0") is False
    assert proj.get("option", "alias") == [
        ("test0", "rtl", "dst", "rtl")
    ]


def test_add_alias_src_dep_not_loaded():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    dst = DesignSchema("dst")
    with dst.active_fileset("rtl"):
        dst.set_topmodule("top")

    proj = Project()
    assert proj.has_library(design) is False
    proj.add_alias(design, "rtl", dst, "rtl")
    assert proj.has_library(design) is True
    assert proj.get("option", "alias") == [
        ("test", "rtl", "dst", "rtl")
    ]


def test_add_alias_src_invalid_fileset():
    design = DesignSchema("test")

    proj = Project(design)
    with pytest.raises(ValueError, match="test does not have rtl as a fileset"):
        proj.add_alias(design, "rtl", 2, "rtl")


def test_add_alias_src_name_type():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    EditableSchema(proj).insert("library", "test0", NamedSchema())
    with pytest.raises(TypeError, match="source dep is not a valid type"):
        proj.add_alias("test0", "rtl", 2, "rtl")


def test_add_alias_invalid_dst_type():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    with pytest.raises(TypeError, match="alias dep is not a valid type"):
        proj.add_alias("test", "rtl", 2, "rtl")


def test_add_alias_dst_name_not_loaded():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    with pytest.raises(KeyError, match="test0 has not been loaded"):
        proj.add_alias("test", "rtl", "test0", "rtl")


def test_add_alias_dst_invalid_fileset():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")

    proj = Project(design)
    with pytest.raises(ValueError, match="alias does not have rtl2 as a fileset"):
        proj.add_alias("test", "rtl", alias, "rtl2")


def test_add_alias_dst_name_type():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    with pytest.raises(TypeError, match="alias dep is not a valid type"):
        proj.add_alias("test", "rtl", 2, "rtl")


def test_add_alias_dst_by_name_type():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    EditableSchema(proj).insert("library", "test0", NamedSchema())
    with pytest.raises(TypeError, match="alias dep is not a valid type"):
        proj.add_alias("test", "rtl", "test0", "rtl")


def test_add_alias_alias_imported():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    with design.active_fileset("rtl.other"):
        design.set_topmodule("top")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_alias("test", "rtl", alias, "rtl")
    assert proj.add_alias("test", "rtl.other", alias, "rtl1")
    assert proj.getkeys("library") == ("alias", "test")
    assert proj.get("library", "alias", field="schema") is alias
    assert proj.get("option", "alias") == [
        ("test", "rtl", "alias", "rtl"),
        ("test", "rtl.other", "alias", "rtl1")
    ]


def test_add_alias_alias_imported_clobber():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_alias("test", "rtl", alias, "rtl")
    assert proj.add_alias("test", "rtl", "alias", "rtl1", clobber=True)
    assert proj.getkeys("library") == ("alias", "test")
    assert proj.get("library", "alias", field="schema") is alias
    assert proj.get("option", "alias") == [
        ("test", "rtl", "alias", "rtl1")
    ]


def test_add_alias_remove_alias():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_alias("test", "rtl", None, "rtl")
    assert proj.get("option", "alias") == [
        ("test", "rtl", None, None)
    ]


def test_add_alias_repeat_fileset():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_alias("test", "rtl", alias, "")
    assert proj.get("option", "alias") == [
        ("test", "rtl", "alias", None)
    ]


def test_get_filesets_with_alias():
    dep = DesignSchema("dep")
    with dep.active_fileset("rtl"):
        dep.set_topmodule("top")

    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_depfileset(dep, "rtl")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.add_alias(dep, "rtl", alias, "rtl1")
    assert proj.get_filesets() == [
        (design, "rtl"),
        (alias, "rtl1")
    ]


def test_get_filesets_with_alias_remove():
    dep = DesignSchema("dep")
    with dep.active_fileset("rtl"):
        dep.set_topmodule("top")

    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_depfileset(dep, "rtl")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.add_alias(dep, "rtl", None, "rtl1")
    assert proj.get_filesets() == [
        (design, "rtl")
    ]


def test_get_filesets_with_alias_same_fileset():
    dep = DesignSchema("dep")
    with dep.active_fileset("rtl"):
        dep.set_topmodule("top")

    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_depfileset(dep, "rtl")

    alias = DesignSchema("alias")
    with alias.active_fileset("rtl"):
        alias.set_topmodule("top")
    with alias.active_fileset("rtl1"):
        alias.set_topmodule("top")

    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.add_alias(dep, "rtl", alias, "rtl")
    assert proj.get_filesets() == [
        (design, "rtl"),
        (alias, "rtl")
    ]


def test_get_filesets_with_alias_missing():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    assert proj.add_fileset("rtl")
    assert proj.set("option", "alias", ("test", "rtl", "test1", "rtl"))

    with pytest.raises(KeyError, match="test1 is not a loaded library"):
        proj.get_filesets()


def test_has_library_not_found():
    proj = Project()
    assert proj.has_library("test") is False

    proj.add_dep(DesignSchema("test"))
    assert proj.has_library("notfound") is False
    assert proj.has_library("test") is True


def test_has_library_not_found_with_object():
    proj = Project()
    design = DesignSchema("test")
    assert proj.has_library(design) is False

    proj.add_dep(design)
    assert proj.has_library("notfound") is False
    assert proj.has_library(design) is True


def test_summary_headers():
    proj = Project(DesignSchema("testdesign"))
    assert proj._summary_headers() == [
        ("design", "testdesign"),
        ("jobdir", os.path.abspath("build/testdesign/job0"))
    ]


def test_summary_headers_filesets():
    proj = Project(DesignSchema("testdesign"))
    proj.set("option", "fileset", ["rtl0", "rtl1"])
    assert proj._summary_headers() == [
        ("design", "testdesign"),
        ("filesets", "rtl0, rtl1"),
        ("jobdir", os.path.abspath("build/testdesign/job0"))
    ]


def test_summary_headers_alias():
    proj = Project(DesignSchema("testdesign"))
    proj.add_dep(DesignSchema("testalias"))
    proj.set("option", "alias", [
        ("testdesign", "rtl", "testalias", "rtl0"),
        ("testdesign", "rtl", "notfound", "rtl1"),
        ("notfound", "rtl", "testdesign", "rtl1"),
        ("testdesign", "rtl", "testalias", "rtl1"),
    ])
    proj.set("option", "fileset", ["rtl0", "rtl1"])
    assert proj._summary_headers() == [
        ("design", "testdesign"),
        ("filesets", "rtl0, rtl1"),
        ("alias", "testdesign (rtl) -> testalias (rtl0), testdesign (rtl) -> testalias (rtl1)"),
        ("jobdir", os.path.abspath("build/testdesign/job0"))
    ]


def test_summary_headers_alias_with_delete_fileset():
    proj = Project(DesignSchema("testdesign"))
    proj.add_dep(DesignSchema("testalias"))
    proj.set("option", "alias", [
        ("testdesign", "rtl", "testalias", None)
    ])
    proj.set("option", "fileset", ["rtl0", "rtl1"])
    assert proj._summary_headers() == [
        ("design", "testdesign"),
        ("filesets", "rtl0, rtl1"),
        ("alias", "testdesign (rtl) -> deleted"),
        ("jobdir", os.path.abspath("build/testdesign/job0"))
    ]


def test_summary_headers_alias_with_delete_dst():
    proj = Project(DesignSchema("testdesign"))
    proj.add_dep(DesignSchema("testalias"))
    proj.set("option", "alias", [
        ("testdesign", "rtl", None, "rtl")
    ])
    proj.set("option", "fileset", ["rtl0", "rtl1"])
    assert proj._summary_headers() == [
        ("design", "testdesign"),
        ("filesets", "rtl0, rtl1"),
        ("alias", "testdesign (rtl) -> deleted"),
        ("jobdir", os.path.abspath("build/testdesign/job0"))
    ]


def test_summary_no_jobs():
    with pytest.raises(ValueError, match="no history to summarize"):
        Project().summary()


def test_summary_select_job():
    proj = Project(DesignSchema("testdesign"))
    proj.set("option", "jobname", "thisjob")
    proj._record_history()
    proj.set("option", "jobname", "thatjob")
    proj._record_history()

    with patch("siliconcompiler.Project.history") as history:
        history.return_value = proj
        proj.summary()

        history.assert_called_once_with("thatjob")


def test_summary_select_job_user():
    proj = Project(DesignSchema("testdesign"))
    proj.set("option", "jobname", "thisjob")
    proj._record_history()
    proj.set("option", "jobname", "thatjob")
    proj._record_history()

    with patch("siliconcompiler.Project.history") as history:
        history.return_value = proj
        proj.summary("thisjob")

        history.assert_called_once_with("thisjob")


def test_summary_select_unknownjob(caplog):
    proj = Project(DesignSchema("testdesign"))
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.WARNING)

    proj.set("option", "jobname", "thisjob")
    proj._record_history()
    proj.set("option", "jobname", "thatjob")
    proj._record_history()
    proj.set("option", "jobname", "job0")

    with patch("siliconcompiler.Project.history") as history:
        history.return_value = proj
        proj.summary()

        history.assert_called_once_with("thatjob")  # will call with first alphabetical job
    assert "job0 not found in history, picking thatjob" in caplog.text


def test_collect_file_verbose(caplog):
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.collect()

    assert f"Collecting files to: {proj.getcollectiondir()}" in caplog.text
    assert f"  Collecting file: {os.path.abspath('top.v')}" in caplog.text


def test_collect_file_not_verbose(caplog):
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("top.v")
    with open("top.v", "w") as f:
        f.write("test")

    proj = Project(design)
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.collect(verbose=False)

    assert caplog.text == ""


def test_collect_file_update():
    # Checks if collected files are properly updated after editing

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_file("fake.v")

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('fake')

    proj = Project(design)
    proj.collect()

    filename = design.get_file(fileset="rtl", filetype="verilog")[0]

    assert len(os.listdir(proj.getcollectiondir())) == 1
    with open(os.path.join(proj.getcollectiondir(), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun collect
    proj.collect()
    assert len(os.listdir(proj.getcollectiondir())) == 1
    with open(os.path.join(proj.getcollectiondir(), os.path.basename(filename)), 'r') as f:
        assert f.readline() == 'newfake'


def test_collect_directory():
    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("testingdir")
            design.add_file("testingdir/test.v")

    os.makedirs('testingdir', exist_ok=True)

    with open('testingdir/test.v', 'w') as f:
        f.write('test')

    proj = Project(design)
    proj.collect()

    assert len(os.listdir(proj.getcollectiondir())) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(proj.getcollectiondir())
    assert os.listdir(path) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(proj.getcollectiondir())


def test_collect_subdirectory():
    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("testingdir")
            design.add_file("testingdir/subdir/test.v")

    os.makedirs('testingdir/subdir', exist_ok=True)

    with open('testingdir/subdir/test.v', 'w') as f:
        f.write('test')

    proj = Project(design)
    proj.collect()

    assert len(os.listdir(proj.getcollectiondir())) == 1

    path = design.get_idir(fileset="rtl")[0]
    assert path.startswith(proj.getcollectiondir())
    assert os.listdir(path) == ['subdir']
    assert os.listdir(os.path.join(path, "subdir")) == ['test.v']
    assert design.get_file(fileset="rtl",
                           filetype="verilog")[0].startswith(proj.getcollectiondir())


def test_collect_file_with_false():
    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=False):
            design.add_file("fake.v")

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('fake')

    proj = Project(design)
    proj.collect()

    # No files should have been collected
    assert len(os.listdir(proj.getcollectiondir())) == 0


def test_collect_file_home(monkeypatch):
    def _mock_home():
        return Path(os.getcwd()) / "home"

    monkeypatch.setattr(Path, 'home', _mock_home)

    _mock_home().mkdir(exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir(str(Path.home()))

    with open(Path.home() / "test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    proj.collect()

    # No files should have been collected
    assert len(os.listdir(proj.getcollectiondir())) == 1
    subdir = os.path.join(proj.getcollectiondir(), os.listdir(proj.getcollectiondir())[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_build():
    os.makedirs('build', exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("build")

    with open("build/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    proj.collect()

    # No files should have been collected
    assert len(os.listdir(proj.getcollectiondir())) == 1
    subdir = os.path.join(proj.getcollectiondir(), os.listdir(proj.getcollectiondir())[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_dir():
    os.makedirs('test/.test', exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test/test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    proj.collect()

    # No files should have been collected
    assert len(os.listdir(proj.getcollectiondir())) == 1
    subdir = os.path.join(proj.getcollectiondir(), os.listdir(proj.getcollectiondir())[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_hidden_file():
    os.makedirs('test', exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open("test/.test.v", "w") as f:
        f.write("test")

    proj = Project(design)
    proj.collect()

    # No files should have been collected
    assert len(os.listdir(proj.getcollectiondir())) == 1
    subdir = os.path.join(proj.getcollectiondir(), os.listdir(proj.getcollectiondir())[0])
    assert len(os.listdir(subdir)) == 0


def test_collect_file_whitelist_error():
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)

    with pytest.raises(RuntimeError, match=".* is not on the approved collection list"):
        proj.collect(whitelist=[os.path.abspath('not_test_folder')])

    assert len(os.listdir(proj.getcollectiondir())) == 0


def test_collect_file_whitelist_pass():
    os.makedirs('test/testing', exist_ok=True)

    # Create instance of design
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        with design._active(copy=True):
            design.add_idir("test")

    with open('test/test', 'w') as f:
        f.write('test')

    proj = Project(design)
    proj.collect(whitelist=[os.path.abspath('test')])

    assert len(os.listdir(proj.getcollectiondir())) == 1


def test_get_task():
    class FauxTask(TaskSchema):
        def tool(self):
            return "faux"

    class FauxTask0(FauxTask):
        def task(self):
            return "task0"

    class FauxTask1(FauxTask):
        def task(self):
            return "task1"

    class FauxTask2(TaskSchema):
        def tool(self):
            return "anotherfaux"

        def task(self):
            return "task1"

    faux0 = FauxTask0()
    faux1 = FauxTask1()
    faux2 = FauxTask2()

    proj = Project()
    EditableSchema(proj).insert("tool", "faux", ToolSchema())
    EditableSchema(proj).insert("tool", "faux", "task", "task0", faux0)
    EditableSchema(proj).insert("tool", "faux", "task", "task1", faux1)
    EditableSchema(proj).insert("tool", "anotherfaux", ToolSchema())
    EditableSchema(proj).insert("tool", "anotherfaux", "task", "task1", faux2)

    assert proj.get_task() == set([faux0, faux1, faux2])
    assert proj.get_task(tool="faux") == set([faux0, faux1])
    assert proj.get_task(task="task1") == set([faux1, faux2])
    assert proj.get_task(tool="faux", task="task1") is faux1
    assert proj.get_task(filter=lambda t: isinstance(t, FauxTask)) == set([faux0, faux1])
    assert proj.get_task(filter=lambda t: isinstance(t, FauxTask2)) is faux2
    assert proj.get_task(filter=FauxTask2) is faux2


def test_get_task_missing():
    assert Project().get_task("tool0", "task0") == set()


def test_get_task_empty():
    assert Project().get_task() == set()


def test_load_target():
    class Target:
        calls = 0

        @staticmethod
        def target(target: Project):
            Target.calls += 1

    proj = Project()

    assert Target.calls == 0
    proj.load_target(Target.target)
    assert Target.calls == 1


def test_load_target_invalid_signature_type():
    def target(target: str):
        pass

    proj = Project()

    with pytest.raises(TypeError, match="target must take in a Project object"):
        proj.load_target(target)


def test_load_target_invalid_signature_required_args():
    def target():
        pass

    proj = Project()

    with pytest.raises(ValueError,
                       match="target signature cannot must take at least one argument"):
        proj.load_target(target)


def test_load_target_invalid_signature_toomany_required_args():
    def target(arg0, arg1):
        pass

    proj = Project()

    with pytest.raises(ValueError,
                       match="target signature cannot have more than one required argument"):
        proj.load_target(target)


def test_load_target_invalid_project():
    class Proj0(Project):
        pass

    class Proj1(Project):
        pass

    def target(arg0: Proj1):
        pass

    proj = Proj0()

    with pytest.raises(TypeError, match="target requires a Proj1 project"):
        proj.load_target(target)


def test_load_target_with_kwargs():
    proj = Project()

    class Target:
        calls = 0

        @staticmethod
        def target(target: Project, arg0: str = "", arg1: int = 1):
            Target.calls += 1
            assert target is proj
            assert arg0 == "test"
            assert arg1 == 2

    assert Target.calls == 0
    proj.load_target(Target.target, arg0="test", arg1=2)
    assert Target.calls == 1


def test_load_target_with_kwargs_incomplete():
    proj = Project()

    class Target:
        calls = 0

        @staticmethod
        def target(target: Project, arg0: str = "", arg1: int = 1):
            Target.calls += 1
            assert target is proj
            assert arg0 == "test"
            assert arg1 == 1

    assert Target.calls == 0
    proj.load_target(Target.target, arg0="test")
    assert Target.calls == 1


def test_load_target_string():
    class Target:
        calls = 0

        @staticmethod
        def target(proj):
            Target.calls += 1

    proj = Project()

    with patch("importlib.import_module") as import_mod:
        import_mod.return_value = Target
        assert Target.calls == 0
        proj.load_target("Target.target")
        import_mod.assert_called_once_with("Target")
        assert Target.calls == 1


def test_load_target_string_invalid():
    proj = Project()
    with pytest.raises(ValueError, match="unable to process incomplete function path"):
        proj.load_target("Target")


def test_getdict_type():
    assert Project._getdict_type() == "Project"


def test_from_dict_restore_deps():
    dep_design = DesignSchema("dep_design")
    design = DesignSchema("testdesign")
    design.add_dep(dep_design)

    proj = Project(design)
    assert proj.getkeys("library") == ("dep_design", "testdesign")
    assert design.has_dep("dep_design")

    new_proj = Project.from_manifest(cfg=proj.getdict())
    assert new_proj.getkeys("library") == ("dep_design", "testdesign")
    new_design = new_proj.get("library", "testdesign", field="schema")
    new_dep_design = new_proj.get("library", "dep_design", field="schema")
    assert new_design is not design
    assert new_dep_design is not dep_design
    assert new_design.has_dep("dep_design")
    assert new_design.get_dep("dep_design") is new_dep_design


def test_find_result_not_setup():
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    with pytest.raises(ValueError, match=r"\[option,fileset\] is not set"):
        proj.find_result("vg", "thisstep")


def test_find_result_no_design():
    proj = Project()
    proj.set("option", "fileset", "rtl")
    with pytest.raises(ValueError, match=r"name has not been set"):
        proj.find_result("vg", "thisstep")


def test_find_result_no_step():
    proj = Project()

    with pytest.raises(ValueError, match="step is required"):
        proj.find_result(filename="balh")


def test_find_result():
    Path("outputs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)

    Path("outputs/top.vg").touch()
    Path("outputs/top.def.gz").touch()
    Path("outputs/other.def").touch()
    Path("reports/top.rpt").touch()
    Path("reports/report_this.rpt").touch()

    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("vg", "thisstep") == os.path.abspath("outputs/top.vg")
        getworkdir.assert_called_once_with("thisstep", "0")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("not", "thisstep") is None
        getworkdir.assert_called_once_with("thisstep", "0")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("vg", "thisstep", index="5") == os.path.abspath("outputs/top.vg")
        getworkdir.assert_called_once_with("thisstep", "5")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("def", "thisstep") == os.path.abspath("outputs/top.def.gz")
        getworkdir.assert_called_once_with("thisstep", "0")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("rpt", "thisstep", directory="reports") == \
            os.path.abspath("reports/top.rpt")
        getworkdir.assert_called_once_with("thisstep", "0")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("rpt", "thisstep", directory="reports",
                                filename="report_this.rpt") \
            == os.path.abspath("reports/report_this.rpt")
        getworkdir.assert_called_once_with("thisstep", "0")

    with patch("siliconcompiler.Project.getworkdir") as getworkdir:
        getworkdir.return_value = os.path.abspath(".")
        assert proj.find_result("thisstep", filename="other.def") == \
            os.path.abspath("outputs/other.def")
        getworkdir.assert_called_once_with("thisstep", "0")
