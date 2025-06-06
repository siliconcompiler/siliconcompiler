import os
import pytest

from siliconcompiler import Chip
from siliconcompiler.checklist import ChecklistSchema


@pytest.fixture
def chip():
    from siliconcompiler.targets import freepdk45_demo
    from siliconcompiler import NodeStatus
    chip = Chip('test')
    chip.use(freepdk45_demo)

    for step, index in chip.schema.get("flowgraph", "asicflow", field="schema").get_nodes():
        chip.set('record', 'status', NodeStatus.SUCCESS, step=step, index=index)

    return chip


def test_check_fail(chip):
    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/syn/0')
    with open('build/test/job0/syn/0/yosys.log', 'w') as f:
        f.write('test')

    chip.set('metric', 'errors', 1, step='syn', index='0')
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'report', 'errors', 'yosys.log',
             step='syn', index='0')
    chip.schema.record_history()

    checklist = ChecklistSchema()
    checklist.set("d0", "criteria", "errors==0")
    checklist.set("d0", "task", ('job0', 'syn', '0'))

    assert not checklist.check(chip)


def test_check_pass(chip):
    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/syn/0')
    with open('build/test/job0/syn/0/yosys.log', 'w') as f:
        f.write('test')

    chip.set('metric', 'errors', 1, step='syn', index='0')
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'report', 'errors', 'yosys.log',
             step='syn', index='0')
    chip.schema.record_history()

    checklist = ChecklistSchema()
    checklist.set("d1", "criteria", "errors<2")
    checklist.set("d1", "task", ('job0', 'syn', '0'))

    # automated pass
    assert checklist.check(chip, logger=chip.logger)
