import json
import pytest
import re

import os.path

from unittest.mock import patch, MagicMock

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.tools.builtin.nop import NOPTask

from siliconcompiler.scheduler import SlurmSchedulerNode
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.utils.multiprocessing import MPManager


@pytest.fixture
def project():
    flow = Flowgraph("testflow")

    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


def test_init(project):
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            hex = "thisisahash"
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(project, "stepone", "0")
        job_name_call.assert_called_once()
    assert node.jobhash == "thisisahash"


def test_init_with_id(project):
    project.set("record", "remoteid", "thisistheremoteid")
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            pass
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(project, "stepone", "0")
        job_name_call.assert_not_called()
    assert node.jobhash == "thisistheremoteid"


def test_is_local(project):
    node = SlurmSchedulerNode(project, "stepone", "0")
    assert node.is_local is False


def test_get_configuration_directory(project):
    assert os.path.basename(SlurmSchedulerNode.get_configuration_directory(project)) == \
        "sc_configs"
    assert os.path.dirname(SlurmSchedulerNode.get_configuration_directory(project)) == \
        jobdir(project)


def test_get_job_name():
    assert SlurmSchedulerNode.get_job_name("hash", "step", "index") == "hash_step_index"


def test_get_runtime_file_name():
    assert SlurmSchedulerNode.get_runtime_file_name("hash", "step", "index", "sh") == \
        "hash_step_index.sh"


def test_slurm_show_no_nodelog(disable_mp_process, project):
    # Inserting value into configuration
    project.option.scheduler.set_name("slurm")
    project.option.scheduler.set_queue("test_queue")

    class DummyPOpen:
        def wait(self):
            return

        returncode = 10

    # Run the project's build process synchronously.
    with patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.assert_slurm") as assert_slurm, \
            patch("subprocess.Popen") as popen, \
            patch("siliconcompiler.schema_support.record.RecordSchema.record_python_packages"):
        popen.return_value = DummyPOpen()

        with pytest.raises(RuntimeError,
                           match=r"Run failed: Could not run final steps \(steptwo\) "
                                 r"due to errors in: stepone/0"):
            project.run()
        assert_slurm.assert_called_once()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')

    # Collect from build/testdesign/job0/job.log
    with open("build/testdesign/job0/job.log") as f:
        caplog = f.read()

    assert "Slurm exited with a non-zero code (10)." in caplog
    assert re.search(r"Node log file: .*\/build\/testdesign\/job0\/sc_configs\/"
                     r"[0-9a-f]+_stepone_0\.log", caplog) is None


def test_slurm_show_nodelog(disable_mp_process, project):
    # Inserting value into configuration
    project.option.scheduler.set_name("slurm")
    project.option.scheduler.set_queue("test_queue")

    class DummyPOpen:
        def wait(self):
            return

        returncode = 10

    def dummy_get_runtime_file_name(hash, step, index, ext):
        return f"thisfile.{ext}"

    # Run the project's build process synchronously.
    with patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.assert_slurm") as assert_slurm, \
            patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.get_runtime_file_name") \
            as get_runtime_file_name, \
            patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode."
                  "get_configuration_directory") as get_configuration_directory, \
            patch("subprocess.Popen") as popen, \
            patch("siliconcompiler.schema_support.record.RecordSchema.record_python_packages"):
        popen.return_value = DummyPOpen()
        get_configuration_directory.return_value = "."
        get_runtime_file_name.side_effect = dummy_get_runtime_file_name

        with open("thisfile.log", "w") as f:
            f.write("find this text in the log")

        with pytest.raises(RuntimeError,
                           match=r"Run failed: Could not run final steps \(steptwo\) "
                                 r"due to errors in: stepone/0"):
            project.run()
        assert_slurm.assert_called_once()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')

    # Collect from build/testdesign/job0/job.log
    with open("build/testdesign/job0/job.log") as f:
        caplog = f.read()

    assert "find this text in the log" in caplog
    assert "Slurm exited with a non-zero code (10)." in caplog
    assert "Node log file: " in caplog
    assert "thisfile.log" in caplog


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.slurm
@pytest.mark.timeout(300)
def test_slurm_local_py(project):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    project.set('option', 'scheduler', 'name', 'slurm')

    # Run the project's build process synchronously.
    assert project.run()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')
    assert os.path.isfile('build/testdesign/job0/stepone/0/outputs/testdesign.pkg.json')
    assert os.path.isfile('build/testdesign/job0/steptwo/0/outputs/testdesign.pkg.json')

    assert project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS


def test_mark_copy(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = SlurmSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set:
        assert node.mark_copy() is True
        sc_set.assert_called()
        assert sc_set.call_count == 2


def test_mark_copy_with_shared_require_copy(project):
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/nfs"])

    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = SlurmSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set, \
            patch("siliconcompiler.Project.find_files") as find_files:
        find_files.return_value = ["/nfs/testdir", "/notshared"]
        assert node.mark_copy() is True
        sc_set.assert_called()
        assert sc_set.call_count == 2


def test_mark_copy_with_shared_require_no_copy(project):
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/nfs", "/shared"])

    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = SlurmSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set, \
            patch("siliconcompiler.Project.find_files") as find_files:
        find_files.return_value = ["/nfs/testdir", "/shared"]
        assert node.mark_copy() is False
        sc_set.assert_not_called()


def test_mark_copy_with_shared_require_selective_copy(project):
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/nfs", "/shared"])

    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    def dummy_find(*key, **kwargs):
        if key[-1] == "refdir":
            return ["/nfs/testdir", "/shared"]
        else:
            return ["/nfs/testdir", "/notshared"]

    node = SlurmSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set, \
            patch("siliconcompiler.Project.find_files") as find_files:
        find_files.side_effect = dummy_find
        assert node.mark_copy() is True
        sc_set.assert_called_once_with('tool', 'builtin', 'task', 'nop', 'prescript', True,
                                       field='copy', clobber=True, step=None, index=None)


def test_mark_copy_with_shared_covers_all(project):
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/"])

    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = SlurmSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set, \
            patch("siliconcompiler.Project.find_files") as find_files:
        assert node.mark_copy() is False
        sc_set.assert_not_called()
        find_files.assert_not_called()


def test_init_calls_assert():
    with patch("siliconcompiler.scheduler.SlurmSchedulerNode.assert_slurm") as assert_slurm:
        SlurmSchedulerNode.init(None)
        assert_slurm.assert_called_once()


def test_load_user_config_load_config(monkeypatch):
    monkeypatch.setattr(MPManager.get_settings(), "_SettingsManager__filepath",
                        os.path.abspath("options.json"))
    with open("options.json", "w") as fd:
        json.dump({
            "scheduler-slurm": {
                "sharedpaths": ["/nfs", "/shared"],
                "dummy_data": None
            }
        }, fd)

    assert MPManager.get_settings().get_category("scheduler-slurm") == {}
    MPManager.get_settings()._load()
    assert MPManager.get_settings().get_category("scheduler-slurm") == {
        "sharedpaths": ["/nfs", "/shared"],
        "dummy_data": None
    }


def test_set_user_config(monkeypatch):
    monkeypatch.setattr(MPManager.get_settings(), "_SettingsManager__filepath",
                        os.path.abspath("options.json"))

    assert MPManager.get_settings().get_category("scheduler-slurm") == {}
    SlurmSchedulerNode._set_user_config("sharedpaths", ["/nfs", "/shared"])
    assert MPManager.get_settings().get_category("scheduler-slurm") == {
        "sharedpaths": ["/nfs", "/shared"]
    }


def test_write_user_config(monkeypatch):
    monkeypatch.setattr(MPManager.get_settings(), "_SettingsManager__filepath",
                        os.path.abspath("options.json"))

    assert MPManager.get_settings().get_category("scheduler-slurm") == {}
    SlurmSchedulerNode._set_user_config("sharedprefix", [])
    SlurmSchedulerNode._write_user_config()

    assert os.path.isfile(os.path.abspath("options.json"))
    with open(os.path.abspath("options.json")) as fd:
        data = json.load(fd)

    assert data['scheduler-slurm'] == {'sharedprefix': []}


def test_check_required_paths(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    assert SlurmSchedulerNode(project, "steptwo", "0").check_required_paths() is True


def test_cancel(project):
    '''A slurm node cancels its own job, so nothing above it has to know that
       the work is not where the node process is'''
    project.set('record', 'remoteid', 'thisisahash')
    node = SlurmSchedulerNode(project, "steptwo", "0")

    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run", return_value=_scancel_ok()) as run:
        node.cancel()

    assert [call.args[0] for call in run.call_args_list] == [
        ["scancel", "--name", "thisisahash_steptwo_0"]
    ]


def test_cancel_without_scancel(project, project_logger, caplog):
    '''A job that was asked to stop and could not be is worth saying out loud'''
    project.set('record', 'remoteid', 'thisisahash')
    project_logger(project)
    node = SlurmSchedulerNode(project, "steptwo", "0")

    with patch("shutil.which", return_value=None):
        node.cancel()

    assert "Unable to cancel slurm job for steptwo/0" in caplog.text


def test_cancel_reports_a_refused_scancel(project, project_logger, caplog):
    '''A scancel that returned nonzero left the job running, and the caller is
       about to kill the only thing waiting on it'''
    project.set('record', 'remoteid', 'thisisahash')
    project_logger(project)
    node = SlurmSchedulerNode(project, "steptwo", "0")

    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run", return_value=_scancel_result(1)):
        node.cancel()

    assert "Unable to cancel slurm job for steptwo/0" in caplog.text


def _scancel_result(returncode):
    """What subprocess.run() hands back, with only what cancel_nodes reads."""
    result = MagicMock()
    result.returncode = returncode
    return result


def _scancel_ok():
    return _scancel_result(0)


def test_cancel_nodes():
    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run", return_value=_scancel_ok()) as run:
        assert SlurmSchedulerNode.cancel_nodes(
            "thisisahash", [("stepone", "0"), ("steptwo", "1")]) == \
            [("stepone", "0"), ("steptwo", "1")]

    assert [call.args[0] for call in run.call_args_list] == [
        ["scancel", "--name", "thisisahash_stepone_0"],
        ["scancel", "--name", "thisisahash_steptwo_1"]
    ]


def test_cancel_nodes_no_nodes():
    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run") as run:
        assert SlurmSchedulerNode.cancel_nodes("thisisahash", []) == []

    run.assert_not_called()


def test_cancel_nodes_without_scancel():
    with patch("shutil.which", return_value=None), \
            patch("subprocess.run") as run:
        assert SlurmSchedulerNode.cancel_nodes("thisisahash", [("stepone", "0")]) == []

    run.assert_not_called()


def test_cancel_nodes_refused():
    '''A scancel that returned nonzero did not cancel anything, and saying it
       did would have the caller kill the job's only waiter'''
    def refuse(cmd, **kwargs):
        return _scancel_result(1 if 'steptwo_1' in cmd[-1] else 0)

    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run", side_effect=refuse):
        assert SlurmSchedulerNode.cancel_nodes(
            "thisisahash",
            [("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")]) == \
            [("stepone", "0"), ("stepthree", "2")]


def test_cancel_nodes_timeout():
    '''A scancel that does not return leaves its node unclaimed'''
    import subprocess

    def hang(cmd, **kwargs):
        if 'steptwo_1' in cmd[-1]:
            raise subprocess.TimeoutExpired(cmd, kwargs['timeout'])
        return _scancel_ok()

    with patch("shutil.which", return_value="/usr/bin/scancel"), \
            patch("subprocess.run", side_effect=hang) as run:
        # The node after the one that hung is still attempted.
        assert SlurmSchedulerNode.cancel_nodes(
            "thisisahash",
            [("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")]) == \
            [("stepone", "0"), ("stepthree", "2")]

    assert len(run.call_args_list) == 3
    assert all(call.kwargs["timeout"] == SlurmSchedulerNode._CANCEL_TIMEOUT
               for call in run.call_args_list)


def _sinfo_result(returncode, stdout=b""):
    """What subprocess.run() hands back, with only what the partition lookup reads."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    return result


def _sinfo_calls(text, json_out):
    """Answers 'sinfo --format %P' with text and 'sinfo --json' with json_out."""
    def run(cmd, *args, **kwargs):
        return text if "--json" not in cmd else json_out
    return run


def test_get_slurm_partition_prefers_the_default():
    '''The partition marked '*' is the cluster's default, and picking anything
       else means submitting somewhere the admin did not nominate'''
    with patch("subprocess.run",
               return_value=_sinfo_result(0, b"debug\nbatch*\nlong\n")) as run:
        assert SlurmSchedulerNode.get_slurm_partition() == "batch"

    assert run.call_args_list[0].args[0] == ["sinfo", "--noheader", "--format", "%P"]


def test_get_slurm_partition_without_a_default():
    '''A cluster with no default partition still has to yield an answer'''
    with patch("subprocess.run", return_value=_sinfo_result(0, b"debug\nlong\n")):
        assert SlurmSchedulerNode.get_slurm_partition() == "debug"


def test_get_slurm_partition_falls_back_to_new_json():
    '''23.02 onwards: a top-level "sinfo" list of records carrying one partition
       object each'''
    payload = json.dumps({
        "sinfo": [
            {"partition": {"name": "batch"}},
            {"partition": {"name": "long"}},
            {"partition": {"name": "batch"}}
        ]
    }).encode()

    with patch("subprocess.run",
               side_effect=_sinfo_calls(_sinfo_result(1),
                                        _sinfo_result(0, payload))) as run:
        assert SlurmSchedulerNode.get_slurm_partition() == "batch"

    assert run.call_args_list[-1].args[0] == ["sinfo", "--json"]


def test_get_slurm_partition_falls_back_to_old_json():
    '''22.05: a top-level "nodes" list whose records carry a list of names.
       This is the schema the pinned slurm emitted, and it still has to work'''
    payload = json.dumps({
        "nodes": [
            {"partitions": ["ctldpart", "other"]}
        ]
    }).encode()

    with patch("subprocess.run",
               side_effect=_sinfo_calls(_sinfo_result(1),
                                        _sinfo_result(0, payload))):
        assert SlurmSchedulerNode.get_slurm_partition() == "ctldpart"


def test_get_slurm_partition_reports_an_unreadable_cluster():
    '''Failing both ways is worth an error rather than a partition of ''.'''
    with patch("subprocess.run", return_value=_sinfo_result(1)):
        with pytest.raises(RuntimeError, match="Unable to determine partitions in slurm"):
            SlurmSchedulerNode.get_slurm_partition()


def test_get_slurm_partition_survives_unparsable_json():
    '''A --json that is not json at all must not raise JSONDecodeError'''
    with patch("subprocess.run",
               side_effect=_sinfo_calls(_sinfo_result(1),
                                        _sinfo_result(0, b"not json"))):
        with pytest.raises(RuntimeError, match="Unable to determine partitions in slurm"):
            SlurmSchedulerNode.get_slurm_partition()
