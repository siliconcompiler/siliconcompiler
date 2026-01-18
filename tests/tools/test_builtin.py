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
    MuxTask, VerifyTask, ImportFilesTask, FilterTask
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


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask, VerifyTask])
def tets_run(cls):
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


@pytest.mark.parametrize("cls", [NOPTask, JoinTask, MinimumTask, MaximumTask, MuxTask, VerifyTask])
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
