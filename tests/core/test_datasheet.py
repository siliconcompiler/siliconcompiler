# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler


def test_datasheet():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('nand2')

    mode = 'default'

    # inputs
    chip.set('datasheet', 'pin', 'a', 'dir', mode, 'input')
    chip.set('datasheet', 'pin', 'b', 'dir', mode, 'input')
    chip.set('datasheet', 'pin', 'a', 'cap', mode, (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'b', 'cap', mode, (0.9, 0.9, 0.9))

    # output
    chip.set('datasheet', 'pin', 'z', 'dir', mode, 'output')
    chip.set('datasheet', 'pin', 'z', 'trise', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tfall', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'trise', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tfall', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tdelayr', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tdelayf', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tdelayr', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', 'pin', 'z', 'tdelayf', mode, 'b', (0.9, 0.9, 0.9))

    # print outputs
    for key in chip.allkeys():
        if key[0] == 'datasheet':
            val = chip.get(*key)
            if val:
                print(key, chip.get(*key))
