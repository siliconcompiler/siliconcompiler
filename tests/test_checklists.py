import logging
import os
import pytest

from pathlib import Path, PosixPath

from siliconcompiler import Project, NodeStatus
from siliconcompiler import Flowgraph, Design
from siliconcompiler.schema import EditableSchema, Parameter, PerNode

from siliconcompiler.checklist import Checklist, Criteria


@pytest.fixture
def project():
    class TestFlow(Flowgraph):
        def __init__(self):
            super().__init__("testflow")

            self.node("teststep", "siliconcompiler.tools.builtin.nop/NOPTask")

    class TestProject(Project):
        def __init__(self):
            super().__init__(Design("testdesign"))

            self.set_flow(TestFlow())

            self.set("record", "status", NodeStatus.SUCCESS, step="teststep", index="0")

        @property
        def logger(self):
            return logging.getLogger()

    return TestProject()


def test_criteria_get_set_description():
    criteria = Criteria()
    # Test description
    assert criteria.get_description() is None
    criteria.set_description("Test Description")
    assert criteria.get_description() == "Test Description"


def test_criteria_get_set_requirement():
    criteria = Criteria()
    # Test requirement
    assert criteria.get_requirement() is None
    criteria.set_requirement("Test Requirement")
    assert criteria.get_requirement() == "Test Requirement"


def test_criteria_get_set_dataformat():
    criteria = Criteria()
    # Test dataformat
    assert criteria.get_dataformat() is None
    criteria.set_dataformat("Test Dataformat")
    assert criteria.get_dataformat() == "Test Dataformat"


def test_criteria_get_set_rationale():
    criteria = Criteria()
    # Test rationale
    assert criteria.get_rationale() == []
    criteria.add_rationale("Rationale 1")
    assert criteria.get_rationale() == ["Rationale 1"]
    criteria.add_rationale(["Rationale 2", "Rationale 3"])
    assert criteria.get_rationale() == ["Rationale 1", "Rationale 2", "Rationale 3"]
    criteria.add_rationale("Rationale 4", clobber=True)
    assert criteria.get_rationale() == ["Rationale 4"]


def test_criteria_get_set_criteria():
    criteria = Criteria()
    # Test criteria
    assert criteria.get_criteria() == []
    criteria.add_criteria("errors == 0")
    assert criteria.get_criteria() == ["errors == 0"]
    criteria.add_criteria(["warnings == 0", "setup >= 0"])
    assert criteria.get_criteria() == ["errors == 0", "warnings == 0", "setup >= 0"]
    criteria.add_criteria("hold >= 0", clobber=True)
    assert criteria.get_criteria() == ["hold >= 0"]


def test_criteria_get_set_task():
    criteria = Criteria()
    # Test task
    assert criteria.get_task() == []
    criteria.add_task(("job0", "syn", "0"))
    assert criteria.get_task() == [("job0", "syn", "0")]
    criteria.add_task([("job0", "place", "0"), ("job0", "cts", "0")])
    assert criteria.get_task() == [("job0", "syn", "0"),
                                     ("job0", "place", "0"),
                                     ("job0", "cts", "0")]
    criteria.add_task(("job1", "route", "0"), clobber=True)
    assert criteria.get_task() == [("job1", "route", "0")]


def test_criteria_get_set_report():
    criteria = Criteria()
    # Test report
    assert criteria.get_report() == []
    criteria.add_report("report1.log")
    assert criteria.get_report() == ["report1.log"]
    criteria.add_report(["report2.log", "report3.json"])
    assert criteria.get_report() == ["report1.log", "report2.log", "report3.json"]
    criteria.add_report("final.rpt", clobber=True)
    assert criteria.get_report() == ["final.rpt"]


def test_criteria_get_set_waiver():
    criteria = Criteria()
    # Test waiver
    assert criteria.get_waiver("errors") == []
    waiver_path = Path("waiver1.txt")
    criteria.add_waiver("errors", waiver_path)
    assert criteria.get_waiver("errors") == ["waiver1.txt"]
    criteria.add_waiver("errors", ["waiver2.txt", "waiver3.txt"])
    assert criteria.get_waiver("errors") == ["waiver1.txt", "waiver2.txt", "waiver3.txt"]
    criteria.add_waiver("errors", "final_waiver.txt", clobber=True)
    assert criteria.get_waiver("errors") == ["final_waiver.txt"]


def test_criteria_get_set_ok():
    criteria = Criteria()
    # Test ok
    assert not criteria.get_ok()
    criteria.set_ok(True)
    assert criteria.get_ok()


def test_checklist_criteria_methods_make():
    checklist = Checklist()
    # Test make_criteria
    item1 = checklist.make_criteria("item1")
    assert isinstance(item1, Criteria)
    assert "item1" in checklist.getkeys()

    # Test make_criteria raises error on duplicate
    with pytest.raises(ValueError):
        checklist.make_criteria("item1")


def test_checklist_criteria_methods_get():
    checklist = Checklist()
    item1 = checklist.make_criteria("item1")

    # Test get_criteria by name
    retrieved_item1 = checklist.get_criteria("item1")
    assert retrieved_item1 == item1


def test_checklist_criteria_methods_fail():
    checklist = Checklist()
    # Test get_criteria raises error on not found
    with pytest.raises(ValueError):
        checklist.get_criteria("nonexistent_item")


def test_checklist_criteria_methods():
    checklist = Checklist()
    checklist.make_criteria("item1")

    # Test get_criteria to get all
    all_criteria = checklist.get_criteria()
    assert isinstance(all_criteria, dict)
    assert "item1" in all_criteria
    assert all(isinstance(c, Criteria) for c in all_criteria.values())
    assert len(all_criteria) == 1

    # Add another and get all again
    checklist.make_criteria("item2")
    all_criteria = checklist.get_criteria()
    assert len(all_criteria) == 2
    assert "item2" in all_criteria


def test_check_fail_unmet_spec(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d0", "criteria", "errors==0")
    checklist.set("d0", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "d0 criteria errors==0 (1==0) unmet by job job0 with step teststep/0 and task " \
        "builtin/nop." in caplog.text


def test_check_fail_invalid_node(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d0", "criteria", "errors==0")
    checklist.set("d0", "task", ('job0', 'notvalid', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "notvalid/0 not found in flowgraph for job0" in caplog.text


def test_check_fail_invalid_missing_docs(project, caplog):
    project.set('metric', 'errors', 1, step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d0", "criteria", "errors==1")
    checklist.set("d0", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "d0 criteria errors==1 met by job job0 with step teststep/0 and task builtin/nop." \
        in caplog.text
    assert "No reports generated for metric errors in job job0 with step teststep/0 and task " \
        "builtin/nop" in caplog.text
    assert "No report documenting item d0" in caplog.text


def test_check_pass(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", "errors<2")
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    # automated pass
    assert checklist.check() is True
    assert "d1 criteria errors<2 met by job job0 with step teststep/0 and task builtin/nop." \
        in caplog.text


def test_check_item_missing(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", "errors<2")
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    # automated pass
    assert checklist.check(items=["d0"]) is False
    assert "d0 is not a check in testchecklist." in caplog.text


def test_check_node_skipped(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')
    project.set("record", "status", NodeStatus.SKIPPED, step="teststep", index="0")

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", "errors<2")
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    # automated pass
    assert checklist.check() is True
    assert "teststep/0 was skipped" in caplog.text


def test_check_non_metric(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'errors',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", "error<2")
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    project.logger.setLevel(logging.INFO)

    # automated pass
    assert checklist.check() is False
    assert "Criteria must use legal metrics only: error<2" in caplog.text


@pytest.mark.parametrize("criteria", (
        '1.0.0',
        '+ 1.0',
        '1.0e+09.5',
        '1.0 e-09',
        '1.0e -9',
    ))
def test_check_criteria_formatting_float_fail(project, criteria):
    EditableSchema(project).insert("metric", "fmax", Parameter("float", pernode=PerNode.REQUIRED))
    project.set('metric', 'fmax', 5, step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", f'fmax=={criteria}')
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    with pytest.raises(ValueError, match="^Illegal checklist criteria: fmax==.*$"):
        checklist.check()


@pytest.mark.parametrize("criteria", (
        '1.0',
        '+1.0',
        '-1.0',
        '1.0e+09',
        '1.0e-09',
        '1.0e-9',
        ' 1.0e-9 ',
    ))
def test_check_criteria_formatting_float_pass(project, criteria):
    # Test won't work if file doesn't exist
    os.makedirs('build/testdesign/job0/teststep/0')
    with open('build/testdesign/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    EditableSchema(project).insert("metric", "fmax", Parameter("float", pernode=PerNode.REQUIRED))
    print(project.getkeys("metric"))

    project.set('metric', 'fmax', criteria.strip(), step='teststep', index='0')
    project.set('tool', 'builtin', 'task', 'nop', 'report', 'fmax',
                'build/testdesign/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = Checklist("testchecklist")
    checklist.set("d1", "criteria", f'fmax=={criteria}')
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    project.add_dep(checklist)
    project._record_history()

    assert checklist.check() is True
