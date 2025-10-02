import logging
import pickle
import pytest

import os.path

from pathlib import Path
from PIL import Image

from unittest.mock import patch

from siliconcompiler import Project
from siliconcompiler import Lint, Sim
from siliconcompiler import Design, Flowgraph, Checklist
from siliconcompiler import Task
from siliconcompiler.library import LibrarySchema

from siliconcompiler.schema import NamedSchema, EditableSchema, Parameter, Scope
from siliconcompiler.schema_support.option import OptionSchema

from siliconcompiler.utils.logging import SCColorLoggerFormatter, SCLoggerFormatter
from siliconcompiler.utils.paths import jobdir

from siliconcompiler.project import SCColorLoggerFormatter as dut_sc_color_logger


class FauxTask0(Task):
    def tool(self):
        return "tool0"

    def task(self):
        return "task0"


class FauxTask1(Task):
    def tool(self):
        return "tool1"

    def task(self):
        return "task1"


class FauxTask2(Task):
    def tool(self):
        return "tool1"

    def task(self):
        return "task2"


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
    assert Project()._Project__cwd == os.path.abspath(".")


def test_option():
    proj = Project()
    assert isinstance(proj.option, OptionSchema)
    assert proj.get("option", field="schema") is proj.option


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
    assert Project(Design("testname")).name == "testname"


def test_name_set_from_set_design():
    project = Project()
    assert project.name is None
    project.set_design("testname")
    assert project.name == "testname"


def test_design_not_set():
    with pytest.raises(ValueError, match="^design name is not set$"):
        Project().design


def test_design_not_imported():
    with pytest.raises(KeyError, match="^'testname design has not been loaded'$"):
        Project("testname").design


def test_design():
    design = Design("testname")
    project = Project(design)

    assert project.design is design


def test_set_design_str():
    project = Project("oldname")
    assert project.name == "oldname"
    project.set_design("testname")
    assert project.name == "testname"


def test_set_design_not_valid():
    with pytest.raises(TypeError, match="^design must be a string or a Design object$"):
        Project().set_design(2)


def test_set_design_obj():
    project = Project("oldname")
    assert project.name == "oldname"

    design = Design("testname")
    project.set_design(design)
    assert project.name == "testname"
    assert project.design is design


def test_set_flow_str():
    project = Project()
    project.set_flow("testflow")
    assert project.get("option", "flow") == "testflow"


def test_set_flow_not_valid():
    with pytest.raises(TypeError, match="^flow must be a string or a Flowgraph object$"):
        Project().set_flow(2)


def test_set_flow_obj():
    project = Project()
    flow = Flowgraph("testflow")
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


def test_record_history_warn(monkeypatch, caplog):
    proj = Project("testname")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
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
    with pytest.raises(KeyError, match="^'job0 is not a valid job'$"):
        Project().history("job0")


def test_add_fileset():
    design = Design("test")
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
    design = Design("test")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    with design.active_fileset("rtl.other"):
        design.set_topmodule("top2")
    proj = Project(design)
    assert proj.add_fileset(["rtl", "rtl.other"])
    assert proj.get("option", "fileset") == ["rtl", "rtl.other"]


def test_add_fileset_list_invalid():
    design = Design("test")
    proj = Project(design)
    with pytest.raises(TypeError,
                       match="^fileset must be a string or a list/tuple/set of strings$"):
        proj.add_fileset(["rtl", 1])


def test_add_fileset_clobber():
    design = Design("test")
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
    design = Design("test")
    proj = Project(design)
    with pytest.raises(TypeError,
                       match="^fileset must be a string or a list/tuple/set of strings$"):
        proj.add_fileset(1)


def test_add_fileset_invalid():
    design = Design("test")
    proj = Project(design)
    with pytest.raises(ValueError, match="^rtl is not a valid fileset in test$"):
        proj.add_fileset("rtl")


def test_convert():
    class ASIC(Project):
        def __init__(self, design=None):
            super().__init__(design)

            EditableSchema(self).insert("asic", Parameter("str"))

    class FPGA(Project):
        def __init__(self, design=None):
            super().__init__(design)

            EditableSchema(self).insert("fpga", Parameter("str"))

    design = Design("design0")
    proj0 = ASIC(design)

    proj1 = FPGA.convert(proj0)

    assert proj0.allkeys("library") == proj1.allkeys("library")
    assert proj0.allkeys("library") == proj1.allkeys("library")


def test_convert_invalid():
    with pytest.raises(TypeError, match="^source object must be a Project$"):
        Project.convert("this")


def test_add_dep_design():
    design = Design("test")
    proj = Project()
    proj.add_dep(design)
    assert proj.getkeys("library") == ("test",)
[…]

def test_init_logger_name_uniqueness():
    """Each project should get a unique logger name."""
    proj1 = Project()
    proj2 = Project()
    assert proj1.logger.name != proj2.logger.name
    assert proj1.logger.name.startswith("siliconcompiler.project_")
    assert proj2.logger.name.startswith("siliconcompiler.project_")
# (Remaining lines unchanged)