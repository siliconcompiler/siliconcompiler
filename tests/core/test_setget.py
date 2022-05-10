# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import re

def test_setget():
    '''API test for set/get methods

    Performs set or add based on API example for each entry in schema and
    ensures that we can recover the same value back. Also tests that keypaths in
    schema examples are valid.
    '''

    DEBUG = False
    chip = siliconcompiler.Chip('test')
    error = 0

    allkeys = chip.getkeys()
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

        argstring = re.sub(r'[\'\s]', '', match.group(2))
        tuplematch = re.match(r'(.*?),\((.*,.*)\)', argstring)
        if tuplematch:
            keypath = tuplematch.group(1).split(',')
            tuplestr = tuplematch.group(2)
            if sctype.strip('[]').startswith('(str,'):
                tuplestr = re.sub(r'[\(\)\'\s]','',tuplestr)
                value = tuple(tuplestr.split(','))
            else:
                value = tuple(map(float, tuplestr.split(',')))
            if re.match(r'\[',sctype):
                value = [value]
            args =  keypath + [value]
        else:
            keypath =  argstring.split(',')[:-1]
            value = argstring.split(',')[-1]
            if sctype == "float":
                value = float(value)
            elif sctype == "bool":
                    value = bool(sctype=='true')
            elif sctype == "int":
                value = int(value)
            if re.match(r'\[',sctype):
                value = [value]
            args = keypath + [value]

        if match.group(1) == 'set':
            if DEBUG:
                print(args)
            chip.set(*args, clobber=True)
        elif match.group(1) == 'add':
            chip.add(*args)

        print(keypath)
        result = chip.get(*keypath)
        assert result == value, f'Expected value {value} from keypath {keypath}. Got {result}.'

    chip.write_manifest('allvals.json')

    assert(error==0)

def test_set_field_bool():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'txt', False, field='copy')
    assert chip.get('input', 'txt', field='copy') is False

def test_set_field_error():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'txt', 'asdf', field='copy')
    # expect copy flag unchanged and error triggered
    assert chip.get('input', 'txt', field='copy') is True
    assert chip.error == 1

def test_set_add_field_list():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'txt', 'Alyssa P. Hacker', field='author')
    chip.add('input', 'txt', 'Ben Bitdiddle', field='author')
    assert chip.get('input', 'txt', field='author') == ['Alyssa P. Hacker', 'Ben Bitdiddle']

#########################
if __name__ == "__main__":
    test_setget()
