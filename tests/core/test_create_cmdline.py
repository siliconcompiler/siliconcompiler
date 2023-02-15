import re
import pytest

import siliconcompiler

def do_cli_test(args, monkeypatch, switchlist=None, input_map=None):
    chip = siliconcompiler.Chip('test')
    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc', switchlist=switchlist, input_map=input_map)
    return chip

def test_cli_multi_source(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc',
            '-input', 'rtl verilog examples/ibex/ibex_alu.v',
            '-input', 'rtl verilog examples/ibex/ibex_branch_predict.v',
            '-target', 'freepdk45_demo']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('input','rtl','verilog') == ['examples/ibex/ibex_alu.v',
                                                 'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option','target') == 'freepdk45_demo'

def test_cli_include_flag(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    args = ['sc',
            '-input', 'rtl verilog source.v',
            '-I', 'include/inc1', '+incdir+include/inc2']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('input', 'rtl', 'verilog') == ['source.v']
    assert chip.get('option', 'idir') == ['include/inc1', 'include/inc2']

def test_optmode(monkeypatch):
    '''Test optmode special handling.'''
    args = ['sc', '-O3']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('option', 'optmode') == 'O3'

def test_spaces_in_value(monkeypatch):
    desc = 'My package description'
    args = ['sc', '-package_description', desc]

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('package', 'description') == desc

def test_limited_switchlist(monkeypatch):
    args = ['sc', '-loglevel', 'DEBUG', '-var', 'foo bar']
    chip = do_cli_test(args, monkeypatch, switchlist=['-loglevel', '-var'])

    assert chip.get('option', 'loglevel') == 'DEBUG'
    assert chip.get('option', 'var', 'foo') == ['bar']

def test_pernode_optional(monkeypatch):
    '''Ensure we can specify pernode overrides from CLI, and that they support
    spaces in values.'''
    args = ['sc']
    args += ['-asic_logiclib', 'syn "syn lib"']
    args += ['-asic_logiclib', 'syn 1 "\\"syn1\\" lib"']
    args += ['-asic_logiclib', '"my lib"']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('asic', 'logiclib') == ['my lib']
    assert chip.get('asic', 'logiclib', step='syn') == ['syn lib']
    assert chip.get('asic', 'logiclib', step='syn', index=1) == ['"syn1" lib']

def test_pernode_required(monkeypatch):
    pass

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

def test_cli_examples(monkeypatch):
    # Need to mock this function, since our cfg CLI example will try to call it
    # on a fake manifest.
    def _mock_read_manifest(chip, manifest, clobber=False, clear=False):
        # nop
        pass
    monkeypatch.setattr(siliconcompiler.Chip, 'read_manifest', _mock_read_manifest)

    chip = siliconcompiler.Chip('test')
    for keypath in chip.allkeys():
        examples = chip.get(*keypath, field='example')
        for example in examples:
            if not example.startswith('cli'):
                continue

            match = re.match(r'cli\: (\S+)(?:\s(.*))?', example)
            assert match is not None, f'Invalid CLI example: {example}'

            switch, value = match.groups()
            if value is None:
                value = ''

            if len(value.split(' ')) > 1:
                assert value[0] == "'" and value[-1] == "'", f'Multi-word value must be surrounded by quotes: {example}'
            value = value.strip("'")

            default_count = keypath.count('default')
            assert len(value.split(' ')) >= default_count + 1, f'Not enough values to fill in default keys: {keypath}'
            if chip.get(*keypath, field='pernode') == 'required':
                *free_keys, step, index, expected_val = value.split(' ', default_count + 2)
            else:
                *free_keys, expected_val = value.split(' ', default_count)
                step, index = None, None
            typestr = chip.get(*keypath, field='type')
            replaced_keypath = [free_keys.pop(0) if key == 'default' else key for key in keypath]

            # Special cases
            if keypath == ['option', 'optmode']:
                expected_val = switch.lstrip('-')
            elif keypath == ['option', 'define']:
                expected_val = switch[len('-D'):]
            elif switch.startswith('+incdir+'):
                expected_val = switch[len('+incdir+'):]
            elif switch.startswith('+libext+'):
                expected_val = switch[len('+libext+'):]

            args = ['sc', switch]
            if value:
                args.append(value)

            c = do_cli_test(args, monkeypatch)

            if expected_val:
                assert c.get(*replaced_keypath, step=step, index=index) == _cast(expected_val, typestr)
            else:
                assert typestr == 'bool', 'Implicit value only alowed for boolean'
                assert c.get(*replaced_keypath, step=step, index=index) == True
