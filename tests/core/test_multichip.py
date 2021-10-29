# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_multichip():

    a = siliconcompiler.Chip(loglevel="INFO")
    b = siliconcompiler.Chip(loglevel="INFO")
    c = siliconcompiler.Chip(loglevel="INFO")

    a.set('design', "top")
    b.set('design', "adder")
    c.set('design', "mult")

    assert a.get('design') == 'top'
    assert a.get('design',cfg=b.cfg) == 'adder'
    assert a.get('design',cfg=c.cfg) == 'mult'

#########################
if __name__ == "__main__":
    test_multichip()
