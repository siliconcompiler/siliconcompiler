# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest
import re
import siliconcompiler
import logging


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
        pernode = chip.get(*key, field='pernode')
        if DEBUG:
            print(key, sctype, examples)
        for example in examples:
            if pernode != 'required':
                match = re.match(r'api\:\s+chip.(set|add|get)\((.*)\)',
                                 example)
            else:
                match = re.match(r'api\:\s+chip.(set|add|get)\((.*), step=(.*), index=(.*)\)',
                                 example)
            if match is not None:
                break

        assert match is not None, f'Illegal example for keypath {key} ({example})'

        if len(match.groups()) == 2:
            method, argstring = match.groups()
            step, index = None, None
        else:
            method, argstring, step, index = match.groups()

        if method == 'get':
            continue

        # Remove ' and whitespace from args
        argstring = re.sub(r'[\'\s]', '', argstring)

        # Passing len(key) as second argument to split ensures we only split up
        # to len(key) commas, preserving tuple values.
        *keypath, value = argstring.split(',', len(key))

        value = _cast(value, sctype)

        if match.group(1) == 'set':
            if DEBUG:
                print(*keypath, value)
            chip.set(*keypath, value, step=step, index=index, clobber=True)
        elif match.group(1) == 'add':
            chip.add(*keypath, value, step=step, index=index)

        if step is None and index is None and pernode == 'optional':
            # arbitrary step/index to avoid error
            step, index = 'syn', '0'
        result = chip.get(*keypath, step=step, index=index)
        assert result == value, f'Expected value {value} from keypath {keypath}. Got {result}.'

    chip.write_manifest('allvals.json')

    assert error == 0


def test_set_field_bool():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'doc', 'txt', False, field='copy')
    assert chip.get('input', 'doc', 'txt', field='copy') is False


def test_getkeys_invalid_keypath():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.getkeys('option', None)


def test_add_invalid_keypath():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.add('option', None, 'test_val')


def test_set_invalid_keypath():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('option', None, 'test_val')


def test_get_invalid_keypath():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.get('option', None)


def test_get_invalid_keypath_continue():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'continue', True)
    ret_val = chip.get('option', None)
    assert ret_val is None


def test_set_valid_keypath_to_none():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'scheduler', 'name', 'slurm')
    chip.set('option', 'scheduler', 'name', None)
    # arbitrary step/index
    jobscheduler = chip.get('option', 'scheduler', 'name', step='syn', index=0)
    assert jobscheduler is None
    assert chip._error is False


def test_set_field_error():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'continue', True)
    chip.set('input', 'doc', 'txt', 'asdf', field='copy')
    # expect copy flag unchanged and error triggered
    assert chip.get('input', 'doc', 'txt', field='copy') is True
    assert chip._error is True


def test_set_invalid_field():
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('input', 'doc', 'txt', 'bar', field='foo')


def test_set_add_field_list():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'doc', 'txt', 'Alyssa P. Hacker', field='author')
    chip.add('input', 'doc', 'txt', 'Ben Bitdiddle', field='author')
    assert chip.get('input', 'doc', 'txt', field='author') == ['Alyssa P. Hacker', 'Ben Bitdiddle']


def test_no_clobber_false():
    '''Regression test that clobber=False won't overwrite booleans that have
    been explicitly set to False.
    https://github.com/siliconcompiler/siliconcompiler/issues/1146
    '''
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'remote', False)
    chip.set('option', 'remote', True, clobber=False)

    assert chip.get('option', 'remote') is False


def test_get_no_side_effect():
    '''Test that get() of keypaths that don't exist yet doesn't create them.'''
    chip = siliconcompiler.Chip('test')

    # Surelog not set up yet
    assert chip.getkeys('tool', 'surelog', 'task') == []

    # Able to recover default value
    assert chip.get('tool', 'surelog', 'task', 'import', 'stdout', 'suffix',
                    step='import', index='0') == 'log'

    # Recovering default does not affect cfg
    assert chip.getkeys('tool', 'surelog', 'task') == []


@pytest.mark.nostrict
def test_set_enum_success():
    chip = siliconcompiler.Chip('test')
    assert 'test' not in chip.get('option', 'scheduler', 'name', field='enum')
    chip.add('option', 'scheduler', 'name', 'test', field='enum')
    chip.set('option', 'scheduler', 'name', 'test')
    assert chip.get('option', 'scheduler', 'name') == 'test'


def test_set_enum_fail():
    chip = siliconcompiler.Chip('test')
    assert 'test' not in chip.get('option', 'scheduler', 'name', field='enum')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.set('option', 'scheduler', 'name', 'test')


def test_set_list_as_set():
    chip = siliconcompiler.Chip('test')
    chip.add('input', 'rtl', 'verilog', set(['1234', '2345', '1234']))

    assert sorted(chip.get('input', 'rtl', 'verilog', step='test', index='0')) == ['1234', '2345']


def test_set_int_as_string():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'var', 'test', 1)

    assert chip.get('option', 'var', 'test') == ['1']


def test_set_bool_as_string():
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'var', 'test', True)

    assert chip.get('option', 'var', 'test') == ['true']


def test_pernode():
    chip = siliconcompiler.Chip('test')

    chip.set('asic', 'logiclib', 'mylib')
    chip.set('asic', 'logiclib', 'synlib', step='syn')
    chip.set('asic', 'logiclib', 'syn0lib', step='syn', index=0)
    chip.set('asic', 'logiclib', 'placelib', step='place', index=0, clobber=False)

    assert chip.get('asic', 'logiclib', step='floorplan', index=0) == ['mylib']
    assert chip.get('asic', 'logiclib', step='syn', index=0) == ['syn0lib']
    assert chip.get('asic', 'logiclib', step='syn', index=1) == ['synlib']
    assert chip.get('asic', 'logiclib', step='place', index=0) == ['mylib']


def test_pernode_get_global():
    chip = siliconcompiler.Chip('test')

    chip.set('asic', 'logiclib', 'mylib')
    chip.set('asic', 'logiclib', 'synlib', step='syn')
    chip.set('asic', 'logiclib', 'syn0lib', step='syn', index=0)

    assert chip.get('asic', 'logiclib', step='global') == ['mylib']
    assert chip.get('asic', 'logiclib', step='global', index='global') == ['mylib']


def test_pernode_set_global():
    chip = siliconcompiler.Chip('test')

    chip.set('asic', 'logiclib', 'mylib')
    assert chip.get('asic', 'logiclib', step='global') == ['mylib']

    chip.set('asic', 'logiclib', 'mylib1', step='global')
    assert chip.get('asic', 'logiclib', step='global') == ['mylib1']

    chip.set('asic', 'logiclib', 'mylib2', step='global', index='global')
    assert chip.get('asic', 'logiclib', step='global') == ['mylib2']


@pytest.mark.parametrize('field', ['filehash', 'package'])
def test_pernode_fields(field):
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'abcd', field=field)

    # Fallback to global
    assert chip.get('input', 'rtl', 'verilog', field=field) == ['abcd']
    assert chip.get('input', 'rtl', 'verilog', step='syn', field=field) == ['abcd']

    # Can override global
    chip.set('input', 'rtl', 'verilog', '1234', step='syn', field=field)
    assert chip.get('input', 'rtl', 'verilog', field=field) == ['abcd']
    assert chip.get('input', 'rtl', 'verilog', step='syn', field=field) == ['1234']

    # error, step/index required
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.set('tool', 'openroad', 'task', 'place', 'output', 'abc123', field=field)
    chip.set('tool', 'openroad', 'task', 'place', 'output', 'def456', field=field,
             step='place', index=0)
    chip.get('tool', 'openroad', 'task', 'place', 'output', field=field,
             step='place', index=0) == 'def456'


def test_set_package():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'abcd')

    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0) == ['abcd']
    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0, field='package') == [None]

    chip.set('input', 'rtl', 'verilog', 'edfg', package='dep', clobber=False)

    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0) == ['abcd']
    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0, field='package') == [None]

    chip.set('input', 'rtl', 'verilog', 'abcd', package='dep')

    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0) == ['abcd']
    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0, field='package') == ['dep']


def test_set_package_multiple_files():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', ['abcd', 'efgh'])

    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0) == ['abcd', 'efgh']
    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0, field='package') == [None, None]

    chip.add('input', 'rtl', 'verilog', 'ijkl', package='dep')

    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0) == ['abcd', 'efgh', 'ijkl']
    assert chip.get('input', 'rtl', 'verilog', step='syn', index=0, field='package') == \
        [None, None, 'dep']


def test_empty_file_path():
    '''
    Set global value without clobber and then copy, this should not crash
    '''
    chip = siliconcompiler.Chip('test')
    chip.set('tool', 'surelog', 'path', 'test', clobber=False)
    chip.schema.copy()


def test_signature_type():
    '''Test that whether signature field is a list or scalar corresponds to
    parameter's type.'''
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.set('option', 'quiet', ['xyz'], field='signature')
    assert chip.get('option', 'quiet', field='signature') is None

    chip.set('option', 'quiet', 'xyz', field='signature')
    assert chip.get('option', 'quiet', field='signature') == 'xyz'

    chip.set('asic', 'logiclib', ['xyz'], field='signature')
    assert chip.get('asic', 'logiclib', field='signature') == ['xyz']


def test_register_source(caplog):
    chip = siliconcompiler.Chip('test')
    chip.logger = logging.getLogger()

    name = 'siliconcompiler_data'
    path = 'git+https://github.com/siliconcompiler/siliconcompiler'
    ref = 'main'
    chip.register_source(name, path, ref)

    assert chip.get('package', 'source', name, 'path') == path
    assert chip.get('package', 'source', name, 'ref') == ref

    different_path = 'git+https://github.com/different-repo/siliconcompiler'
    different_ref = 'different-ref'
    chip.register_source(name, different_path, different_ref)

    assert chip.get('package', 'source', name, 'path') == different_path
    assert chip.get('package', 'source', name, 'ref') == different_ref
    assert f'The data source {name} already exists.' in caplog.text
    assert f'Overwriting path {path} with {different_path}.' in caplog.text
    assert f'Overwriting ref {ref} with {different_ref}.' in caplog.text


##################################
def test_lock():
    '''API test for show method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')
    chip.set('design', True, field="lock")
    chip.set('design', "FAIL")

    assert chip.get('design') == "gcd"


##################################
def test_unlock():
    '''API test for show method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')
    chip.set('design', True, field="lock")
    chip.set('design', "FAIL")
    assert chip.get('design') == "gcd"
    chip.set('design', False, field="lock")
    chip.set('design', "PASS")
    assert chip.get('design') == "PASS"


#########################
if __name__ == "__main__":
    test_setget()
