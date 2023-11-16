import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo

import os


def main():
    root = os.path.dirname(__file__)

    chip = siliconcompiler.Chip('blinky')
    chip.input(f'{root}/blinky.v')
    chip.input(f'{root}/icebreaker.pcf')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')

    chip.load_target(fpgaflow_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
