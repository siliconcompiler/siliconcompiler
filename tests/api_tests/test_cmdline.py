# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import re
from siliconcompiler import schema_utils
if __name__ != "__main__":
    from tests.fixtures import test_wrapper

#######################################################
def test_cmdline():
    '''
    Cycles through all keys and looks at cli to create
    a command lile argument.
    * booleans not tested
    * check-only asserted
    *
    '''
    chip = siliconcompiler.Chip(loglevel="INFO")
    error = 0
    allkeys = chip.getkeys()
    for key in allkeys:
        #print(key)
        sctype = chip.get(*key, field='type')
        switch = chip.get(*key, field='switch')
        example = chip.get(*key, field='example')[0]
        arglist = schema_utils.switchparse(example)
        #Construct switch
        #Assemble args


        print(switch, arglist)

#########################################################
if __name__ == "__main__":
    test_cmdline()
