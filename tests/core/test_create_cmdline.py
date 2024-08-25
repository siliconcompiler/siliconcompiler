import re
import pytest

import siliconcompiler


@pytest.fixture
def do_cli_test(monkeypatch):
    def run(args, switchlist=None, input_map=None, additional_args=None, chip=None):
        if not chip:
            chip = siliconcompiler.Chip('test')
        monkeypatch.setattr('sys.argv', args)
        print('sys.argv', args)
        args = chip.create_cmdline('sc',
                                   switchlist=switchlist,
                                   input_map=input_map,
                                   additional_args=additional_args)
        # Store additional args in chip object to make testing easier
        chip.args = args
        return chip
    return run


@pytest.mark.nostrict
def test_cli_prevalues(do_cli_test):
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'entrypoint', '1234')
    chip.input('test.v')

    do_cli_test(['sc', '-input', 'rtl verilog testing.v'], chip=chip)

    assert chip.get('option', 'entrypoint') == '1234'
    assert chip.get('input', 'rtl', 'verilog') == ['test.v', 'testing.v']


@pytest.mark.nostrict
def test_cli_prevalues_override(do_cli_test):
    chip = siliconcompiler.Chip('test')
    chip.set('option', 'entrypoint', '1234')
    chip.input('test.v')

    assert chip.get('option', 'entrypoint') == '1234'

    do_cli_test(['sc', '-entrypoint', '5678'], chip=chip)

    assert chip.get('input', 'rtl', 'verilog') == ['test.v']
    assert chip.get('option', 'entrypoint') == '5678'


def test_cli_multi_source(do_cli_test):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc',
            '-input', 'rtl verilog examples/ibex/ibex_alu.v',
            '-input', 'rtl verilog examples/ibex/ibex_branch_predict.v',
            '-target', 'freepdk45_demo']

    chip = do_cli_test(args)

    sources = chip.get('input', 'rtl', 'verilog', step='import', index=0)
    assert sources == ['examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option', 'target') == 'siliconcompiler.targets.freepdk45_demo'


def test_cli_include_flag(do_cli_test):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    args = ['sc',
            '-input', 'rtl verilog source.v',
            '-I', 'include/inc1', '+incdir+include/inc2']

    chip = do_cli_test(args)

    assert chip.get('input', 'rtl', 'verilog', step='import', index=0) == ['source.v']
    assert chip.get('option', 'idir') == ['include/inc1', 'include/inc2']
    assert chip.get('option', 'idir', field='package') == [None, None]


def test_optmode(do_cli_test):
    '''Test optmode special handling.'''
    args = ['sc', '-O3']

    chip = do_cli_test(args)

    # arbitrary step/index
    assert chip.get('option', 'optmode', step='import', index=0) == 'O3'


def test_pernode_boolean(do_cli_test):
    '''Test handling of pernode with booleans.'''
    args = ['sc', '-breakpoint', 'syn', '-breakpoint', 'floorplan true']

    chip = do_cli_test(args)

    # arbitrary index
    assert chip.get('option', 'breakpoint', step='syn', index=0) is True
    assert chip.get('option', 'breakpoint', step='floorplan', index=0) is True


def test_pernode_string(do_cli_test):
    '''Test handling of pernode with strings.'''
    args = ['sc', '-loglevel', 'info', '-loglevel', 'syn debug']

    chip = do_cli_test(args)

    # arbitrary index
    assert chip.get('option', 'loglevel', step='import', index=0) == 'info'
    assert chip.get('option', 'loglevel', step='syn', index=0) == 'debug'


def test_spaces_in_value(do_cli_test):
    desc = 'My package description'
    args = ['sc', '-package_description', desc]

    chip = do_cli_test(args)

    assert chip.get('package', 'description') == desc


def test_limited_switchlist(do_cli_test):
    args = ['sc', '-loglevel', 'debug', '-var', 'foo bar']
    chip = do_cli_test(args, switchlist=['-loglevel', '-var'])

    assert chip.get('option', 'loglevel', step='import', index=0) == 'debug'
    assert chip.get('option', 'var', 'foo') == ['bar']


def test_pernode_optional(do_cli_test):
    '''Ensure we can specify pernode overrides from CLI, and that they support
    spaces in values.'''
    args = ['sc']
    args += ['-asic_logiclib', 'syn "syn lib"']
    args += ['-asic_logiclib', 'syn 1 "\\"syn1\\" lib"']
    args += ['-asic_logiclib', '"my lib"']

    chip = do_cli_test(args)

    assert chip.get('asic', 'logiclib', step='floorplan', index=0) == ['my lib']
    assert chip.get('asic', 'logiclib', step='syn', index=0) == ['syn lib']
    assert chip.get('asic', 'logiclib', step='syn', index=1) == ['"syn1" lib']


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
        return val.strip('"')


def test_additional_parameters(do_cli_test):
    args = ['sc',
            '-input', 'rtl verilog examples/ibex/ibex_alu.v',
            '-input', 'rtl verilog examples/ibex/ibex_branch_predict.v',
            '-target', 'freepdk45_demo',
            '-testing_bool',
            '-testing_str', 'this is a string',
            '-testing_int', '12']

    additional_args = {
        '-testing_bool': {
            'action': 'store_true'
        },
        '-testing_str': {
            'type': str
        },
        '-testing_int': {
            'type': int
        }
    }

    chip = do_cli_test(args, additional_args=additional_args)

    assert chip.args['testing_bool']
    assert chip.args['testing_str'] == 'this is a string'
    assert chip.args['testing_int'] == 12

    sources = chip.get('input', 'rtl', 'verilog', step='import', index=0)
    assert sources == ['examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option', 'target') == 'siliconcompiler.targets.freepdk45_demo'


def test_additional_parameters_not_used(do_cli_test):
    args = ['sc',
            '-input', 'rtl verilog examples/ibex/ibex_alu.v',
            '-input', 'rtl verilog examples/ibex/ibex_branch_predict.v',
            '-target', 'freepdk45_demo',
            '-testing_bool']

    additional_args = {
        '-testing_bool': {
            'action': 'store_true'
        },
        '-testing_str': {
            'type': str
        },
        '-testing_int': {
            'type': int
        }
    }

    chip = do_cli_test(args, additional_args=additional_args)

    assert chip.args['testing_bool']
    assert chip.args['testing_str'] is None
    assert chip.args['testing_int'] is None

    sources = chip.get('input', 'rtl', 'verilog', step='import', index=0)
    assert sources == ['examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option', 'target') == 'siliconcompiler.targets.freepdk45_demo'


def test_cli_examples(do_cli_test, monkeypatch):
    # Need to mock this function, since our cfg CLI example will try to call it
    # on a fake manifest.
    def _mock_read_manifest(chip, manifest, **kwargs):
        # nop
        pass
    monkeypatch.setattr(siliconcompiler.Schema, 'read_manifest', _mock_read_manifest)

    Debug = False
    did_something = True
    example_index = 0
    while (did_something):
        args = ['sc']
        did_something = False
        chip = siliconcompiler.Chip('test')
        chip.remove('package', 'source', 'siliconcompiler')
        expected_data = []
        for keypath in chip.allkeys():
            if Debug:
                print(keypath)
            examples = chip.get(*keypath, field='example')
            examples = [e for e in examples if e.startswith('cli')]
            if len(examples) <= example_index:
                continue
            did_something = True
            example = examples[example_index]
            match = re.match(r'cli\: (\S+)(?:\s(.*))?', example)
            assert match is not None, f'Invalid CLI example: {example}'

            switch, value = match.groups()
            if value is None:
                value = ''

            if len(value.split(' ')) > 1:
                assert value[0] == "'" and value[-1] == "'", \
                    f'Multi-word value must be surrounded by quotes: {example}'
            value = value.strip("'")

            default_count = keypath.count('default')
            assert len(value.split(' ')) >= default_count + 1, \
                f'Not enough values to fill in default keys: {keypath}'
            if chip.get(*keypath, field='pernode') == 'required':
                *free_keys, step, index, expected_val = value.split(' ', default_count + 2)
            else:
                *free_keys, expected_val = value.split(' ', default_count)
                step, index = None, None
            typestr = chip.get(*keypath, field='type')
            replaced_keypath = [free_keys.pop(0) if key == 'default' else key for key in keypath]

            # Special cases
            if keypath == ('option', 'optmode') and switch.startswith('-O'):
                expected_val = switch.lstrip('-')
            elif keypath == ('option', 'define') and switch.startswith('-D'):
                expected_val = switch[len('-D'):]
            elif switch.startswith('+incdir+'):
                expected_val = switch[len('+incdir+'):]
            elif switch.startswith('+libext+'):
                expected_val = switch[len('+libext+'):]

            # Handle target specially since it affects other values
            if keypath == ('option', 'target'):
                c = do_cli_test(['sc', switch, value])
                assert c.schema.get(*replaced_keypath, step=step, index=index) == \
                    f'siliconcompiler.targets.{expected_val}'
                continue

            args.append(switch)
            if value:
                args.append(value)

            if expected_val:
                expected = (replaced_keypath, step, index, _cast(expected_val, typestr))
            else:
                assert typestr == 'bool', 'Implicit value only allowed for boolean'
                expected = (replaced_keypath, step, index, True)

            expected_data.append(expected)

        c = do_cli_test(args)

        for kp, step, index, val in expected_data:
            print("Check", kp, c.schema.get(*kp, step=step, index=index), val)
            assert c.schema.get(*kp, step=step, index=index) == val

        example_index += 1


def test_invalid_switch():
    chip = siliconcompiler.Chip('test_chip')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.create_cmdline('testing', switchlist=['-loglevel', '-var', '-abcd'])
