import siliconcompiler
import os

def main():
    chip = siliconcompiler.Chip('binary_4_bit_adder_top')
    chip.add('input', 'vhdl', 'binary_4_bit_adder_top.vhd')
    # this is to set -fsynopsys
    # see PR #1015 (https://github.com/siliconcompiler/siliconcompiler/pull/1015)
    chip.set('tool', 'ghdl', 'task', 'import', 'var', 'import', '0', 'extraopts', '-fsynopsys')

    chip.load_target('freepdk45_demo')
    flow = 'vhdlsyn'
    chip.node(flow, 'import', 'ghdl')
    chip.node(flow, 'syn', 'yosys')
    chip.edge(flow, 'import', 'syn')

    chip.set('option', 'flow', flow)

    chip.run()

if __name__ == '__main__':
    main()
