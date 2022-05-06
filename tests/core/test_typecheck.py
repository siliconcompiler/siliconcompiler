# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_typecheck():
    chip = siliconcompiler.Chip('top')

    error = 0

    #basic get/set test
    design = chip.get('design')
    if design != "top":
        error = 1

    #Check list access
    inlist = ['import','syn']
    chip.set('option', 'steplist', inlist)
    if (inlist != chip.get('option', 'steplist')):
        error = 1

    #Check scalar to list access
    inscalar = 'import'
    chip.set('option', 'steplist', 'import')
    outlist = chip.get('option', 'steplist')
    if (outlist != [inscalar]):
        error = 1

    #check illegal key (expected error)
    chip.set('badquery', 'top')
    if not chip.error:
        error = 1
    else:
        chip.error = 0

    #check error on scalar add
    chip.add('design', 'top')
    if not chip.error:
        error = 1
    else:
        chip.error = 0

    #check assigning list to scalar
    chip.set('design', ['top'])
    if not chip.error:
        error = 1
    else:
        chip.error = 0

    assert (error == 0)

#########################
if __name__ == "__main__":
    test_typecheck()
