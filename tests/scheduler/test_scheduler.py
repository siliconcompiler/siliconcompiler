import logging
import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Chip, Flow
from siliconcompiler.scheduler import Scheduler

from siliconcompiler.tools.builtin import nop


@pytest.fixture
def remove_display_environment():
    names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
    return {k: v for k, v in os.environ.items() if k not in names_to_remove}


@pytest.fixture
def basic_chip():
    chip = Chip('test')

    flow = Flow('test')
    flow.node('test', 'stepone', nop)
    chip.use(flow)
    chip.set('option', 'flow', 'test')

    return chip


def test_init_no_flow():
    with pytest.raises(ValueError, match="flow must be specified"):
        Scheduler(Chip('test'))


def test_init_flow_not_defined():
    chip = Chip('test')
    chip.set("option", "flow", "test")
    with pytest.raises(ValueError, match="flow is not defined"):
        Scheduler(chip)


def test_init_flow_not_valid(basic_chip):
    with patch("siliconcompiler.flowgraph.FlowgraphSchema.validate") as call:
        call.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_chip)


def test_init_flow_runtime_not_valid(basic_chip):
    with patch("siliconcompiler.flowgraph.FlowgraphSchema.validate") as call0, \
         patch("siliconcompiler.flowgraph.RuntimeFlowgraph.validate") as call1:
        call0.return_value = True
        call1.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_chip)


def test_check_display_run(basic_chip):
    # Checks if check_display() is called during run()
    scheduler = Scheduler(basic_chip)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_display",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(gcd_chip, remove_display_environment, caplog):
    # Checks if the nodisplay option is set
    # On linux system without display
    gcd_chip.logger = logging.getLogger()
    gcd_chip.logger.setLevel(logging.INFO)

    gcd_chip.set("option", "nodisplay", False)
    assert gcd_chip.get('option', 'nodisplay') is False

    scheduler = Scheduler(gcd_chip)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert gcd_chip.get('option', 'nodisplay') is True
    assert "Environment variable $DISPLAY or $WAYLAND_DISPLAY not set" in caplog.text
    assert "Setting [option,nodisplay] to True" in caplog.text


@patch('sys.platform', 'linux')
@pytest.mark.parametrize("env,value", [("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")])
def test_check_display_with_display(gcd_chip, remove_display_environment, env, value):
    # Checks that the nodisplay option is not set
    # On linux system with display

    gcd_chip.set("option", "nodisplay", False)
    assert gcd_chip.get('option', 'nodisplay') is False

    scheduler = Scheduler(gcd_chip)
    remove_display_environment[env] = value
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert gcd_chip.get('option', 'nodisplay') is False


@patch('sys.platform', 'darwin')
def test_check_display_with_display_macos(gcd_chip, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On macos system
    gcd_chip.set("option", "nodisplay", False)
    assert gcd_chip.get('option', 'nodisplay') is False

    scheduler = Scheduler(gcd_chip)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert gcd_chip.get('option', 'nodisplay') is False


@patch('sys.platform', 'win32')
def test_check_display_with_display_windows(gcd_chip, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On windows system
    gcd_chip.set("option", "nodisplay", False)
    assert gcd_chip.get('option', 'nodisplay') is False

    scheduler = Scheduler(gcd_chip)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert gcd_chip.get('option', 'nodisplay') is False


def test_increment_job_name_run(basic_chip):
    # Checks if __increment_job_name() is called during run()
    scheduler = Scheduler(basic_chip)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__increment_job_name",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


def test_increment_job_name_with_cleanout(basic_chip):
    basic_chip.set('option', 'clean', False)

    scheduler = Scheduler(basic_chip)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_with_clean_but_not_increment(basic_chip):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('option', 'jobincr', False)

    scheduler = Scheduler(basic_chip)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_default(basic_chip):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)

    assert basic_chip.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_chip.get("option", "jobname") == "job1"


def test_increment_job_name_default_no_dir(basic_chip):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_chip)

    assert basic_chip.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is False
    assert basic_chip.get("option", "jobname") == "job0"


@pytest.mark.parametrize("prev_name,new_name", [
    ("test0", "test1"),
    ("test00", "test1"),
    ("test10", "test11"),
    ("test", "test1"),
    ("junkname0withnumbers1", "junkname0withnumbers2")
])
def test_increment_job_name(basic_chip, prev_name, new_name):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('option', 'jobincr', True)

    basic_chip.set('option', 'jobname', prev_name)
    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)

    assert basic_chip.get("option", "jobname") == prev_name
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_chip.get("option", "jobname") == new_name


def test_clean_build_dir(basic_chip):
    basic_chip.set('option', 'clean', True)

    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_called_once()


def test_clean_build_dir_with_from(basic_chip):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('option', 'from', 'stepone')

    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)
    assert os.path.isdir(basic_chip.getworkdir())

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_clean_build_dir_do_nothing(basic_chip):
    basic_chip.set('option', 'clean', False)

    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_clean_build_dir_remote(basic_chip):
    basic_chip.set('option', 'clean', True)
    basic_chip.set('record', 'remoteid', 'blah')

    scheduler = Scheduler(basic_chip)

    os.makedirs(basic_chip.getworkdir(), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as call:
        scheduler._Scheduler__clean_build_dir()
        call.assert_not_called()


def test_check_manifest_pass(basic_chip):
    scheduler = Scheduler(basic_chip)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = True
        scheduler.run()
        call.assert_called_once()


def test_check_manifest_fail(basic_chip):
    scheduler = Scheduler(basic_chip)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = False
        with pytest.raises(RuntimeError, match='check_manifest\\(\\) failed'):
            scheduler.run()
        call.assert_called_once()
