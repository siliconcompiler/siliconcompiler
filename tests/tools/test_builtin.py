import logging
import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Flowgraph, Design, Project
from siliconcompiler.schema import EditableSchema, Parameter, PerNode
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.builtin.join import JoinTask
from siliconcompiler.tools.builtin.minimum import MinimumTask
from siliconcompiler.tools.builtin.maximum import MaximumTask
from siliconcompiler.tools.builtin.mux import MuxTask
from siliconcompiler.tools.builtin.verify import VerifyTask
from siliconcompiler.tools.builtin.importfiles import ImportFilesTask
from siliconcompiler.tools.builtin.filter import FilterTask
from siliconcompiler.tools.builtin.wait import Wait


@pytest.fixture
def minmax_project(monkeypatch):
    def minmax(cls, parallel: int = 10):
        design = Design("testdesign")
        with design.active_fileset("rtl"):
            design.set_topmodule("top")

        proj = Project(design)
        EditableSchema(proj).insert("metric", "metric0", Parameter("int", pernode=PerNode.REQUIRED))
        EditableSchema(proj).insert("metric", "metric1", Parameter("int", pernode=PerNode.REQUIRED))

        flow = Flowgraph("test")

        flow.node("end", cls())
        for n in range(parallel):
            flow.node("start", NOPTask(), index=n)
            flow.edge("start", "end", tail_index=n)

            # errors / warnings is always present so safe to use here
            flow.set("start", str(n), "weight", "metric0", 1.0)
            flow.set("start", str(n), "goal", "metric1", 0.0)

            proj.set("metric", "metric0", 1000 - n * 1 + 42.0, step="start", index=n)
            proj.set("metric", "metric1", 0, step="start", index=n)

        monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
        proj.logger.setLevel(logging.INFO)
        proj.add_fileset("rtl")
        proj.set_flow(flow)

        return proj

    return minmax


@pytest.mark.parametrize("tool", [
    NOPTask, JoinTask, MinimumTask, MaximumTask,
    MuxTask, VerifyTask, ImportFilesTask, FilterTask, Wait
])
def test_tool_name(tool):
    assert tool().tool() == "builtin"


def test_nop_name():
    assert NOPTask().task() == "nop"


def test_join_name():
    assert JoinTask().task() == "join"


def test_minimum_name():
    assert MinimumTask().task() == "minimum"


def test_maximum_name():
    assert MaximumTask().task() == "maximum"


def test_mux_name():
    assert MuxTask().task() == "mux"


def test_verify_name():
    assert VerifyTask().task() == "verify"


def test_importfiles_name():
    assert ImportFilesTask().task() == "importfiles"


def test_filter_name():
    assert FilterTask().task() == "filter"


def test_wait_name():
    assert Wait().task() == "wait"


def test_nop_select_inputs(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", NOPTask())
    flow.edge("start", "end")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'nop'" in caplog.text


def test_join_select_inputs(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", JoinTask())
    flow.edge("start", "end")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'join'" in caplog.text


def test_wait_select_inputs(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", Wait())
    flow.edge("start", "end")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'wait'" in caplog.text


def test_wait_no_io_files():
    """Test that Wait task doesn't set up input/output files (unlike other builtin tasks)"""
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    task_name = Wait().task()

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", Wait())
    flow.edge("start", "end")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == []
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == []

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    # Wait task should NOT copy inputs to outputs
    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == []
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == []


def test_minimum(minmax_project, caplog):
    node = SchedulerNode(minmax_project(MinimumTask), "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '9')]

    assert "Running builtin task 'minimum'" in caplog.text
    assert "Selected 'start/9' with score 0.000" in caplog.text


def test_maximum(minmax_project, caplog):
    node = SchedulerNode(minmax_project(MaximumTask), "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'maximum'" in caplog.text
    assert "Selected 'start/0' with score 1.000" in caplog.text


@pytest.mark.parametrize("cls", [MinimumTask, MaximumTask])
def test_minmax_all_fail(minmax_project, cls):
    project = minmax_project(cls)
    for index in project.getkeys("flowgraph", "test", "start"):
        project.set("record", "status", "error", step="start", index=index)

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == []


def test_minimum_winner_failed(minmax_project, caplog):
    project = minmax_project(MinimumTask)
    project.set("record", "status", "error", step="start", index="9")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '8')]

    assert "Running builtin task 'minimum'" in caplog.text
    assert "Selected 'start/8' with score 0.000" in caplog.text


def test_minimum_winner_goal_negative(minmax_project, caplog):
    project = minmax_project(MinimumTask)
    project.set("metric", "metric1", -1, step="start", index="9")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '8')]

    assert "Running builtin task 'minimum'" in caplog.text
    assert "Step start/9 failed because it didn't meet goals for 'metric1' metric." in caplog.text
    assert "Selected 'start/8' with score 0.000" in caplog.text


def test_minimum_winner_goal_positive(minmax_project, caplog):
    project = minmax_project(MinimumTask)
    project.set("metric", "metric1", 1, step="start", index="9")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '8')]

    assert "Running builtin task 'minimum'" in caplog.text
    assert "Step start/9 failed because it didn't meet goals for 'metric1' metric." in caplog.text
    assert "Selected 'start/8' with score 0.000" in caplog.text


def test_maximum_winner_failed(minmax_project, caplog):
    project = minmax_project(MaximumTask)
    project.set("record", "status", "error", step="start", index="0")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '1')]

    assert "Running builtin task 'maximum'" in caplog.text
    assert "Selected 'start/1' with score 1.000" in caplog.text


def test_maximum_winner_goal_negative(minmax_project, caplog):
    project = minmax_project(MaximumTask)
    project.set("metric", "metric1", -1, step="start", index="0")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '1')]

    assert "Running builtin task 'maximum'" in caplog.text
    assert "Step start/0 failed because it didn't meet goals for 'metric1' metric." in caplog.text
    assert "Selected 'start/1' with score 1.000" in caplog.text


def test_maximum_winner_goal_positive(minmax_project, caplog):
    project = minmax_project(MaximumTask)
    project.set("metric", "metric1", 1, step="start", index="0")
    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '1')]

    assert "Running builtin task 'maximum'" in caplog.text
    assert "Step start/0 failed because it didn't meet goals for 'metric1' metric." in caplog.text
    assert "Selected 'start/1' with score 1.000" in caplog.text


def test_mux_minimum(minmax_project, caplog):
    project = minmax_project(MuxTask)
    project.set('flowgraph', "test", 'end', '0', 'args', 'minimum(metric0)')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '9')]

    assert "Running builtin task 'mux'" in caplog.text


def test_mux_maximum(minmax_project, caplog):
    project = minmax_project(MuxTask)
    project.set('flowgraph', "test", 'end', '0', 'args', 'maximum(metric0)')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'mux'" in caplog.text


def test_mux_two_metrics(minmax_project, caplog):
    project = minmax_project(MuxTask)
    for index in project.getkeys("flowgraph", "test", "start"):
        project.set("metric", "metric0", 100 - int(index), step="start", index=index)
        project.set("metric", "metric1", int(index) % 3, step="start", index=index)
    project.set('flowgraph', "test", 'end', '0', 'args', 'maximum(metric1)')
    project.add('flowgraph', "test", 'end', '0', 'args', 'minimum(metric0)')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '8')]

    assert "Running builtin task 'mux'" in caplog.text


def test_verify_pass(minmax_project, caplog):
    project = minmax_project(VerifyTask, parallel=1)
    project.set('flowgraph', "test", 'end', '0', 'args', 'metric0==1042')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'verify'" in caplog.text


def test_verify_fail(minmax_project, caplog):
    project = minmax_project(VerifyTask, parallel=1)
    project.set('flowgraph', "test", 'end', '0', 'args', 'metric0==1041')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        with pytest.raises(ValueError, match=r"^end/0 fails 'metric0' metric: 1042==1041$"):
            node.task.select_input_nodes()

    assert "Running builtin task 'verify'" in caplog.text


def test_verify_pass_two(minmax_project, caplog):
    project = minmax_project(VerifyTask, parallel=1)
    project.set('flowgraph', "test", 'end', '0', 'args', 'metric0==1042')
    project.add('flowgraph', "test", 'end', '0', 'args', 'metric1==0')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        assert node.task.select_input_nodes() == [('start', '0')]

    assert "Running builtin task 'verify'" in caplog.text


def test_verify_fail_two(minmax_project, caplog):
    project = minmax_project(VerifyTask, parallel=1)
    project.set('flowgraph', "test", 'end', '0', 'args', 'metric0==1042')
    project.add('flowgraph', "test", 'end', '0', 'args', 'metric1==1')

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        with pytest.raises(ValueError, match=r"^end/0 fails 'metric1' metric: 0==1$"):
            node.task.select_input_nodes()

    assert "Running builtin task 'verify'" in caplog.text


def test_verify_input_fail(minmax_project):
    project = minmax_project(VerifyTask, parallel=2)

    node = SchedulerNode(project, "end", "0")
    with node.runtime():
        with pytest.raises(ValueError, match=r"^end/0 receives 2 inputs, but only supports one$"):
            node.task.setup()


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask,
                                 VerifyTask, Wait])
def test_run(cls):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", cls())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    node = SchedulerNode(proj, "start", "0")
    with node.runtime():
        assert node.task.run() == 0


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask,
                                 VerifyTask, Wait])
def test_post_process(cls):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", cls())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    node = SchedulerNode(proj, "start", "0")
    with node.runtime():
        with patch("shutil.copytree") as copy:
            node.task.post_process()
            copy.assert_called_once()


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask])
def test_setup_copies_inputs(cls):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    task_name = cls().task()

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", cls())
    flow.edge("start", "end")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == []
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == []

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == [
        "test.out"
    ]
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == [
        "test.out"
    ]


def test_setup_copies_inputs_verify():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    task_name = VerifyTask().task()

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", VerifyTask())
    flow.edge("start", "end")

    proj = Project(design)
    EditableSchema(proj).insert("metric", "metric0", Parameter("float"))
    EditableSchema(proj).insert("metric", "metric1", Parameter("float"))
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")
    proj.set('flowgraph', "test", 'end', '0', 'args', 'metric0==1042')

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == []
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == []

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == [
        "test.out"
    ]
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == [
        "test.out"
    ]


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask])
def test_setup_copies_inputs_multiple(cls):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    task_name = cls().task()

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("otherstart", NOPTask())
    flow.node("end", cls())
    flow.edge("start", "end")
    flow.edge("otherstart", "end")

    proj = Project(design)
    EditableSchema(proj).insert("metric", "metric0", Parameter("float"))
    EditableSchema(proj).insert("metric", "metric1", Parameter("float"))
    proj.add_fileset("rtl")
    proj.set_flow(flow)
    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("other.out", step="otherstart", index="0")

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == []
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == []

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    assert proj.get("tool", "builtin", "task", task_name, "input", step="end", index="0") == [
        "other.out", "test.out"
    ]
    assert proj.get("tool", "builtin", "task", task_name, "output", step="end", index="0") == [
        "other.out", "test.out"
    ]


def test_importfiles_fail_inputs():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", ImportFilesTask())
    flow.edge("start", "end")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        with pytest.raises(ValueError,
                           match=r"^task must be an entry node$"):
            node.setup()


def test_importfiles_fail_no_inputs():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("task", ImportFilesTask())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    node = SchedulerNode(proj, "task", "0")
    with node.runtime():
        with pytest.raises(ValueError,
                           match=r"^task requires files or directories to import$"):
            node.setup()


def test_importfiles_just_file(monkeypatch):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("task", ImportFilesTask())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    with open("thisfile.txt", "w") as f:
        f.write("this")

    os.makedirs('run', exist_ok=True)

    ImportFilesTask.find_task(proj).add_import_file("thisfile.txt")

    node = SchedulerNode(proj, "task", "0")
    with node.runtime():
        node.setup()
        node.task.setup_work_directory("run")

        assert node.task.get("require") == [
            "tool,builtin,task,importfiles,var,file"]

        monkeypatch.chdir("run")
        node.task.run()
    assert os.path.isfile("outputs/thisfile.txt")


def test_importfiles(monkeypatch):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("task", ImportFilesTask())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    with open("thisfile.txt", "w") as f:
        f.write("this")

    os.makedirs("thisdir", exist_ok=True)
    with open("thisdir/thatfile.txt", "w") as f:
        f.write("this")

    os.makedirs('run', exist_ok=True)

    ImportFilesTask.find_task(proj).add_import_file("thisfile.txt")
    ImportFilesTask.find_task(proj).add_import_dir("thisdir")

    node = SchedulerNode(proj, "task", "0")
    with node.runtime():
        node.setup()
        node.task.setup_work_directory("run")

        assert node.task.get("require") == [
            "tool,builtin,task,importfiles,var,file",
            "tool,builtin,task,importfiles,var,dir"]

        monkeypatch.chdir("run")
        node.task.run()
    assert os.path.isfile("outputs/thisfile.txt")
    assert os.path.isfile("outputs/thisdir/thatfile.txt")


def test_filter_fail_inputs():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("task", FilterTask())

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    node = SchedulerNode(proj, "task", "0")
    with node.runtime():
        with pytest.raises(ValueError,
                           match=r"^task receives no files$"):
            node.setup()


def test_filter_remove_all(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", FilterTask())
    flow.edge("start", "end")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")
    FilterTask.find_task(proj).add_filter_keep("nomatch")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    assert "Filters (nomatch) removed all incoming files" in caplog.text


def test_filter_remove_all_from_args(monkeypatch, caplog):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", FilterTask())
    flow.edge("start", "end")
    flow.set("end", "0", "args", "nomatch")

    proj = Project(design)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    NOPTask.find_task(proj).add_output_file("test.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()

    assert "Filters (nomatch) removed all incoming files" in caplog.text


def test_filter_remove_one():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", FilterTask())
    flow.edge("start", "end")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    NOPTask.find_task(proj).add_output_file("test0.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test1.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test2.out", step="start", index="0")
    FilterTask.find_task(proj).add_filter_keep("test0*")
    FilterTask.find_task(proj).add_filter_keep("test2*")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()
        assert node.task.get("output") == ['test0.out', 'test2.out']


def test_filter_remove_one_from_args():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", FilterTask())
    flow.edge("start", "end")
    flow.set("end", "0", "args", "test0*")
    flow.add("end", "0", "args", "test2*")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    NOPTask.find_task(proj).add_output_file("test0.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test1.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test2.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()
        assert node.task.get("output") == ['test0.out', 'test2.out']


def test_filter_keep_default():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    flow = Flowgraph("test")
    flow.node("start", NOPTask())
    flow.node("end", FilterTask())
    flow.edge("start", "end")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    NOPTask.find_task(proj).add_output_file("test0.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test1.out", step="start", index="0")
    NOPTask.find_task(proj).add_output_file("test2.out", step="start", index="0")

    node = SchedulerNode(proj, "end", "0")
    with node.runtime():
        node.setup()
        assert node.task.get("output") == ['test0.out', 'test1.out', 'test2.out']


###############################################################################
# Tests for Wait.serialize_tool_tasks
###############################################################################
def test_wait_serialize_tool_tasks_simple():
    """Test serialization of two directly connected nodes with the same tool."""
    flow = Flowgraph("testflow")
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.edge("place1", "place2")

    # Manually set the tool to match
    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Should NOT have wait tasks for directly connected nodes
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('place2', '0'),))

    # Verify graph is still valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_multiple():
    """Test serialization of three directly connected nodes with the same tool."""
    flow = Flowgraph("testflow")
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("place3", NOPTask(), index=0)

    flow.edge("place1", "place2")
    flow.edge("place2", "place3")

    # Set all to same tool
    for step in ["place1", "place2", "place3"]:
        flow.set(step, "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Should NOT have wait tasks for directly connected nodes
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('place2', '0'),),
        (('place3', '0'),))

    # Verify graph is still valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_no_matching_tool():
    """Test serialization when no nodes use the specified tool."""
    flow = Flowgraph("testflow")
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.edge("place1", "place2")

    flow.set("place1", "0", "tool", "yosys")
    flow.set("place2", "0", "tool", "yosys")

    initial_nodes = len(flow.get_nodes())
    Wait.serialize_tool_tasks(flow, "openroad")

    # Should have no new nodes added
    assert len(flow.get_nodes()) == initial_nodes

    # Verify execution order unchanged
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('place2', '0'),))


def test_wait_serialize_tool_tasks_invalid_tool_name():
    """Test error handling for invalid tool names."""
    flow = Flowgraph("testflow")
    flow.node("place1", NOPTask())

    with pytest.raises(ValueError, match="tool_name must be a non-empty string"):
        Wait.serialize_tool_tasks(flow, "")

    with pytest.raises(ValueError, match="tool_name must be a non-empty string"):
        Wait.serialize_tool_tasks(flow, None)


def test_wait_serialize_tool_tasks_parallel_branches():
    """Test serialization with parallel branches converging."""
    flow = Flowgraph("testflow")

    # Create parallel paths that both use the same tool
    flow.node("start", NOPTask())
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("join", JoinTask())

    flow.edge("start", "place1")
    flow.edge("start", "place2")
    flow.edge("place1", "join")
    flow.edge("place2", "join")

    # Set place nodes to same tool
    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Verify wait node was added (place1 and place2 are parallel)
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 1
    assert ("place2.wait", "0") in nodes

    # Verify execution order enforces serialization
    assert flow.get_execution_order() == (
        (('start', '0'),),
        (('place1', '0'),),
        (('place2.wait', '0'),),
        (('place2', '0'),),
        (('join', '0'),))

    # Verify edges: place1 -> wait -> place2
    wait_inputs = flow.get("place2.wait", "0", "input")
    assert ("place1", "0") in wait_inputs

    place2_inputs = flow.get("place2", "0", "input")
    assert ("place2.wait", "0") in place2_inputs
    assert ("start", "0") in place2_inputs  # Original edge preserved

    # Graph should still be valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_complex_diamond():
    """Test serialization with a complex diamond graph."""
    flow = Flowgraph("testflow")

    # Create diamond pattern
    flow.node("start", NOPTask())
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("place3", NOPTask(), index=0)
    flow.node("place4", NOPTask(), index=0)
    flow.node("end", JoinTask())

    # Edges
    flow.edge("start", "place1")
    flow.edge("start", "place2")
    flow.edge("place1", "place3")
    flow.edge("place2", "place4")
    flow.edge("place3", "end")
    flow.edge("place4", "end")

    # Set all place nodes to same tool
    for i in range(1, 5):
        flow.set(f"place{i}", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Verify wait nodes added for parallel branches
    # place1 and place2 are parallel (no path between them)
    # place3 and place4 are parallel (no path between them)
    # But place1->place3 have path, place2->place4 have path
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) >= 1  # At least one wait node for parallel branches

    # Verify all wait nodes follow naming convention
    for wait_node in wait_nodes:
        assert wait_node[0].endswith(".wait")
        assert wait_node[1] == "0"

    # Verify execution order
    exec_order = flow.get_execution_order()
    level_map = {}
    for level_idx, level in enumerate(exec_order):
        for node in level:
            level_map[node] = level_idx
    # All place nodes should be at different levels (serialized)
    assert level_map[('place1', '0')] < level_map[('place2', '0')] < level_map[('place3', '0')] \
        < level_map[('place4', '0')]

    # Graph should be valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_single_node():
    """Test serialization with only one node using the tool."""
    flow = Flowgraph("testflow")
    flow.node("place1", NOPTask())
    flow.node("join", JoinTask())
    flow.edge("place1", "join")

    flow.set("place1", "0", "tool", "openroad")

    initial_nodes = len(flow.get_nodes())
    Wait.serialize_tool_tasks(flow, "openroad")

    # No new nodes should be added (only one place node)
    assert len(flow.get_nodes()) == initial_nodes

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('join', '0'),))


def test_wait_serialize_tool_tasks_mixed_tools():
    """Test serialization with mixed tools in the flow."""
    flow = Flowgraph("testflow")

    # Create a mix of different tools
    flow.node("syn1", NOPTask(), index=0)
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("route1", NOPTask(), index=0)

    flow.edge("syn1", "place1")
    flow.edge("place1", "place2")
    flow.edge("place2", "route1")

    flow.set("syn1", "0", "tool", "yosys")
    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")
    flow.set("route1", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # All openroad nodes have dependency paths (place1->place2->route1)
    # so no wait tasks should be added
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify original edges are preserved
    assert ("syn1", "0") in flow.get("place1", "0", "input")
    assert ("place1", "0") in flow.get("place2", "0", "input")
    assert ("place2", "0") in flow.get("route1", "0", "input")

    # Verify execution order
    assert flow.get_execution_order() == (
        (('syn1', '0'),),
        (('place1', '0'),),
        (('place2', '0'),),
        (('route1', '0'),))

    # Should only serialize openroad nodes
    assert flow.validate()


def test_wait_serialize_tool_tasks_multiple_indices():
    """Test serialization with multiple indices of same step."""
    flow = Flowgraph("testflow")

    # Create multiple indices
    flow.node("place", NOPTask(), index=0)
    flow.node("place", NOPTask(), index=1)
    flow.node("place", NOPTask(), index=2)

    flow.edge("place", "place", tail_index=0, head_index=1)
    flow.edge("place", "place", tail_index=1, head_index=2)

    # Set all to same tool
    for i in range(3):
        flow.set("place", str(i), "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Directly connected indices don't need wait nodes
    # Verify execution order
    assert flow.get_execution_order() == (
        (('place', '0'),),
        (('place', '1'),),
        (('place', '2'),))

    # Graph should be valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_preserves_non_tool_edges():
    """Test that serialization preserves edges to/from non-tool nodes."""
    flow = Flowgraph("testflow")

    flow.node("start", NOPTask())
    flow.node("place1", NOPTask())
    flow.node("place2", NOPTask())
    flow.node("end", JoinTask())

    # Create edges
    flow.edge("start", "place1")
    flow.edge("start", "place2")  # This edge should be preserved
    flow.edge("place1", "end")
    flow.edge("place2", "end")

    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # place1 and place2 are parallel branches, wait should be added
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 1

    # Verify original edges to non-tool nodes are preserved
    assert ("start", "0") in flow.get("place1", "0", "input")
    assert ("start", "0") in flow.get("place2", "0", "input")
    assert ("place1", "0") in flow.get("end", "0", "input")
    assert ("place2", "0") in flow.get("end", "0", "input")

    # Verify execution order (wait node inserted between place1 and place2)
    assert flow.get_execution_order() == (
        (("start", "0"),),
        (("place1", "0"),),
        (("place2.wait", "0"),),
        (("place2", "0"),),
        (("end", "0"),))

    assert flow.validate()


def test_wait_serialize_tool_tasks_large_chain():
    """Test serialization with a large chain of nodes."""
    flow = Flowgraph("testflow")

    # Create a chain of 10 place nodes
    num_nodes = 10
    for i in range(num_nodes):
        flow.node("place", NOPTask(), index=i)
        flow.set("place", str(i), "tool", "openroad")

        if i > 0:
            flow.edge("place", "place", tail_index=i-1, head_index=i)

    initial_node_count = len(flow.get_nodes())

    Wait.serialize_tool_tasks(flow, "openroad")

    # Directly connected chain doesn't need wait tasks
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0
    assert len(nodes) == initial_node_count

    # Verify chain edges are preserved
    for i in range(1, num_nodes):
        inputs = flow.get("place", str(i), "input")
        assert ("place", str(i-1)) in inputs

    # Verify execution order maintains chain (all nodes at different levels)
    expected_order = tuple((("place", str(i)),) for i in range(num_nodes))
    assert flow.get_execution_order() == expected_order

    assert flow.validate()


def test_wait_serialize_tool_tasks_maintains_execution_order():
    """Test that serialization maintains proper execution order."""
    flow = Flowgraph("testflow")

    flow.node("start", NOPTask())
    flow.node("place1", NOPTask())
    flow.node("place2", NOPTask())
    flow.node("end", JoinTask())

    flow.edge("start", "place1")
    flow.edge("place1", "place2")
    flow.edge("place2", "end")

    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    exec_order_after = flow.get_execution_order()

    # No wait nodes should be added (place1 -> place2 have dependency path)
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify execution order maintains place1 < place2
    level_map = {}
    for level_idx, level in enumerate(exec_order_after):
        for node in level:
            level_map[node] = level_idx

    assert level_map[("place1", "0")] < level_map[("place2", "0")]

    # Execution order should still follow dependencies
    assert flow.validate()


def test_wait_serialize_tool_tasks_multiple_independent_chains():
    """Test serialization with multiple independent chains."""
    flow = Flowgraph("testflow")

    # Chain 1
    flow.node("syn1", NOPTask())
    flow.node("place1", NOPTask())
    flow.edge("syn1", "place1")

    # Chain 2 (independent)
    flow.node("syn2", NOPTask())
    flow.node("place2", NOPTask())
    flow.edge("syn2", "place2")

    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # place1 and place2 are independent (no path), so wait should be added
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 1

    # Verify original chain edges are preserved
    assert ("syn1", "0") in flow.get("place1", "0", "input")
    assert ("syn2", "0") in flow.get("place2", "0", "input")

    # Verify execution order (wait node inserted between place1 and place2)
    assert flow.get_execution_order() == (
        (("syn1", "0"), ("syn2", "0")),
        (("place1", "0"),),
        (("place2.wait", "0"),),
        (("place2", "0"),))

    # Both chains should remain independent
    assert flow.validate()


def test_wait_serialize_tool_tasks_idempotent():
    """Test that calling serialize twice doesn't break the graph."""
    flow = Flowgraph("testflow")

    flow.node("place1", NOPTask())
    flow.node("place2", NOPTask())
    flow.edge("place1", "place2")

    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")
    assert flow.validate()

    nodes_after_first = len(flow.get_nodes())
    wait_nodes_first = [n for n in flow.get_nodes() if "wait" in n[0]]

    # Call again - should not add more wait tasks
    Wait.serialize_tool_tasks(flow, "openroad")
    assert flow.validate()

    nodes_after_second = len(flow.get_nodes())
    wait_nodes_second = [n for n in flow.get_nodes() if "wait" in n[0]]

    # No wait tasks should exist (place1->place2 have dependency path)
    assert len(wait_nodes_first) == 0
    assert len(wait_nodes_second) == 0

    # Node count should remain the same
    assert nodes_after_first == nodes_after_second

    # Original edge should still be preserved
    assert ("place1", "0") in flow.get("place2", "0", "input")

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('place2', '0'),))

    # Graph should still be valid even after second call
    assert len(flow.get_nodes()) >= nodes_after_first


def test_wait_serialize_tool_tasks_non_connected():
    """Test serialization with nodes that have dependency path through other tools."""
    flow = Flowgraph("testflow")

    # Create a graph where two tool nodes are connected through another tool
    # place1 -> other -> place2 (has dependency path, no wait needed)
    flow.node("place1", NOPTask(), index=0)
    flow.node("other", JoinTask(), index=0)
    flow.node("place2", NOPTask(), index=0)

    flow.edge("place1", "other")
    flow.edge("other", "place2")

    # Set place nodes to same tool
    flow.set("place1", "0", "tool", "openroad")
    flow.set("place2", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Should NOT have wait task - nodes have dependency path through 'other'
    # They cannot execute in parallel
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('other', '0'),),
        (('place2', '0'),))

    # Graph should be valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_mixed_direct_indirect():
    """Test serialization with mix of directly and indirectly connected nodes."""
    flow = Flowgraph("testflow")

    # Three place nodes: place1->place2 (direct), place2->other->place3 (indirect)
    # All have dependency paths, so no wait tasks needed
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("other", JoinTask(), index=0)
    flow.node("place3", NOPTask(), index=0)

    flow.edge("place1", "place2")
    flow.edge("place2", "other")
    flow.edge("other", "place3")

    # Set place nodes to same tool
    for i in [1, 2, 3]:
        flow.set(f"place{i}", "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Should NOT have wait tasks - all nodes have dependency paths
    # place1->place2 (direct), place2->other->place3 (indirect)
    # They already execute serially, no need for wait tasks
    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]
    assert len(wait_nodes) == 0

    # Verify execution order
    assert flow.get_execution_order() == (
        (('place1', '0'),),
        (('place2', '0'),),
        (('other', '0'),),
        (('place3', '0'),))

    # Graph should be valid
    assert flow.validate()


def test_wait_serialize_tool_tasks_three_parallel_nodes():
    """Test serialization with three parallel nodes - exposes chaining issue."""
    flow = Flowgraph("testflow")

    # Create three parallel openroad nodes with no paths between them
    flow.node("start", NOPTask())
    flow.node("place1", NOPTask(), index=0)
    flow.node("place2", NOPTask(), index=0)
    flow.node("place3", NOPTask(), index=0)
    flow.node("join", JoinTask())

    # All three places start from the same node
    flow.edge("start", "place1")
    flow.edge("start", "place2")
    flow.edge("start", "place3")

    # All three converge to join
    flow.edge("place1", "join")
    flow.edge("place2", "join")
    flow.edge("place3", "join")

    # Set all to same tool
    for step in ["place1", "place2", "place3"]:
        flow.set(step, "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]

    # Should have wait nodes for serialization
    assert len(wait_nodes) >= 2, f"Expected at least 2 wait nodes, got {len(wait_nodes)}"

    # Verify execution order enforces serial execution: place1 < place2 < place3
    assert flow.get_execution_order() == (
        (("start", "0"),),
        (("place1", "0"),),
        (("place2.wait", "0"),),
        (("place2", "0"),),
        (("place3.wait", "0"),),
        (("place3", "0"),),
        (("join", "0"),))

    # CRITICAL: Verify wait tasks form a chain to ensure serial execution
    # place1 -> place2_0.wait -> place2 -> place3_0.wait -> place3
    # This means place2 should depend on place2_0.wait AND place3 should depend on place3_0.wait

    if len(wait_nodes) >= 1:
        # Check that place2 has the first wait as an input
        place2_inputs = flow.get("place2", "0", "input")
        has_wait_input = any("wait" in str(inp[0]) for inp in place2_inputs)
        assert has_wait_input, f"place2 should have a wait node as input, got {place2_inputs}"

    if len(wait_nodes) >= 2:
        # Check that place3 has the second wait as an input
        place3_inputs = flow.get("place3", "0", "input")
        has_wait_input = any("wait" in str(inp[0]) for inp in place3_inputs)
        assert has_wait_input, f"place3 should have a wait node as input, got {place3_inputs}"

        # Check that the waits are chained: second wait should depend on place2
        # Find the wait nodes
        wait_list = sorted(wait_nodes)
        if len(wait_list) >= 2:
            # The second wait should have place2 as input (creating the chain)
            second_wait = wait_list[1]
            second_wait_inputs = flow.get(second_wait[0], second_wait[1], "input")
            assert ("place2", "0") in second_wait_inputs, \
                f"Second wait should have place2 as input to form chain, got {second_wait_inputs}"

    assert flow.validate()


def test_wait_serialize_tool_tasks_four_parallel_nodes():
    """Test serialization with four parallel nodes - stronger test for chaining."""
    flow = Flowgraph("testflow")

    # Create four parallel openroad nodes
    flow.node("start", NOPTask())
    for i in range(4):
        flow.node("place", NOPTask(), index=i)
        flow.edge("start", "place", head_index=i)
        flow.set("place", str(i), "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    nodes = flow.get_nodes()
    wait_nodes = [n for n in nodes if "wait" in n[0]]

    # Should have 3 wait nodes for 4 parallel nodes to create a chain
    assert len(wait_nodes) == 3, \
        f"Expected 3 wait nodes for 4 parallel nodes, got {len(wait_nodes)}"

    # Verify execution order enforces serial execution: place/0 < place/1 < place/2 < place/3
    assert flow.get_execution_order() == (
        (("start", "0"),),
        (("place", "0"),),
        (("place.wait", "1"),),
        (("place", "1"),),
        (("place.wait", "2"),),
        (("place", "2"),),
        (("place.wait", "3"),),
        (("place", "3"),))

    # Verify the chain: place/0 -> place.wait/1 -> place/1 -> place.wait/2 ->
    # place/2 -> place.wait/3 -> place/3
    # This means:
    # - place/1 should have place.wait/1 as input
    # - place/2 should have place.wait/2 as input
    # - place/3 should have place.wait/3 as input

    for i in range(1, 4):
        inputs = flow.get("place", str(i), "input")
        has_expected_wait = any("place.wait" in inp[0] for inp in inputs)
        assert has_expected_wait, \
            f"place/{i} should have a place.wait node as input to ensure serial " \
            f"execution, got {inputs}"

    assert flow.validate()


def test_wait_serialize_tool_tasks_validates_serial_execution():
    """Test that serialization truly enforces serial execution order."""
    flow = Flowgraph("testflow")

    # Three parallel branches that must execute serially
    flow.node("start", NOPTask())
    flow.node("p1", NOPTask())
    flow.node("p2", NOPTask())
    flow.node("p3", NOPTask())
    flow.node("end", JoinTask())

    flow.edge("start", "p1")
    flow.edge("start", "p2")
    flow.edge("start", "p3")
    flow.edge("p1", "end")
    flow.edge("p2", "end")
    flow.edge("p3", "end")

    for step in ["p1", "p2", "p3"]:
        flow.set(step, "0", "tool", "openroad")

    Wait.serialize_tool_tasks(flow, "openroad")

    # Verify execution order is fully serialized
    assert flow.get_execution_order() == (
        (("start", "0"),),
        (("p1", "0"),),
        (("p2.wait", "0"),),
        (("p2", "0"),),
        (("p3.wait", "0"),),
        (("p3", "0"),),
        (("end", "0"),))

    assert flow.validate()
