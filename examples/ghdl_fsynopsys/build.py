import siliconcompiler
import os

def main():
    chip = siliconcompiler.Chip()
    chip.set('design', 'binary_4_bit_adder_top')
    chip.add('source', 'binary_4_bit_adder_top.vhd')

    chip.load_target('freepdk45_demo')

    # TODO: add in synthesis step once we can get an output that passes thru
    # Yosys.
    flow = 'vhdlsyn'
    chip.node(flow, 'import', 'ghdl')
    chip.node(flow, 'syn', 'yosys')
    chip.edge(flow, 'import', 'syn')

    chip.set('flow', flow)

    chip.run()

if __name__ == '__main__':
    main()
