# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    chip = siliconcompiler.Chip(loglevel="INFO")

    error = 0

    #basic get/set test
    chip.set('design', 'top' )
    design = chip.get('design')
    if design != "top":
        error = 1

    #Check list access
    inlist = ['import','syn']
    chip.set('steplist', inlist)
    if (inlist != chip.get('steplist')):
        error = 1

    #Check scalar to list access
    inscalar = 'import'
    chip.set('steplist', 'import')
    outlist = chip.get('steplist')
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

    if error:
        print("FAIL")
        sys.exit(1)

#########################
if __name__ == "__main__":
    sys.exit(main())
    print("errorcode=",error)
