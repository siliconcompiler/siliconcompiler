import os
import siliconcompiler
import pytest


def test_checklist():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/syn/0')
    with open('build/test/job0/syn/0/yosys.log', 'w') as f:
        f.write('test')

    chip.set('metric', 'errors', 1, step='syn', index='0')
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'report', 'errors', 'yosys.log',
             step='syn', index='0')
    chip.schema.record_history()

    # automated fail
    chip.set('checklist', 'iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'syn', '0'))
    assert not chip.check_checklist('iso', ['d0'])

    # automated pass
    chip.set('checklist', 'iso', 'd1', 'criteria', 'errors<2')
    chip.set('checklist', 'iso', 'd1', 'task', ('job0', 'syn', '0'))
    assert chip.check_checklist('iso', ['d1'])

    assert not chip.check_checklist('iso', ['d1'], check_ok=True)

    chip.set('checklist', 'iso', 'd1', 'ok', True)
    assert chip.check_checklist('iso', ['d1'], check_ok=True)


def test_checklist_no_reports():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('metric', 'errors', 1, step='syn', index='0')
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'report', 'errors', 'yosys.log',
             step='syn', index='0')
    chip.schema.record_history()

    # automated pass
    chip.set('checklist', 'iso', 'd1', 'criteria', 'errors<2')
    chip.set('checklist', 'iso', 'd1', 'task', ('job0', 'syn', '0'))
    assert chip.check_checklist('iso', ['d1'], require_reports=False)


def test_checklist_no_non_logged_keys():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    metrics = (
        'tasktime',
        'exetime',
        'memory'
    )

    for metric in metrics:
        chip.set('metric', metric, 10, step='syn', index='0')
    chip.schema.record_history()

    for metric in metrics:
        chip.add('checklist', 'iso', 'd0', 'criteria', f'{metric}==10')
    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'syn', '0'))
    assert chip.check_checklist('iso', ['d0'])


def test_missing_check_checklist():
    '''
    Check that check_checklist will generate an error on missing items
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    # automated fail
    chip.set('checklist', 'iso', 'd1', 'criteria', 'errors==0')
    chip.set('checklist', 'iso', 'd1', 'task', ('job0', 'syn', '0'))
    assert not chip.check_checklist('iso', ['d0'])


def test_missing_job():
    '''
    Check that check_checklist will generate an error on missing jobs
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    # automated fail
    chip.set('checklist', 'iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist', 'iso', 'd0', 'task', ('job1', 'syn', '0'))
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.check_checklist('iso', ['d0'])


def test_missing_step():
    '''
    Check that check_checklist will generate an error on missing steps
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.schema.record_history()

    # automated fail
    chip.set('checklist', 'iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'synth', '0'))
    with pytest.raises(siliconcompiler.SiliconCompilerError, match='synth not found in flowgraph'):
        chip.check_checklist('iso', ['d0'])


def test_missing_index():
    '''
    Check that check_checklist will generate an error on missing indexes
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.schema.record_history()

    # automated fail
    chip.set('checklist', 'iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'syn', '1'))
    with pytest.raises(siliconcompiler.SiliconCompilerError, match='syn1 not found in flowgraph'):
        chip.check_checklist('iso', ['d0'])


def test_missing_checklist():
    '''
    Check if check_checklist fails when checklist has not been loaded.
    '''

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    assert not chip.check_checklist('iso')


def test_criteria_formatting_float_pass():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    # Test won't work if file doesn't exist
    os.makedirs('build/test/job0/syn/0')
    with open('build/test/job0/syn/0/yosys.log', 'w') as f:
        f.write('test')

    chip.set('tool', 'yosys', 'task', 'syn_asic', 'report', 'fmax', 'yosys.log',
             step='syn', index='0')
    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'syn', '0'))

    for criteria in (
        '1.0',
        '+1.0',
        '-1.0',
        '1.0e+09',
        '1.0e-09',
        '1.0e-9',
        ' 1.0e-9 ',
    ):
        chip.set('metric', 'fmax', criteria.strip(), step='syn', index='0')
        chip.schema.record_history()
        chip.set('checklist', 'iso', 'd0', 'criteria', f'fmax=={criteria}')

        assert chip.check_checklist('iso', ['d0'])


def test_criteria_formatting_float_fail():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('checklist', 'iso', 'd0', 'task', ('job0', 'syn', '0'))

    for criteria in (
        '1.0.0',
        '+ 1.0',
        '1.0e+09.5',
        '1.0 e-09',
        '1.0e -9',
    ):
        chip.set('metric', 'fmax', 5, step='syn', index='0')
        chip.schema.record_history()
        chip.set('checklist', 'iso', 'd0', 'criteria', f'fmax=={criteria}')

        with pytest.raises(siliconcompiler.SiliconCompilerError):
            assert not chip.check_checklist('iso', ['d0'])


#########################
if __name__ == "__main__":
    test_checklist()
