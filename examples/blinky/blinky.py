#!/usr/bin/env python3

import siliconcompiler
from siliconcompiler.targets import fpgaflow_demo
import os


def main():
    root = os.path.dirname(__file__)

    chip = siliconcompiler.Chip('blinky')
    chip.input(os.path.join(root, "blinky.v"))
    chip.input(os.path.join(root, "icebreaker.pcf"))
    chip.set('fpga', 'partname', 'ice40up5k-sg48')

    chip.use(fpgaflow_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
