import siliconcompiler as sc
import os

def add_sources(chip):
    chip.add('source', 'eq1.vhd')
    chip.add('source', 'eq2.v')

def main():
    chip = sc.Chip()

    chip.add('design', 'eq2')
    add_sources(chip)
    chip.set('target', 'freepdk45_ghdlflow')

    chip.set_jobid()
    chip.target()
    chip.run()

if __name__ == '__main__':
    main()
