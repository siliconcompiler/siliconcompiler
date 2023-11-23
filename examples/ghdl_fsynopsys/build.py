import siliconcompiler

from siliconcompiler.tools.ghdl import convert
from siliconcompiler.tools.yosys import syn_asic
import os


def main():
    chip = siliconcompiler.Chip('binary_4_bit_adder_top')
    root = os.path.dirname(__file__)
    chip.input(f'{root}/binary_4_bit_adder_top.vhd')
    # this is to set -fsynopsys
    # see PR #1015 (https://github.com/siliconcompiler/siliconcompiler/pull/1015)
    chip.set('tool', 'ghdl', 'task', 'convert', 'var', 'extraopts', '-fsynopsys')

    chip.load_target("freepdk45_demo")
    flow = 'vhdlsyn'
    chip.node(flow, 'import', convert)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    chip.set('option', 'flow', flow)

    chip.run()


if __name__ == '__main__':
    main()
