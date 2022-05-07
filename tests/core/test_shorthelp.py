# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_help():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('test')
    allkeys = chip.getkeys()
    for key in allkeys:
        shorthelp=chip.get(*key, field='shorthelp')
        typestr=chip.get(*key, field='type')
        scope=chip.get(*key, field='scope')
        keystr = ','.join(key)
        group = key[0]
        row = [scope,f",{group}", f",{typestr}", f',"{shorthelp}"', f',"{keystr}"']
        print("{: <8} {: <15} {: <20} {: <45} {: <60}".format(*row))

#########################
if __name__ == "__main__":
    test_help()
