# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import pytest
import siliconcompiler
import re

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

@pytest.mark.skip(reason="Need to go back and fix this....")
def test_setget():
    '''API test for set/get methods
    '''

    chip = siliconcompiler.Chip()
    error = 0

    allkeys = chip.getkeys()
    for key in allkeys:
        sctype = chip.get(*key, field='type')
        example = chip.get(*key, field='example')[0]
        match = re.match(r'cli\:\s+chip.set\((.*)\)', example)
        if match:
            argstring = re.sub(r'[\'\s]', '', match.group(1))
            tuplematch = re.match(r'(.*?),\((.*,.*)\)', argstring)
            if tuplematch:
                keypath = tuplematch.group(1).split(',')
                value = tuple(map(float, tuplematch.group(2).split(',')))
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
            chip.set(*args, clobber=True)
            result = chip.get(*keypath)
            if result != value:
                error = 1
                print(f"ERROR: expected = {value} result = {result} keypath={keypath}")
        else:
            print("ERROR: illegal example")
            error = 1

    chip.writecfg('allvals.json')

    assert(error==0)

#########################
if __name__ == "__main__":
    test_setget()
