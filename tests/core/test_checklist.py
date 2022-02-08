# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_checklist():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_project('freepdk45_demo')

    #automated fail
    chip.set('metric','syn','0', 'errors', 'real', 1)
    chip.set('eda','yosys','report', 'syn', '0', 'qor', 'qor.rpt')
    chip.set('checklist','iso', 'd0', 'criteria', 'errors==0')
    chip.set('checklist','iso', 'd0', 'step', 'syn')
    assert not chip.check_checklist('iso', 'd0')

    #automated pass
    chip.set('checklist','iso', 'd1', 'step', 'syn')
    assert chip.check_checklist('iso', 'd1')

#########################
if __name__ == "__main__":
    test_checklist()
