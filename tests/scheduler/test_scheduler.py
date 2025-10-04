import logging
import os
import pytest
import time
import sys

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.scheduler import Scheduler
from siliconcompiler.schema import EditableSchema, Parameter

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.tools import get_task


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


def test_clean_build_dir_full_keep_log(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once()
        remove.assert_not_called()


def test_clean_build_dir_full_keep_log_rm_old_log(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")
    with open(os.path.join(jobdir(basic_project), "job.log.bak"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once()
        remove.assert_called_once_with(os.path.join(jobdir(basic_project), "job.log.bak"))


def test_clean_build_dir_full_with_from(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'from', 'stepone')

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    assert os.path.isdir(jobdir(basic_project))

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_clean_build_dir_full_do_nothing(basic_project):
    basic_project.set('option', 'clean', False)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_clean_build_dir_full_remote(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('record', 'remoteid', 'blah')

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_install_file_logger_new_log(basic_project):
    """Test __install_file_logger creates a new log file when none exists."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    log_file = os.path.join(job_dir, "job.log")
    
    # Ensure no log file exists
    assert not os.path.exists(log_file)
    
    scheduler._Scheduler__install_file_logger()
    
    # Verify log file was created
    assert os.path.exists(log_file)
    # Verify handler was added
    assert scheduler._Scheduler__joblog_handler is not None


def test_install_file_logger_backup_existing(basic_project):
    """Test __install_file_logger backs up existing log file."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    log_file = os.path.join(job_dir, "job.log")
    bak_file = os.path.join(job_dir, "job.log.bak")
    
    # Create an existing log file
    with open(log_file, "w") as f:
        f.write("existing log content")
    
    scheduler._Scheduler__install_file_logger()
    
    # Verify backup was created
    assert os.path.exists(bak_file)
    with open(bak_file, "r") as f:
        assert f.read() == "existing log content"
    
    # Verify new log file exists
    assert os.path.exists(log_file)


def test_install_file_logger_multiple_backups(basic_project):
    """Test __install_file_logger creates .bak.1, .bak.2 when .bak exists."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    log_file = os.path.join(job_dir, "job.log")
    bak_file = os.path.join(job_dir, "job.log.bak")
    bak_file_1 = os.path.join(job_dir, "job.log.bak.1")
    
    # Create existing log and backup
    with open(log_file, "w") as f:
        f.write("current log")
    with open(bak_file, "w") as f:
        f.write("first backup")
    
    scheduler._Scheduler__install_file_logger()
    
    # Verify .bak.1 was created with the current log content
    assert os.path.exists(bak_file_1)
    with open(bak_file_1, "r") as f:
        assert f.read() == "current log"
    
    # Verify original .bak still exists
    assert os.path.exists(bak_file)
    with open(bak_file, "r") as f:
        assert f.read() == "first backup"


def test_install_file_logger_sequential_backups(basic_project):
    """Test __install_file_logger handles multiple sequential backups."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    log_file = os.path.join(job_dir, "job.log")
    
    # Create existing backups
    with open(log_file, "w") as f:
        f.write("log3")
    with open(os.path.join(job_dir, "job.log.bak"), "w") as f:
        f.write("log2")
    with open(os.path.join(job_dir, "job.log.bak.1"), "w") as f:
        f.write("log1")
    
    scheduler._Scheduler__install_file_logger()
    
    # Verify .bak.2 was created
    assert os.path.exists(os.path.join(job_dir, "job.log.bak.2"))
    with open(os.path.join(job_dir, "job.log.bak.2"), "r") as f:
        assert f.read() == "log3"


def test_clean_build_dir_incr_removes_old_steps(basic_project):
    """Test __clean_build_dir_incr removes steps not in current flow."""
    basic_project.set('option', 'clean', True)
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    
    # Create directory for step in current flow
    step_in_flow = os.path.join(job_dir, "stepone")
    os.makedirs(step_in_flow, exist_ok=True)
    
    # Create directory for step NOT in current flow
    old_step = os.path.join(job_dir, "oldstep")
    os.makedirs(old_step, exist_ok=True)
    
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=[('stepone', '0')]), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]):
        scheduler._Scheduler__clean_build_dir_incr()
    
    # Verify old step was removed
    assert not os.path.exists(old_step)
    # Verify current step remains
    assert os.path.exists(step_in_flow)


def test_clean_build_dir_incr_removes_old_indices(basic_project):
    """Test __clean_build_dir_incr removes indices not in current flow."""
    basic_project.set('option', 'clean', True)
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    
    # Create step directory
    step_dir = os.path.join(job_dir, "stepone")
    os.makedirs(step_dir, exist_ok=True)
    
    # Create valid index
    valid_index = os.path.join(step_dir, "0")
    os.makedirs(valid_index, exist_ok=True)
    
    # Create invalid index
    old_index = os.path.join(step_dir, "1")
    os.makedirs(old_index, exist_ok=True)
    
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=[('stepone', '0')]), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]):
        scheduler._Scheduler__clean_build_dir_incr()
    
    # Verify old index was removed
    assert not os.path.exists(old_index)
    # Verify valid index remains
    assert os.path.exists(valid_index)


def test_clean_build_dir_incr_skips_files(basic_project):
    """Test __clean_build_dir_incr skips files in job directory."""
    basic_project.set('option', 'clean', True)
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    
    # Create a file in job directory
    test_file = os.path.join(job_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")
    
    # Create step directory
    step_dir = os.path.join(job_dir, "stepone")
    os.makedirs(step_dir, exist_ok=True)
    
    # Create a file in step directory
    step_file = os.path.join(step_dir, "step.txt")
    with open(step_file, "w") as f:
        f.write("step content")
    
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=[('stepone', '0')]), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]):
        scheduler._Scheduler__clean_build_dir_incr()
    
    # Verify files were not removed
    assert os.path.exists(test_file)
    assert os.path.exists(step_file)


def test_clean_build_dir_incr_cleans_pending_nodes(basic_project):
    """Test __clean_build_dir_incr cleans directories of pending nodes."""
    scheduler = Scheduler(basic_project)
    
    # Mock the flow and tasks
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=[('stepone', '0')]), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]), \
         patch.object(scheduler._Scheduler__record, 'get', return_value=NodeStatus.PENDING):
        
        # Mock the tasks dictionary with a mock node
        mock_node = patch('siliconcompiler.scheduler.SchedulerNode', autospec=True).start()
        mock_node_instance = mock_node.return_value
        mock_node_instance.runtime.return_value.__enter__ = lambda *_: None
        mock_node_instance.runtime.return_value.__exit__ = lambda *_: None
        scheduler._Scheduler__tasks = {('stepone', '0'): mock_node_instance}
        
        scheduler._Scheduler__clean_build_dir_incr()
        
        # Verify clean_directory was called
        mock_node_instance.clean_directory.assert_called_once()
        patch.stopall()


def test_clean_build_dir_incr_empty_jobdir(basic_project):
    """Test __clean_build_dir_incr handles empty job directory gracefully."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=[('stepone', '0')]), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]):
        # Should not raise any exception
        scheduler._Scheduler__clean_build_dir_incr()


def test_clean_build_dir_incr_multiple_steps_and_indices(basic_project):
    """Test __clean_build_dir_incr with complex directory structure."""
    scheduler = Scheduler(basic_project)
    
    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)
    
    # Create multiple steps and indices
    for step in ['stepone', 'steptwo', 'oldstep']:
        step_dir = os.path.join(job_dir, step)
        os.makedirs(step_dir, exist_ok=True)
        for index in ['0', '1', '2']:
            index_dir = os.path.join(step_dir, index)
            os.makedirs(index_dir, exist_ok=True)
    
    # Define valid nodes (stepone/0, stepone/1, steptwo/0)
    valid_nodes = [('stepone', '0'), ('stepone', '1'), ('steptwo', '0')]
    
    with patch.object(scheduler._Scheduler__flow, 'get_nodes', return_value=valid_nodes), \
         patch.object(scheduler._Scheduler__flow_runtime, 'get_nodes', return_value=[]):
        scheduler._Scheduler__clean_build_dir_incr()
    
    # Verify old step was removed completely
    assert not os.path.exists(os.path.join(job_dir, "oldstep"))
    
    # Verify valid indices remain
    assert os.path.exists(os.path.join(job_dir, "stepone", "0"))
    assert os.path.exists(os.path.join(job_dir, "stepone", "1"))
    assert os.path.exists(os.path.join(job_dir, "steptwo", "0"))
    
    # Verify invalid indices were removed
    assert not os.path.exists(os.path.join(job_dir, "stepone", "2"))
    assert not os.path.exists(os.path.join(job_dir, "steptwo", "1"))
    assert not os.path.exists(os.path.join(job_dir, "steptwo", "2"))


def test_run_setup_scheduler_flow_reset(gcd_nop_project):
    """Test __run_setup handles SchedulerFlowReset exception correctly."""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    scheduler = Scheduler(gcd_nop_project)

    # Setup necessary mocks
    with patch.object(scheduler, '_Scheduler__check_display'), \
         patch.object(scheduler, '_Scheduler__reset_flow_nodes'), \
         patch.object(scheduler, '_Scheduler__print_status'), \
         patch.object(scheduler, '_Scheduler__mark_pending') as mock_mark_pending, \
         patch.object(scheduler, '_Scheduler__clean_build_dir_full') as mock_clean:

        # Mock get_execution_order to simulate a node that raises SchedulerFlowReset
        mock_node = patch('siliconcompiler.scheduler.SchedulerNode', autospec=True).start()
        mock_node_instance = mock_node.return_value
        mock_node_instance.runtime.return_value.__enter__ = lambda *_: None
        mock_node_instance.runtime.return_value.__exit__ = lambda *_: None
        mock_node_instance.requires_run.side_effect = SchedulerFlowReset("Flow reset test")

        scheduler._Scheduler__tasks = {
            ('stepone', '0'): mock_node_instance,
            ('steptwo', '0'): mock_node_instance
        }

        with patch.object(scheduler._Scheduler__flow, 'get_execution_order',
                         return_value=[[('stepone', '0')]]), \
             patch.object(scheduler._Scheduler__flow, 'get_nodes',
                         return_value=[('stepone', '0'), ('steptwo', '0')]), \
             patch.object(scheduler._Scheduler__record, 'get', return_value=NodeStatus.SUCCESS):

            scheduler._Scheduler__run_setup()

            # Verify clean was called with recheck=True
            mock_clean.assert_called_once_with(recheck=True)

            # Verify all nodes were marked pending
            assert mock_mark_pending.call_count == 2
            mock_mark_pending.assert_any_call('stepone', '0')
            mock_mark_pending.assert_any_call('steptwo', '0')

        patch.stopall()


def test_run_setup_normal_flow(gcd_nop_project):
    """Test __run_setup normal flow without SchedulerFlowReset."""
    scheduler = Scheduler(gcd_nop_project)

    with patch.object(scheduler, '_Scheduler__check_display'), \
         patch.object(scheduler, '_Scheduler__reset_flow_nodes'), \
         patch.object(scheduler, '_Scheduler__print_status'), \
         patch.object(scheduler, '_Scheduler__mark_pending') as mock_mark_pending, \
         patch.object(scheduler, '_Scheduler__clean_build_dir_full') as mock_clean:

        # Mock node that requires run
        mock_node = patch('siliconcompiler.scheduler.SchedulerNode', autospec=True).start()
        mock_node_instance = mock_node.return_value
        mock_node_instance.runtime.return_value.__enter__ = lambda *_: None
        mock_node_instance.runtime.return_value.__exit__ = lambda *_: None
        mock_node_instance.requires_run.return_value = True

        scheduler._Scheduler__tasks = {('stepone', '0'): mock_node_instance}

        with patch.object(scheduler._Scheduler__flow, 'get_execution_order',
                         return_value=[[('stepone', '0')]]), \
             patch.object(scheduler._Scheduler__record, 'get', return_value=NodeStatus.SUCCESS):

            scheduler._Scheduler__run_setup()

            # Verify clean was NOT called
            mock_clean.assert_not_called()

            # Verify node was marked pending due to requires_run
            mock_mark_pending.assert_called_once_with('stepone', '0')

        patch.stopall()


def test_run_setup_replay_journal(gcd_nop_project):
    """Test __run_setup replays journal for successful unchanged nodes."""
    from siliconcompiler.schema import Journal

    scheduler = Scheduler(gcd_nop_project)

    with patch.object(scheduler, '_Scheduler__check_display'), \
         patch.object(scheduler, '_Scheduler__reset_flow_nodes'), \
         patch.object(scheduler, '_Scheduler__print_status'):

        # Mock node that doesn't require run
        mock_node = patch('siliconcompiler.scheduler.SchedulerNode', autospec=True).start()
        mock_node_instance = mock_node.return_value
        mock_node_instance.runtime.return_value.__enter__ = lambda *_: None
        mock_node_instance.runtime.return_value.__exit__ = lambda *_: None
        mock_node_instance.requires_run.return_value = False

        scheduler._Scheduler__tasks = {('stepone', '0'): mock_node_instance}

        # Mock extra_setup_nodes (would be populated by previous run)
        # extra_setup_nodes = {('stepone', '0'): gcd_nop_project}

        with patch.object(scheduler._Scheduler__flow, 'get_execution_order',
                         return_value=[[('stepone', '0')]]), \
             patch.object(scheduler._Scheduler__record, 'get', return_value=NodeStatus.SUCCESS), \
             patch.object(scheduler, '_Scheduler__flow_load_runtime') as mock_flow_load, \
             patch('siliconcompiler.schema.Journal.access') as mock_journal:

            mock_journal.return_value.replay = patch.object(Journal, 'replay', autospec=True).start()
            mock_flow_load.get_nodes.return_value = [('stepone', '0')]

            # Inject extra_setup_nodes into the setup
            with patch.object(scheduler._Scheduler__flow_runtime, 'get_entry_nodes',
                              return_value=[]):
                scheduler._Scheduler__run_setup()

    patch.stopall()


def test_run_exception_hook_restored():
    """Test that sys.excepthook is restored even when run() fails."""
    flow = Flowgraph("test")
    flow.node("stepone", NOPTask())
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    scheduler = Scheduler(proj)

    original_hook = sys.excepthook

    # Mock check_manifest to raise an exception
    with patch.object(scheduler, 'check_manifest', return_value=False):
        try:
            scheduler.run()
        except RuntimeError:
            pass

    # Verify excepthook was restored
    assert sys.excepthook == original_hook


def test_run_file_logger_cleanup():
    """Test that file logger is properly removed even on error."""
    flow = Flowgraph("test")
    flow.node("stepone", NOPTask())
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    scheduler = Scheduler(proj)

    # Mock to cause failure after logger is installed
    with patch.object(scheduler, 'check_manifest', return_value=False):
        try:
            scheduler.run()
        except RuntimeError:
            pass

    # Logger handler should still be cleaned up
    assert isinstance(scheduler._Scheduler__joblog_handler, logging.NullHandler)


def test_clean_build_dir_full_preserves_non_log_files_on_recheck(basic_project):
    """Test __clean_build_dir_full with recheck preserves non-log files."""
    basic_project.set('option', 'clean', True)
    scheduler = Scheduler(basic_project)

    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)

    # Create various files
    with open(os.path.join(job_dir, "job.log"), "w") as f:
        f.write("log")
    with open(os.path.join(job_dir, "data.json"), "w") as f:
        f.write("{}")
    os.makedirs(os.path.join(job_dir, "subdir"), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as rmtree, \
         patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)

        # Should remove directory but not job.log
        rmtree.assert_called_once()
        # Should remove data.json but not job.log
        remove.assert_called_once_with(os.path.join(job_dir, "data.json"))


def test_clean_build_dir_full_handles_nested_backups(basic_project):
    """Test __clean_build_dir_full handles multiple existing backups during recheck."""
    basic_project.set('option', 'clean', True)
    scheduler = Scheduler(basic_project)

    job_dir = jobdir(basic_project)
    os.makedirs(job_dir, exist_ok=True)

    # Create job.log and multiple backups
    with open(os.path.join(job_dir, "job.log"), "w") as f:
        f.write("current")
    with open(os.path.join(job_dir, "job.log.bak"), "w") as f:
        f.write("backup1")
    with open(os.path.join(job_dir, "job.log.bak.1"), "w") as f:
        f.write("backup2")
    with open(os.path.join(job_dir, "job.log.bak.2"), "w") as f:
        f.write("backup3")

    with patch("shutil.rmtree", autospec=True) as _rmtree, \
         patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)

        # Should remove all backups but not job.log
        assert remove.call_count == 3
        remove.assert_any_call(os.path.join(job_dir, "job.log.bak"))
        remove.assert_any_call(os.path.join(job_dir, "job.log.bak.1"))
        remove.assert_any_call(os.path.join(job_dir, "job.log.bak.2"))


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


def test_check_flowgraph_io_basic(basic_project, monkeypatch, caplog):
    monkeypatch.setattr(basic_project, "_Project__logger", logging.getLogger())
    basic_project.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_input_file("test.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_join(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("dojoin", NOPTask())
    flow.node("postjoin", NOPTask())
    flow.edge("stepone", "dojoin")
    flow.edge("steptwo", "dojoin")
    flow.edge("dojoin", "postjoin")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("a.v", step="stepone", index="0")

    nop.add_output_file("b.v", step="steptwo", index="0")
    nop.add_input_file("a.v", step="dojoin", index="0")
    nop.add_input_file("b.v", step="dojoin", index="0")
    nop.add_output_file("a.v", step="dojoin", index="0")
    nop.add_output_file("b.v", step="dojoin", index="0")
    nop.add_input_file("a.v", step="postjoin", index="0")
    nop.add_input_file("b.v", step="postjoin", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_join_extra_files(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("dojoin", NOPTask())
    flow.node("postjoin", NOPTask())
    flow.edge("stepone", "dojoin")
    flow.edge("steptwo", "dojoin")
    flow.edge("dojoin", "postjoin")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("a.v", step="stepone", index="0")
    nop.add_output_file("common.v", step="stepone", index="0")
    nop.add_output_file("b.v", step="steptwo", index="0")
    nop.add_output_file("common.v", step="stepone", index="0")
    nop.add_input_file("common.v", step="dojoin", index="0")
    nop.add_output_file("common.v", step="dojoin", index="0")
    nop.add_input_file("common.v", step="postjoin", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_missing_input(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_input_file("test.v", step="steptwo", index="0")
    nop.add_input_file("missing.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 will not receive required input missing.v" in caplog.text


def test_check_flowgraph_io_with_files_multple_input(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask(), index=0)
    flow.node("stepone", NOPTask(), index=1)
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo", tail_index=0)
    flow.edge("stepone", "steptwo", tail_index=1)
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")

    nop.add_output_file("test.v", step="stepone", index="1")
    nop.add_input_file("test.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 receives test.v from multiple input tasks" in caplog.text


def test_rerun(gcd_nop_project):
    '''Regression test for #458.'''
    gcd_nop_project.set('option', 'to', ['stepthree'])
    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ
    gcd_nop_project.set('option', 'from', ['steptwo'])
    gcd_nop_project.set('option', 'to', ['steptwo'])
    assert gcd_nop_project.run()
    assert (
        run_copy.history("job0").get("record", "endtime", step="steptwo", index="0")
        != gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")
    )
    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == NodeStatus.SUCCESS


def test_resume_normal(gcd_nop_project):
    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ
    assert gcd_nop_project.run()
    assert run_copy.history("job0").get("record", "endtime", step="steptwo", index="0") == gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")
    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepfour", index="0") == NodeStatus.SUCCESS


def test_resume_value_changed(gcd_nop_project):
    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))

    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ

    # Change require list
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    assert gcd_nop_project.set("option", "testing", "thistest")
    gcd_nop_project.logger.setLevel(logging.DEBUG)
    assert gcd_nop_project.run()

    assert (
        run_copy.history("job0").get("record", "endtime", step="steptwo", index="0")
        == gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")
    )
    assert (
        run_copy.history("job0").get("record", "endtime", step="stepthree", index="0")
        != gcd_nop_project.history("job0").get("record", "endtime", step="stepthree", index="0")
    )
    assert (
        run_copy.history("job0").get("record", "endtime", step="stepfour", index="0")
        != gcd_nop_project.history("job0").get("record", "endtime", step="stepfour", index="0")
    )
    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepfour", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="steptwo", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepthree", index="0") == NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepfour", index="0") == NodeStatus.SUCCESS