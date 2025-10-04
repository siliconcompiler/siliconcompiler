import logging
import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.scheduler import Scheduler

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir


@pytest.fixture
def gcd_nop_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("stepthree", NOPTask())
    flow.node("stepfour", NOPTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    flow.edge("stepthree", "stepfour")
    project.set_flow(flow)

    return project


@pytest.fixture
def remove_display_environment():
    names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
    return {k: v for k, v in os.environ.items() if k not in names_to_remove}


@pytest.fixture
def basic_project():
    flow = Flowgraph("test")
    flow.node("stepone", NOPTask())
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


@pytest.fixture
def basic_project_no_flow():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")

    return proj


def test_init_no_flow():
    with pytest.raises(ValueError, match="flow must be specified"):
        Scheduler(Project(Design("testdesign")))


def test_init_flow_not_defined(basic_project):
    basic_project.set("option", "flow", "testflow")
    with pytest.raises(ValueError, match="flow is not defined"):
        Scheduler(basic_project)


def test_init_flow_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call:
        call.return_value = False
        with pytest.raises(ValueError, match=r"test flowgraph contains errors and cannot be run\."):
            Scheduler(basic_project)


def test_init_flow_runtime_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call0, \
         patch("siliconcompiler.flowgraph.RuntimeFlowgraph.validate") as call1:
        call0.return_value = True
        call1.return_value = False
        with pytest.raises(ValueError, match=r"test flowgraph contains errors and cannot be run\."):
            Scheduler(basic_project)


def test_check_display_run(basic_project):
    # Checks if check_display() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_display",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(basic_project, remove_display_environment, monkeypatch, caplog):
    # Checks if the nodisplay option is set
    # On linux system without display
    monkeypatch.setattr(basic_project, "_Project__logger", logging.getLogger())
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

    os.makedirs(jobdir(basic_project), exist_ok=True)

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

    os.makedirs(jobdir(basic_project), exist_ok=True)

    assert basic_project.get("option", "jobname") == prev_name
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_project.get("option", "jobname") == new_name


def test_clean_build_dir_full(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_called_once()
        remove.assert_called_once()

# ... rest of unchanged tests ...


def test_run_setup_with_flow_reset(gcd_nop_project, monkeypatch):
    """Test that SchedulerFlowReset in __run_setup triggers full clean and marks all pending"""
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.DEBUG)

    gcd_nop_project.set('option', 'to', ['steptwo'])
    assert gcd_nop_project.run()

    flow = Flowgraph("differentflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    gcd_nop_project.set_flow(flow)

    with patch(
        "siliconcompiler.scheduler.Scheduler._Scheduler__clean_build_dir_full"
    ) as clean_mock:
        assert gcd_nop_project.run()
        clean_mock.assert_any_call(recheck=True)


def test_run_setup_flow_reset_marks_all_pending(gcd_nop_project):
    """Test that SchedulerFlowReset marks all nodes as pending"""
    gcd_nop_project.set('option', 'to', ['steptwo'])
    assert gcd_nop_project.run()

    assert gcd_nop_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS

    flow = Flowgraph("newflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("stepthree", NOPTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    gcd_nop_project.set_flow(flow)

    assert gcd_nop_project.run()

    assert gcd_nop_project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.get(
        "record", "status", step="stepthree", index="0"
    ) == NodeStatus.SUCCESS


def test_run_setup_flow_reset_interrupts_replay(gcd_nop_project):
    """Test that SchedulerFlowReset interrupts the replay logic"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    assert gcd_nop_project.run()

    def mock_requires_run(_self):
        raise SchedulerFlowReset

    flow = Flowgraph("newflow")
    flow.node("stepone", NOPTask())
    gcd_nop_project.set_flow(flow)

    with patch("siliconcompiler.scheduler.SchedulerNode.requires_run", mock_requires_run):
        assert gcd_nop_project.run()


def test_run_clean_order(basic_project):
    """Test that run() calls clean methods in correct order"""
    scheduler = Scheduler(basic_project)

    call_order = []

    def track_clean_full():
        call_order.append('clean_full')

    def track_install_logger():
        call_order.append('install_logger')

    def track_clean_incr():
        call_order.append('clean_incr')

    with patch.object(scheduler, '_Scheduler__clean_build_dir_full', track_clean_full), \
         patch.object(scheduler, '_Scheduler__install_file_logger', track_install_logger), \
         patch.object(scheduler, '_Scheduler__clean_build_dir_incr', track_clean_incr):
        scheduler.run()

    assert 'clean_full' in call_order
    assert 'install_logger' in call_order
    assert 'clean_incr' in call_order
    assert call_order.index('clean_full') < call_order.index('install_logger')
    assert call_order.index('install_logger') < call_order.index('clean_incr')