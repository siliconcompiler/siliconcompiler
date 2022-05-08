import siliconcompiler
import os

def main():
    chip = siliconcompiler.Chip()
    chip.set('design', 'binary_4_bit_adder_top')
    chip.add('source', 'binary_4_bit_adder_top.vhd')
    chip.set('frontend', 'vhdl')

    chip.load_target('freepdk45_demo')

    chip.run()

if __name__ == '__main__':
    main()
