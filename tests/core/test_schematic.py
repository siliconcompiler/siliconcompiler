# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler


def test_schematic():
    '''API test for schematic entry
    '''

    chip = siliconcompiler.Chip('test')

    # 4 input OR gate constructed from 2 input OR gates
    for inst in ['I0', 'I1', 'I2']:
        chip.set('schematic', 'component', inst, 'partname', 'OR2')

    # defining pins
    for pin in ['IN0', 'IN1', 'IN2', 'IN3']:
        chip.set('schematic', 'pin', pin, 'dir', 'input')

    chip.set('schematic', 'pin', 'OUT', 'dir', 'output')

    # connecting nets to pins
    chip.add('schematic', 'net', 'IN0', 'connect', 'I0.A')
    chip.add('schematic', 'net', 'IN1', 'connect', 'I0.B')
    chip.add('schematic', 'net', 'IN2', 'connect', 'I1.A')
    chip.add('schematic', 'net', 'IN3', 'connect', 'I1.B')
    chip.add('schematic', 'net', 'INTA', 'connect', ['I0.Z', 'I2.A'])
    chip.add('schematic', 'net', 'INTB', 'connect', ['I1.Z', 'I2.B'])
    chip.add('schematic', 'net', 'OUT', 'connect', ['I2.Z'])

    # verify that all components mentioned in net exist
    for net in chip.getkeys('schematic', 'net'):
        for pin in chip.get('schematic', 'net', net, 'connect'):
            inst = pin.split('.')[0]
            assert inst in chip.getkeys('schematic', 'component')

    # all pins must be defined as net
    for pin in chip.getkeys('schematic', 'pin'):
        assert pin in chip.getkeys('schematic', 'net')
