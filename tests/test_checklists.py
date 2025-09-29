import logging
import os
import pytest

from siliconcompiler import Project, NodeStatus
from siliconcompiler import Flowgraph, Design
from siliconcompiler.schema import EditableSchema, Parameter, PerNode

from siliconcompiler.checklist import Checklist


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

    with pytest.raises(ValueError, match="Illegal checklist criteria: fmax==.*"):
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
