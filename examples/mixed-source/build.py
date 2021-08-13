import siliconcompiler as sc
import os

def add_sources(chip):
    chip.add('source', 'eq1.vhd')
    chip.add('source', 'eq2.v')

def main():
    chip = sc.Chip()

    chip.add('design', 'eq2')
    add_sources(chip)

    chip.set_jobid()
    chip.target("freepdk45")

    flow = [
        ('import', 'morty'),
        ('importvhdl', 'ghdl'),
        ('syn', 'yosys')
    ]

    for i, (step, tool) in enumerate(flow):
        if i > 0:
            chip.add('flowgraph', step, 'input', flow[i-1][0])
        chip.add('flowgraph', step, 'tool', tool)

    chip.run()

if __name__ == '__main__':
    main()
