# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest
import re
import siliconcompiler

def _cast(val, sctype):
    if sctype.startswith('['):
        # TODO: doesn't handle examples w/ multiple list items (we do not have
        # currently)
        subtype = sctype.strip('[]')
        return [_cast(val.strip('[]'), subtype)]
    elif sctype.startswith('('):
        vals = val.strip('()').split(',')
        subtypes = sctype.strip('()').split(',')
        return tuple(_cast(v.strip(), subtype.strip()) for v, subtype in zip(vals, subtypes))
    elif sctype == 'float':
        return float(val)
    elif sctype == 'int':
        return int(val)
    elif sctype == 'bool':
        return bool(val)
    else:
        # everything else (str, file, dir) is treated like a string
        return val

def test_setget():
    '''API test for set/get methods

    Performs set or add based on API example for each entry in schema and
    ensures that we can recover the same value back. Also tests that keypaths in
    schema examples are valid.
    '''

    DEBUG = False
    chip = siliconcompiler.Chip('test')
    error = 0

    allkeys = chip.allkeys()
    for key in allkeys:
        sctype = chip.get(*key, field='type')
        examples = chip.get(*key, field='example')
        if DEBUG:
            print(key, sctype, examples)
        for example in examples:
            match = re.match(r'api\:\s+chip.(set|add|get)\((.*)\)', example)
            if match is not None:
                break

        assert match is not None, f'Illegal example for keypath {key}'

        if match.group(1) == 'get':
            continue

        # Remove ' and whitespace from args
        argstring = re.sub(r'[\'\s]', '', match.group(2))

        # Passing len(key) as second argument to split ensures we only split up
        # to len(key) commas, preserving tuple values.
        *keypath, value = argstring.split(',', len(key))

        value = _cast(value, sctype)

        if match.group(1) == 'set':
            if DEBUG:
                print(*keypath, value)
            chip.set(*keypath, value, clobber=True)
        elif match.group(1) == 'add':
            chip.add(*keypath, value)

        result = chip.get(*keypath)
        assert result == value, f'Expected value {value} from keypath {keypath}. Got {result}.'

    chip.write_manifest('allvals.json')

    assert(error==0)

def test_set_field_bool():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'doc', 'txt', False, field='copy')
    assert chip.get('input', 'doc', 'txt', field='copy') is False

def test_getkeys_invalid_field():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.getkeys('option', None)

def test_add_invalid_field():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.add('option', None, 'test_val')

def test_set_invalid_field():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('option', None, 'test_val')

def test_get_invalid_field():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.get('option', None)

def test_get_invalid_field_continue():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'continue', True)
    ret_val = chip.get('option', None)
    assert ret_val == None

def test_set_valid_field_to_none():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'jobscheduler', 'slurm')
    chip.set('option', 'jobscheduler', None)
    jobscheduler = chip.get('option', 'jobscheduler')
    assert jobscheduler == None
    assert chip._error == False

def test_set_field_error():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'continue', True)
    chip.set('input', 'doc', 'txt', 'asdf', field='copy')
    # expect copy flag unchanged and error triggered
    assert chip.get('input', 'doc', 'txt', field='copy') is True
    assert chip._error == True

def test_set_add_field_list():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'doc', 'txt', 'Alyssa P. Hacker', field='author')
    chip.add('input', 'doc', 'txt', 'Ben Bitdiddle', field='author')
    assert chip.get('input', 'doc', 'txt', field='author') == ['Alyssa P. Hacker', 'Ben Bitdiddle']

def test_no_clobber_false():
    '''Regression test that clobber=False won't overwrite booleans that have
    been explictly set to False.
    https://github.com/siliconcompiler/siliconcompiler/issues/1146
    '''
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'remote', False)
    chip.set('option', 'remote', True, clobber=False)

    assert chip.get('option', 'remote') == False

def test_get_no_side_effect():
    '''Test that get() of keypaths that don't exist yet doesn't create them.'''
    chip = siliconcompiler.Chip('test')

    # Surelog not set up yet
    assert chip.getkeys('tool', 'surelog', 'task') == []

    # Able to recover default value
    assert chip.get('tool', 'surelog', 'task', 'import', 'stdout', 'import', '0', 'suffix') == 'log'

    # Recovering default does not affect cfg
    assert chip.getkeys('tool', 'surelog', 'task') == []

def test_clear():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'remote', True)
    assert chip.get('option', 'remote') == True

    # Clearing a keypath resets it to default value
    chip.clear('option','remote')
    assert chip.get('option', 'remote') == False

    # Able to set a keypath after it's been cleared even if clobber=False
    chip.set('option', 'remote', True, clobber=False)
    assert chip.get('option', 'remote') == True

def test_set_enum_success():
    chip = siliconcompiler.Chip('test')
    chip.add('option', 'mode', 'asic_new', field='enum')
    chip.set('option', 'mode', 'asic_new')
    assert chip.get('option', 'mode') == 'asic_new'

def test_set_enum_fail():
    chip = siliconcompiler.Chip('test')
    try:
        chip.set('option', 'mode', 'asic_new')
    except siliconcompiler.SiliconCompilerError:
        assert True
        return
    assert False

#########################
if __name__ == "__main__":
    test_setget()
