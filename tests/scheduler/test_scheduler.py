import logging
import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Project, FlowgraphSchema, DesignSchema
from siliconcompiler.scheduler import Scheduler

from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def remove_display_environment():
    names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
    return {k: v for k, v in os.environ.items() if k not in names_to_remove}


@pytest.fixture
def basic_project():
    flow = FlowgraphSchema("test")
    flow.node("stepone", NOPTask())
    design = DesignSchema("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


def test_init_no_flow():
    with pytest.raises(ValueError, match="flow must be specified"):
        Scheduler(Project(DesignSchema("testdesign")))


def test_init_flow_not_defined(basic_project):
    basic_project.set("option", "flow", "testflow")
    with pytest.raises(ValueError, match="flow is not defined"):
        Scheduler(basic_project)


def test_init_flow_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.FlowgraphSchema.validate") as call:
        call.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_project)


def test_init_flow_runtime_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.FlowgraphSchema.validate") as call0, \
         patch("siliconcompiler.flowgraph.RuntimeFlowgraph.validate") as call1:
        call0.return_value = True
        call1.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_project)


def test_check_display_run(basic_project):
    # Checks if check_display() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_display",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(basic_project, remove_display_environment, caplog):
    # Checks if the nodisplay option is set
    # On linux system without display
    setattr(basic_project, "_Project__logger", logging.getLogger())
    basic_project.logger.setLevel(logging.INFO)

    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is True
    assert "Environment variable $DISPLAY or $WAYLAND_DISPLAY not set" in caplog.text
    assert "Setting [option,nodisplay] to True" in caplog.text


@patch('sys.platform', 'linux')
@pytest.mark.parametrize("env,value", [("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")])
def test_check_display_with_display(basic_project, remove_display_environment, env, value):
    # Checks that the nodisplay option is not set
    # On linux system with display

    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    remove_display_environment[env] = value
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


@patch('sys.platform', 'darwin')
def test_check_display_with_display_macos(basic_project, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On macos system
    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


@patch('sys.platform', 'win32')
def test_check_display_with_display_windows(basic_project, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On windows system
    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


def test_increment_job_name_run(basic_project):
    # Checks if __increment_job_name() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__increment_job_name",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


def test_increment_job_name_with_cleanout(basic_project):
    basic_project.set('option', 'clean', False)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_with_clean_but_not_increment(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', False)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_default(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)

    assert basic_project.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_project.get("option", "jobname") == "job1"


def test_increment_job_name_default_no_dir(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_project)

    assert basic_project.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is False
    assert basic_project.get("option", "jobname") == "job0"


@pytest.mark.parametrize("prev_name,new_name", [
    ("test0", "test1"),
    ("test00", "test1"),
    ("test10", "test11"),
    ("test", "test1"),
    ("junkname0withnumbers1", "junkname0withnumbers2")
])
def test_increment_job_name(basic_project, prev_name, new_name):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    basic_project.set('option', 'jobname', prev_name)
    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)

    assert basic_project.get("option", "jobname") == prev_name
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_project.get("option", "jobname") == new_name


def test_clean_build_dir(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_called_once()


def test_clean_build_dir_with_from(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'from', 'stepone')

    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)
    assert os.path.isdir(basic_project.getworkdir())

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_clean_build_dir_do_nothing(basic_project):
    basic_project.set('option', 'clean', False)

    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_clean_build_dir_remote(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('record', 'remoteid', 'blah')

    scheduler = Scheduler(basic_project)

    os.makedirs(basic_project.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_check_manifest_pass(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = True
        scheduler.run()
        call.assert_called_once()


def test_check_manifest_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = False
        with pytest.raises(RuntimeError, match='check_manifest\\(\\) failed'):
            scheduler.run()
        call.assert_called_once()
