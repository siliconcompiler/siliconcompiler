import logging
import os
import pytest

from siliconcompiler import NodeStatus
from siliconcompiler import RecordSchema, MetricSchema, ToolSchema, FlowgraphSchema
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter

from siliconcompiler.checklist import ChecklistSchema


@pytest.fixture
def project():
    class TestFlow(FlowgraphSchema):
        def __init__(self):
            super().__init__("testflow")

            self.node("teststep", "testtool.testtask")

    class Project(BaseSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("flowgraph", "testflow", TestFlow())
            schema.insert("metric", MetricSchema())
            schema.insert("record", RecordSchema())
            schema.insert("tool", "testtool", ToolSchema("testtool"))
            schema.insert("option", "flow", Parameter("str"))

            self.set("record", "status", NodeStatus.SUCCESS, step="teststep", index="0")
            self.set("option", "flow", "testflow")

        def history(self, name):
            return self

        @property
        def logger(self):
            return logging.getLogger()

    return Project()


def test_check_fail_unmet_spec(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/teststep/0')
    with open('build/test/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'testtool', 'task', 'testtask', 'report', 'errors',
                'build/test/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = ChecklistSchema()
    checklist.set("d0", "criteria", "errors==0")
    checklist.set("d0", "task", ('job0', 'teststep', '0'))

    schema = EditableSchema(project)
    schema.insert("checklist", checklist)

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "d0 criteria errors==0 (1==0) unmet by job job0 with step teststep0 and task " \
        "testtool/testtask" in caplog.text


def test_check_fail_invalid_node(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/teststep/0')
    with open('build/test/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'testtool', 'task', 'testtask', 'report', 'errors',
                'build/test/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = ChecklistSchema()
    checklist.set("d0", "criteria", "errors==0")
    checklist.set("d0", "task", ('job0', 'notvalid', '0'))

    schema = EditableSchema(project)
    schema.insert("checklist", checklist)

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "notvalid0 not found in flowgraph for job0" in caplog.text


def test_check_fail_invalid_missing_docs(project, caplog):
    project.set('metric', 'errors', 1, step='teststep', index='0')

    checklist = ChecklistSchema()
    checklist.set("d0", "criteria", "errors==1")
    checklist.set("d0", "task", ('job0', 'teststep', '0'))

    schema = EditableSchema(project)
    schema.insert("checklist", checklist)

    project.logger.setLevel(logging.INFO)

    assert checklist.check() is False
    assert "d0 criteria errors==1 met by job job0 with step teststep0 and task testtool/testtask" \
        in caplog.text
    assert "No reports generated for metric errors in job job0 with step teststep0 and task " \
        "testtool/testtask" in caplog.text
    assert "No report documenting item d0" in caplog.text


def test_check_pass(project, caplog):
    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/teststep/0')
    with open('build/test/job0/teststep/0/testtask.log', 'w') as f:
        f.write('test')

    project.set('metric', 'errors', 1, step='teststep', index='0')
    project.set('tool', 'testtool', 'task', 'testtask', 'report', 'errors',
                'build/test/job0/teststep/0/testtask.log',
                step='teststep', index='0')

    checklist = ChecklistSchema()
    checklist.set("d1", "criteria", "errors<2")
    checklist.set("d1", "task", ('job0', 'teststep', '0'))

    schema = EditableSchema(project)
    schema.insert("checklist", checklist)

    project.logger.setLevel(logging.INFO)

    # automated pass
    assert checklist.check() is True
    assert "d1 criteria errors<2 met by job job0 with step teststep0 and task testtool/testtask" \
        in caplog.text
