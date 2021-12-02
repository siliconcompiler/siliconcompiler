# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_help():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip(loglevel="INFO")
    allkeys = chip.getkeys()
    for key in allkeys:
        shorthelp=chip.get(*key, field='shorthelp')
        typestr=chip.get(*key, field='type')
        keystr = ','.join(key)
        row = [typestr, shorthelp, keystr]
        print("{: <15} {: <40} {: <60}".format(*row))

#########################
if __name__ == "__main__":
    test_help()
