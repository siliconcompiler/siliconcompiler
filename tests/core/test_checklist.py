import os
import pytest
import siliconcompiler

@pytest.mark.skip(reason="Deferring until new test/index change")
def test_checklist():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/syn/0')
    with open('build/test/job0/syn/0/yosys.log', 'w') as f:
        f.write('test')

    chip.set('metric','syn','0', 'errors', 1)
    chip.set('tool', 'yosys', 'task', 'syn', 'report', 'syn', '0', 'errors', 'yosys.log')
    chip.schema.record_history()

    #automated fail
    chip.set('checklist','iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist','iso', 'd0', 'task', ('job0', 'syn', '0'))
    assert not chip.check_checklist('iso', ['d0'])

    #automated pass
    chip.set('checklist', 'iso', 'd1', 'criteria', 'errors<2')
    chip.set('checklist','iso', 'd1', 'task', ('job0', 'syn', '0'))
    assert chip.check_checklist('iso', ['d1'])

    assert not chip.check_checklist('iso', ['d1'], check_ok=True)

    chip.set('checklist', 'iso', 'd1', 'ok', True)
    assert chip.check_checklist('iso', ['d1'], check_ok=True)

#########################
if __name__ == "__main__":
    test_checklist()
