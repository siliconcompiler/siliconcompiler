# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_multichip():

    a = siliconcompiler.Chip("top")
    b = siliconcompiler.Chip("adder")
    c = siliconcompiler.Chip("mult")

    assert a.get('design') == 'top'
    assert a.get('design',cfg=b.cfg) == 'adder'
    assert a.get('design',cfg=c.cfg) == 'mult'

#########################
if __name__ == "__main__":
    test_multichip()
