# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler


def test_datasheet():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip('nand2')

    mode = 'default'
    top = chip.top()

    # inputs
    chip.set('datasheet', top, 'pin', 'a', 'dir', mode, 'input')
    chip.set('datasheet', top, 'pin', 'b', 'dir', mode, 'input')
    chip.set('datasheet', top, 'pin', 'a', 'cap', mode, (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'b', 'cap', mode, (0.9, 0.9, 0.9))

    # output
    chip.set('datasheet', top, 'pin', 'z', 'function', mode, '~(a&b)')
    chip.set('datasheet', top, 'pin', 'z', 'dir', mode, 'output')
    chip.set('datasheet', top, 'pin', 'z', 'trise', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tfall', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'trise', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tfall', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tdelayr', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tdelayf', mode, 'a', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tdelayr', mode, 'b', (0.9, 0.9, 0.9))
    chip.set('datasheet', top, 'pin', 'z', 'tdelayf', mode, 'b', (0.9, 0.9, 0.9))

    # print outputs
    for key in chip.allkeys():
        if key[0] == 'datasheet':
            val = chip.get(*key)
            if val:
                print(key, chip.get(*key))


#########################
if __name__ == "__main__":
    test_datasheet()
