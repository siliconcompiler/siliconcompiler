# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler


def test_schematic():
    '''API test for schematic entry
    '''

    chip = siliconcompiler.Chip('test')

    # 4 input OR gate constructed from 2 input OR gates
    chip.add('schematic', 'component', [('I0', 'OR2'),
                                        ('I1', 'OR2'),
                                        ('I2', 'OR2')])

    # pins
    chip.add('schematic', 'pin', [('IN0', 'input'),
                                  ('IN1', 'input'),
                                  ('IN2', 'input'),
                                  ('IN3', 'input'),
                                  ('OUT', 'output')])

    # nets
    chip.add('schematic', 'net', 'IN0', ('I0', 'A'))
    chip.add('schematic', 'net', 'IN1', ('I0', 'B'))
    chip.add('schematic', 'net', 'IN2', ('I1', 'A'))
    chip.add('schematic', 'net', 'IN3', ('I1', 'B'))
    chip.add('schematic', 'net', 'INTA', [('I0', 'Z'), ('I2', 'A')])
    chip.add('schematic', 'net', 'INTB', [('I1', 'Z'), ('I2', 'B')])
    chip.add('schematic', 'net', 'OUT', ('I2', 'Z'))


#########################
if __name__ == "__main__":
    test_schematic()
