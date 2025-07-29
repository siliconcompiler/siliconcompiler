import logging
import pickle
import pytest

import os.path

from pathlib import Path

from siliconcompiler import Project
from siliconcompiler import DesignSchema, FlowgraphSchema, TaskSchema

from siliconcompiler.schema import NamedSchema, EditableSchema

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
    proj = Project()
    with pytest.raises(KeyError, match="test0 has not been loaded"):
        proj.add_alias("test0", "rtl", 2, "rtl")


def test_add_alias_src_dep_not_loaded():
    design = DesignSchema("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project()
    with pytest.raises(KeyError, match="test has not been loaded"):
        proj.add_alias(design, "rtl", 2, "rtl")


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
        ("test", "rtl", "", "")
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
        ("test", "rtl", "alias", "")
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
